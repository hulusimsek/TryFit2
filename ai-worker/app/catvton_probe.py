"""Local CatVTON research comparison; actual raw and optional repaint outputs."""
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
            self.noise_scheduler=DDIMScheduler.from_pretrained(str(weights/'base'),subfolder='scheduler',local_files_only=True)
            self.vae=AutoencoderKL.from_pretrained(str(weights/'vae'),torch_dtype=self.weight_dtype,local_files_only=True).to(self.device).eval()
            self.unet=UNet2DConditionModel.from_pretrained(str(weights/'base'),subfolder='unet',torch_dtype=self.weight_dtype,local_files_only=True).to(self.device).eval()
            init_adapter(self.unet,cross_attn_cls=SkipAttnProcessor)
            self.attn_modules=get_trainable_module(self.unet,'attention')
            self.auto_attn_ckpt_load(str(weights/'adapter'),'mix')
            original=self.unet.forward
            self.unet.forward=types.MethodType(lambda _,sample,timestep,**kwargs:sequential_unet(original,sample,timestep,**kwargs),self.unet)
            self.vae.enable_tiling();self.vae.enable_slicing()
            self.vae.tile_sample_min_size=512;self.vae.tile_latent_min_size=64
            torch.set_float32_matmul_precision('high');torch.backends.cuda.matmul.allow_tf32=True
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
                    peak_allocated_gib=round(torch.cuda.max_memory_allocated()/2**30,3),peak_reserved_gib=round(torch.cuda.max_memory_reserved()/2**30,3))
                make_comparison(target,load_rgb(ROOT/next(c['image'] for c in manifest['cases'] if c['id']==identifier)),primary,dest/(identifier+'-comparison.jpg'))
            except Exception as error:
                item.update(status='failed',error=str(error),traceback=traceback.format_exc())
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
