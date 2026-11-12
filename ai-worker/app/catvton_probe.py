"""Local CatVTON research comparison; actual raw and optional repaint outputs."""
import gc
import json
import random
import sys
import time
import traceback
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image
from experiment import load_rgb, sha256, write_json, command_output, create_review, evaluate, make_comparison
from catvton_inputs import target_inputs, source_cutout

ROOT=Path(__file__).resolve().parents[2]
IDS=['oversize-hoodie','denim-jacket','hooded-sweatshirt']

# 768x1024 (96x128 latent) untiled VAE decode measured ~3.04 GiB peak reserved;
# keep 0.5 GiB fixed baseline + 3.0 GiB area-scaled budget (~3.5 GiB at 768x1024).
_GIB = 1024 ** 3
BASE_LATENT_AREA = 128 * 96
UNTILED_DECODE_FIXED_OVERHEAD_BYTES = int(0.5 * _GIB)
UNTILED_DECODE_SCALED_BYTES = int(3.0 * _GIB)
UNTILED_DECODE_SAFE_FREE_BYTES = UNTILED_DECODE_FIXED_OVERHEAD_BYTES + UNTILED_DECODE_SCALED_BYTES


def estimate_untiled_decode_free_bytes(z):
    """Estimate safe free VRAM for untiled decode scaled by latent area.

    Note: latent area scaling is an approximation (mid-block self-attention scales
    quadratically and driver/external VRAM fragmentation is unpredictable), so
    runtime OutOfMemoryError fallback remains the authoritative safeguard.
    """
    shape = getattr(z, 'shape', None)
    if shape is None or len(shape) < 4:
        return UNTILED_DECODE_SAFE_FREE_BYTES
    area_scale = max(0, int(shape[-2]) * int(shape[-1])) / BASE_LATENT_AREA
    return int(UNTILED_DECODE_FIXED_OVERHEAD_BYTES + UNTILED_DECODE_SCALED_BYTES * area_scale)


def _normalize_device(device):
    if isinstance(device, str):
        import torch
        return torch.device(device)
    return device


def _devices_match(current_device, target_device, cuda_module=None):
    if target_device is None:
        return True
    if current_device is None:
        return False
    current_device = _normalize_device(current_device)
    target_device = _normalize_device(target_device)
    if current_device == target_device:
        return True
    cur_type = getattr(current_device, 'type', None)
    tgt_type = getattr(target_device, 'type', None)
    if cur_type != tgt_type:
        return False
    if cur_type != 'cuda':
        return True
    cur_idx = getattr(current_device, 'index', None)
    tgt_idx = getattr(target_device, 'index', None)
    if cur_idx is None and tgt_idx is None:
        return True
    if cur_idx is None or tgt_idx is None:
        if cuda_module is None:
            import torch
            active_idx = torch.cuda.current_device() if torch.cuda.is_available() else 0
        else:
            active_idx = cuda_module.current_device()
        cur_idx = active_idx if cur_idx is None else cur_idx
        tgt_idx = active_idx if tgt_idx is None else tgt_idx
    return cur_idx == tgt_idx


def _module_device(module):
    params = getattr(module, 'parameters', None)
    if callable(params):
        param = next(iter(params()), None)
        if param is not None:
            return param.device
    bufs = getattr(module, 'buffers', None)
    if callable(bufs):
        buf = next(iter(bufs()), None)
        if buf is not None:
            return buf.device
    return getattr(module, 'device', None)


def _attach_error_stage(exc, stage):
    add_note = getattr(exc, 'add_note', None)
    if callable(add_note) and stage:
        note = f'stage={stage}'
        if note not in getattr(exc, '__notes__', ()):
            add_note(note)


def ensure_unet_device(unet, target_device, *, cuda_module=None, on_error_stage=None):
    """Move UNet to target_device only when its current device differs or prior move failed."""
    if unet is None or target_device is None:
        return False
    if not getattr(unet, '_tryfit_device_uncertain', False):
        current_device = _module_device(unet)
        if _devices_match(current_device, target_device, cuda_module=cuda_module):
            return False
    setattr(unet, '_tryfit_device_uncertain', True)
    try:
        unet.to(target_device)
    except BaseException as exc:
        _attach_error_stage(exc, 'unet_restore')
        if on_error_stage is not None:
            on_error_stage('unet_restore')
        raise
    setattr(unet, '_tryfit_device_uncertain', False)
    return True


def wrap_unet_forward(unet, original_forward, *, cuda_module=None, on_error_stage=None):
    """Wrap UNet forward with lazy device restoration before sequential CFG."""
    def forward(_, sample, timestep, **kwargs):
        target_device = getattr(sample, 'device', None)
        if target_device is not None:
            ensure_unet_device(unet, target_device, cuda_module=cuda_module, on_error_stage=on_error_stage)
        return sequential_unet(original_forward, sample, timestep, **kwargs)

    return forward


def _set_vae_tiling(vae, enabled):
    if enabled:
        vae.enable_tiling()
    else:
        vae.disable_tiling()


def _cuda_free_bytes(cuda_module, device):
    free_bytes, _ = cuda_module.mem_get_info(device)
    return int(free_bytes)


def _safe_cuda_stat(cuda_module, fn_name, device):
    fn = getattr(cuda_module, fn_name, None)
    if not callable(fn):
        return None
    try:
        return int(fn(device))
    except TypeError:
        try:
            return int(fn())
        except Exception:
            return None
    except Exception:
        return None


def _safe_cuda_free_bytes(cuda_module, device):
    try:
        return _cuda_free_bytes(cuda_module, device)
    except Exception:
        return None


def _try_decode_once(original_decode, z, return_dict, generator, oom_error_types):
    """Run one decode attempt in its own frame so OOM exception/activations unwind on return."""
    try:
        return True, original_decode(z, return_dict=return_dict, generator=generator)
    except oom_error_types:
        return False, None


def _offload_unet_to_cpu(unet, cuda_module):
    """Move UNet off GPU when needed; keep _tryfit_device_uncertain on failure."""
    if unet is None:
        return False
    if not getattr(unet, '_tryfit_device_uncertain', False) and _devices_match(_module_device(unet), 'cpu', cuda_module=cuda_module):
        return False
    setattr(unet, '_tryfit_device_uncertain', True)
    unet.to('cpu')
    setattr(unet, '_tryfit_device_uncertain', False)
    return True


def adaptive_vae_decode(
    vae,
    unet,
    original_decode,
    z,
    *,
    return_dict=True,
    generator=None,
    min_free_bytes=None,
    cuda_module=None,
    gc_module=None,
    oom_error_types=None,
    info_sink=None,
):
    """Decode latents without tiling when VRAM allows, offloading UNet or falling back to tiling safely."""
    start = time.perf_counter()
    previous_tiling = bool(getattr(vae, 'use_tiling', False))
    gc_mod = gc_module if gc_module is not None else gc
    z_device = getattr(z, 'device', None)
    is_cuda = getattr(z_device, 'type', None) == 'cuda'
    if is_cuda and cuda_module is None:
        import torch
        cuda_module = torch.cuda
    if oom_error_types is None:
        import torch
        oom_error_types = (torch.cuda.OutOfMemoryError,)

    info = {
        'mode': None,
        'unet_offloaded': False,
        'oom_fallback': False,
        'initial_tiling': previous_tiling,
        'final_tiling': previous_tiling,
        'free_vram_before_bytes': None,
        'free_vram_after_offload_bytes': None,
        'free_vram_after_bytes': None,
        'allocated_vram_before_bytes': None,
        'reserved_vram_before_bytes': None,
        'allocated_vram_after_bytes': None,
        'reserved_vram_after_bytes': None,
        'peak_allocated_vram_bytes': None,
        'peak_reserved_vram_bytes': None,
        'threshold_bytes': None,
        'elapsed_seconds': 0.0,
        'error_type': None,
        'error_stage': None,
    }
    stage = 'vram_probe' if is_cuda else 'untiled_decode'

    try:
        if is_cuda:
            stage = 'vram_probe'
            threshold = int(min_free_bytes) if min_free_bytes is not None else estimate_untiled_decode_free_bytes(z)
            info['threshold_bytes'] = threshold
            cuda_module.empty_cache()
            free_before = _cuda_free_bytes(cuda_module, z_device)
            info['free_vram_before_bytes'] = free_before
            info['allocated_vram_before_bytes'] = _safe_cuda_stat(cuda_module, 'memory_allocated', z_device)
            info['reserved_vram_before_bytes'] = _safe_cuda_stat(cuda_module, 'memory_reserved', z_device)
            free_available = free_before

            if free_available < threshold and unet is not None:
                stage = 'unet_offload'
                if _offload_unet_to_cpu(unet, cuda_module):
                    cuda_module.empty_cache()
                    info['unet_offloaded'] = True
                    stage = 'vram_probe'
                    free_available = _cuda_free_bytes(cuda_module, z_device)
            info['free_vram_after_offload_bytes'] = free_available

            if free_available < threshold:
                stage = 'tiled_direct_decode'
                _set_vae_tiling(vae, True)
                info['mode'] = 'tiled_direct'
                return original_decode(z, return_dict=return_dict, generator=generator)

        stage = 'untiled_decode'
        _set_vae_tiling(vae, False)
        info['mode'] = 'untiled'
        ok, decoded = _try_decode_once(original_decode, z, return_dict, generator, oom_error_types)
        if ok:
            return decoded

        info['oom_fallback'] = True
        stage = 'oom_cleanup'
        if is_cuda and unet is not None and not info['unet_offloaded']:
            if _offload_unet_to_cpu(unet, cuda_module):
                info['unet_offloaded'] = True
        gc_mod.collect()
        if is_cuda:
            cuda_module.empty_cache()

        stage = 'tiled_fallback_decode'
        _set_vae_tiling(vae, True)
        info['mode'] = 'tiled_fallback'
        return original_decode(z, return_dict=return_dict, generator=generator)
    except BaseException as exc:
        info['error_type'] = type(exc).__name__
        info['error_stage'] = stage
        _attach_error_stage(exc, stage)
        raise
    finally:
        try:
            _set_vae_tiling(vae, previous_tiling)
        except BaseException as restore_exc:
            if info['error_type'] is None:
                info['error_type'] = type(restore_exc).__name__
                info['error_stage'] = 'tiling_restore'
                _attach_error_stage(restore_exc, 'tiling_restore')
                info['final_tiling'] = bool(getattr(vae, 'use_tiling', previous_tiling))
                info['elapsed_seconds'] = round(time.perf_counter() - start, 4)
                if info_sink is not None:
                    info_sink(dict(info))
                raise
        info['final_tiling'] = bool(getattr(vae, 'use_tiling', previous_tiling))
        if is_cuda:
            info['free_vram_after_bytes'] = _safe_cuda_free_bytes(cuda_module, z_device)
            info['allocated_vram_after_bytes'] = _safe_cuda_stat(cuda_module, 'memory_allocated', z_device)
            info['reserved_vram_after_bytes'] = _safe_cuda_stat(cuda_module, 'memory_reserved', z_device)
            info['peak_allocated_vram_bytes'] = _safe_cuda_stat(cuda_module, 'max_memory_allocated', z_device)
            info['peak_reserved_vram_bytes'] = _safe_cuda_stat(cuda_module, 'max_memory_reserved', z_device)
        info['elapsed_seconds'] = round(time.perf_counter() - start, 4)
        if info_sink is not None:
            info_sink(dict(info))


def sequential_unet(original, sample, timestep, **kwargs):
    """UNet GroupNorm/SDPA branches are independent; avoid doubled activation batch."""
    import torch
    if sample.shape[0] == 1:
        return original(sample,timestep,**kwargs)
    if kwargs.get('encoder_hidden_states') is not None or kwargs.get('return_dict',True):
        raise ValueError('Only pinned CatVTON tuple-output call without text is supported')
    return (torch.cat([original(part,timestep,**kwargs)[0] for part in sample.split(1)],dim=0),)


def pipeline(weights):
    import torch
    sys.path.insert(0,str(ROOT/'vendor/CatVTON'))
    from model.pipeline import CatVTONPipeline
    from model.attn_processor import SkipAttnProcessor
    from model.utils import init_adapter, get_trainable_module
    from diffusers import AutoencoderKL, DDIMScheduler, UNet2DConditionModel

    class LocalPipeline(CatVTONPipeline):
        def __init__(self):
            self.device='cuda';self.weight_dtype=torch.bfloat16
            # Matches official inference.py dataset mode; these are benign adult garment tests.
            self.skip_safety_check=True
            self.last_decode_info=None
            self.last_error_stage=None
            self.noise_scheduler=DDIMScheduler.from_pretrained(str(weights/'base'),subfolder='scheduler',local_files_only=True)
            self.vae=AutoencoderKL.from_pretrained(str(weights/'vae'),torch_dtype=self.weight_dtype,local_files_only=True).to(self.device).eval()
            self.unet=UNet2DConditionModel.from_pretrained(str(weights/'base'),subfolder='unet',torch_dtype=self.weight_dtype,local_files_only=True).to(self.device).eval()
            init_adapter(self.unet,cross_attn_cls=SkipAttnProcessor)
            self.attn_modules=get_trainable_module(self.unet,'attention')
            self.auto_attn_ckpt_load(str(weights/'adapter'),'mix')
            original=self.unet.forward
            self.unet.forward=types.MethodType(
                wrap_unet_forward(
                    self.unet,
                    original,
                    on_error_stage=lambda stage:setattr(self,'last_error_stage',stage),
                ),
                self.unet,
            )
            self.vae.enable_tiling();self.vae.enable_slicing()
            self.vae.tile_sample_min_size=512;self.vae.tile_latent_min_size=64
            original_decode=self.vae.decode
            def _record_decode_info(info):
                self.last_decode_info=info
                if info.get('error_stage'):
                    self.last_error_stage=info['error_stage']
            def wrapped_decode(_,z,return_dict=True,generator=None):
                return adaptive_vae_decode(
                    self.vae,
                    self.unet,
                    original_decode,
                    z,
                    return_dict=return_dict,
                    generator=generator,
                    info_sink=_record_decode_info,
                )
            self.vae.decode=types.MethodType(wrapped_decode,self.vae)
            torch.set_float32_matmul_precision('high');torch.backends.cuda.matmul.allow_tf32=True

        @torch.no_grad()
        def __call__(self,*args,**kwargs):
            self.last_decode_info=None
            self.last_error_stage=None
            return super().__call__(*args,**kwargs)
    return LocalPipeline()


def run(*, flatlay_hoodie=False, annotation_path=None):
    import torch
    manifest=json.loads((ROOT/'evaluation/manifests/trendyol-10.actual.json').read_text(encoding='utf-8'))
    ids=['oversize-hoodie'] if flatlay_hoodie else IDS
    if flatlay_hoodie:
        case=next(c for c in manifest['cases'] if c['id']=='oversize-hoodie')
        sources=json.loads((ROOT/'data/first-outfit/gallery/sources.json').read_text(encoding='utf-8'))
        gallery=next(s for s in sources if Path(s['image']).name=='gallery-1.jpg')
        case.update(image='data/first-outfit/gallery/gallery-1.jpg',image_sha256=sha256(ROOT/'data/first-outfit/gallery/gallery-1.jpg'),
                    garment_photo_type='flat-lay',source_image_url=gallery['source_url'],
                    source_notes='Separate real product flat-lay control of the same hoodie; not part of worn-photo three-case score.')
    annotation_path=Path(annotation_path) if annotation_path is not None else ROOT/'evaluation/annotations/avatar-upper.catvton.json'
    annotation=json.loads(annotation_path.read_text(encoding='utf-8'))
    target_path=ROOT/manifest['person']['image']
    if sha256(target_path)!=annotation['image_sha256']:
        raise ValueError('Target annotation image changed')
    target,hard,mask,overlay,transform=target_inputs(load_rgb(target_path),annotation)
    dest=ROOT/'runs'/('catvton-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6])
    dest.mkdir(parents=True)
    record={'schema_version':1,'status':'initializing','quality_status':'not_reviewed','cases':[],
        'model':'CatVTON mix-48k-1024','settings':{'seed':42,'num_inference_steps':50,'guidance_scale':2.5,'eta':1.0,'width':768,'height':1024},
        'experiment_scope':'separate real flat-lay hoodie control' if flatlay_hoodie else 'three worn-photo SAM-cutout cases',
        'baseline':'runs/20261110T095148Z-cf9135a6','target_sha256':sha256(target_path),
        'target_annotation':annotation,'annotation_sha256':sha256(annotation_path),'target_transform':transform,
        'primary_output':'Official optional repaint of actual inference with original target outside blurred mask; raw output also saved',
        'limitations':['Manual target polygon; not automatic target masking','SAM source selection is researcher-assisted',
            'Different required preprocessing, resolution, sampler and target masking from FASHN; not architecture-only ablation',
            'No measured body reconstruction or fit validation','CatVTON CC BY-NC-SA 4.0: research comparison only'],
        'adaptations':['Local VAE checkpoint path','BF16 CPU load then CUDA','Sequential UNet CFG batch branches',
            'VAE tiling 512 sample / 64 latent and slicing','Target letterboxed without cropping','Official dataset inference mode without safety checker'],
        'upstream_commit':command_output(['git','-C',str(ROOT/'vendor/CatVTON'),'rev-parse','HEAD'])}
    write_json(dest/'manifest.json',manifest);write_json(dest/'run.json',record)
    target.save(dest/'target-canvas.png');hard.save(dest/'target-mask-hard.png');mask.save(dest/'target-mask-blurred.png');overlay.save(dest/'target-mask-overlay.jpg')
    try:
        record['environment']={'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'dtype':'bfloat16','python':sys.version}
        (dest/'pip-freeze.txt').write_text(command_output([sys.executable,'-m','pip','freeze'])['stdout'],encoding='utf-8')
        weights=ROOT/'ai-worker/models/catvton'
        provenance=json.loads((weights/'provenance.json').read_text())
        for entry in provenance['files']:
            if sha256(weights/entry['relative_path'])!=entry['sha256']:
                raise ValueError('Model checkpoint changed')
        record['model_provenance']=provenance
        prepared={}
        for identifier in ids:
            case=next(c for c in manifest['cases'] if c['id']==identifier)
            if flatlay_hoodie:
                condition=load_rgb(ROOT/case['image'])
                condition.save(dest/(identifier+'-condition.png'))
                prepared[identifier]=(condition,{'source_sha256':case['image_sha256'],
                    'condition_sha256':sha256(dest/(identifier+'-condition.png')),'source_type':'real flat-lay product photo; no synthetic garment repair'})
                continue
            extraction=ROOT/('runs/source-extraction-'+identifier+'-refined')
            meta=json.loads((extraction/'extraction.json').read_text())
            if sha256(ROOT/case['image'])!=case['image_sha256'] or meta['annotation']['image_sha256']!=case['image_sha256'] or sha256(extraction/'mask.png')!=meta['mask_sha256']:
                raise ValueError('Source/mask changed')
            condition,box=source_cutout(load_rgb(ROOT/case['image']),Image.open(extraction/'mask.png'))
            condition.save(dest/(identifier+'-condition.png'))
            prepared[identifier]=(condition,{'source_sha256':case['image_sha256'],'source_mask_sha256':meta['mask_sha256'],
                'condition_sha256':sha256(dest/(identifier+'-condition.png')),'visible_foreground_crop_box':box,'source_extraction':str(extraction.relative_to(ROOT))})
        write_json(dest/'run.json',record)
        print('PREPARED_INPUTS='+str(dest),flush=True)
        model=pipeline(weights)
        from utils import repaint_result
        record['status']='running'
        for identifier in ids:
            item={'id':identifier,'status':'running','quality_status':'not_reviewed',**prepared[identifier][1]}
            record['cases'].append(item);write_json(dest/'run.json',record)
            start=time.perf_counter()
            try:
                torch.manual_seed(42);np.random.seed(42);random.seed(42)
                generator=torch.Generator(device='cuda').manual_seed(42)
                torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize()
                print('START '+identifier,flush=True)
                raw=model(image=target,condition_image=prepared[identifier][0],mask=mask,num_inference_steps=50,guidance_scale=2.5,height=1024,width=768,generator=generator,eta=1.0)[0]
                torch.cuda.synchronize()
                raw.save(dest/(identifier+'-raw.png'))
                primary=repaint_result(raw,target,mask)
                primary.save(dest/(identifier+'.png'))
                item.update(status='completed',output=identifier+'.png',output_sha256=sha256(dest/(identifier+'.png')),
                    raw_output=identifier+'-raw.png',raw_sha256=sha256(dest/(identifier+'-raw.png')),
                    peak_allocated_gib=round(torch.cuda.max_memory_allocated()/2**30,3),peak_reserved_gib=round(torch.cuda.max_memory_reserved()/2**30,3),
                    vae_decode=getattr(model,'last_decode_info',None))
                make_comparison(target,load_rgb(ROOT/next(c['image'] for c in manifest['cases'] if c['id']==identifier)),primary,dest/(identifier+'-comparison.jpg'))
            except Exception as error:
                decode_info=getattr(model,'last_decode_info',None)
                item.update(status='failed',error=str(error),error_type=type(error).__name__,
                    error_stage=getattr(model,'last_error_stage',None) or (decode_info or {}).get('error_stage'),
                    vae_decode=decode_info,traceback=traceback.format_exc())
                if isinstance(error,torch.cuda.OutOfMemoryError):record['stopped_reason']='out_of_memory';break
            finally:
                item['elapsed_seconds']=round(time.perf_counter()-start,2);write_json(dest/'run.json',record)
        attempted={c['id'] for c in record['cases']}
        record['cases'].extend({'id':i,'status':'not_run','quality_status':'not_reviewed'} for i in ids if i not in attempted)
        record['status']='completed' if all(c['status']=='completed' for c in record['cases']) else 'incomplete'
    except Exception as error:
        record.update(status='setup_failed',error=str(error),traceback=traceback.format_exc());raise
    finally:
        write_json(dest/'run.json',record);create_review(dest,record)
        print('RUN_DIR='+str(dest),flush=True)
    evaluate(dest)
    (ROOT/'runs'/('latest-catvton-flatlay.txt' if flatlay_hoodie else 'latest-catvton-probe.txt')).write_text(str(dest),encoding='utf-8')
    return dest


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--flatlay-hoodie',action='store_true');parser.add_argument('--annotation',type=Path)
    args=parser.parse_args();run(flatlay_hoodie=args.flatlay_hoodie,annotation_path=args.annotation)
