import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from catvton_inputs import letterbox, source_cutout, target_inputs, unletterbox
from catvton_probe import (
    BASE_LATENT_AREA,
    UNTILED_DECODE_FIXED_OVERHEAD_BYTES,
    UNTILED_DECODE_SAFE_FREE_BYTES,
    adaptive_vae_decode,
    ensure_unet_device,
    estimate_untiled_decode_free_bytes,
    wrap_unet_forward,
)


class InputTests(unittest.TestCase):
    def test_target_mask_and_full_body_share_identical_letterbox(self):
        picture=Image.new('RGB',(100,150),(30,40,50))
        canvas,transform=letterbox(picture,(768,1024))
        self.assertEqual(canvas.size,(768,1024))
        self.assertEqual(transform['resized_size'],[683,1024])
        mask=Image.new('L',picture.size,255)
        padded,mask_transform=letterbox(mask,(768,1024),mask=True)
        self.assertEqual(transform,mask_transform)
        self.assertEqual(padded.getpixel((0,512)),0)
        self.assertEqual(canvas.getpixel((384,0)),(30,40,50))
        self.assertEqual(canvas.getpixel((384,1023)),(30,40,50))

    def test_unletterbox_restores_576x864_and_removes_220_side_strips(self):
        picture=Image.new('RGB',(576,864),(35,90,155))
        canvas,transform=letterbox(picture,(768,1024))
        self.assertEqual(transform,{'original_size':[576,864],'resized_size':[683,1024],'offset':[42,0],'canvas_size':[768,1024]})
        self.assertEqual(canvas.getpixel((0,400)),(220,220,220))
        self.assertEqual(canvas.getpixel((767,400)),(220,220,220))
        restored=unletterbox(canvas,transform)
        self.assertEqual(restored.size,(576,864))
        arr=np.asarray(restored)
        self.assertFalse(np.all(arr==(220,220,220),axis=2).any())
        self.assertEqual(tuple(int(v) for v in arr[432,288]),(35,90,155))

    def test_unletterbox_rejects_missing_or_invalid_transform(self):
        canvas=Image.new('RGB',(768,1024),(220,220,220))
        valid={'original_size':[576,864],'resized_size':[683,1024],'offset':[42,0],'canvas_size':[768,1024]}
        for bad in [
            None,
            {},
            {**valid,'offset':[10,0]},
            {**valid,'resized_size':[900,1024]},
            {**valid,'canvas_size':[576,864]},
            {**valid,'original_size':[True,864]},
        ]:
            with self.assertRaises(ValueError):unletterbox(canvas,bad)

    def test_cutout_preserves_selected_pixels_and_uses_white_background(self):
        picture=Image.new('RGB',(60,80),(12,34,56))
        mask=np.zeros((80,60),dtype='uint8');mask[20:60,20:40]=255
        cutout,box=source_cutout(picture,mask)
        self.assertEqual(cutout.getpixel((25-box[0],30-box[1])),(12,34,56))
        self.assertEqual(cutout.getpixel((0,0)),(255,255,255))
        with self.assertRaises(ValueError):source_cutout(picture,mask[:10])

    def test_invalid_target_annotation_rejected(self):
        with self.assertRaises(ValueError):target_inputs(Image.new('RGB',(20,30)),{'polygon_normalized':[[0,0],[2,0],[1,1]]})

    def test_hand_exclusion_holes_are_aligned_and_validated(self):
        image=Image.new('RGB',(100,150),'gray')
        annotation={'polygon_normalized':[[.2,.2],[.8,.2],[.8,.8],[.2,.8]],
                    'exclusion_polygons_normalized':[[[.3,.3],[.5,.3],[.5,.5],[.3,.5]]]}
        _,hard,_,_,_=target_inputs(image,annotation,size=image.size)
        self.assertEqual(hard.getpixel((40,60)),0)
        self.assertEqual(hard.getpixel((60,60)),255)
        annotation['exclusion_polygons_normalized']=[[[0,0],[float('nan'),0],[1,1]]]
        with self.assertRaises(ValueError):target_inputs(image,annotation)

    def test_preservation_mask_blocks_soft_alpha_without_disabling_other_edits(self):
        image=Image.new('RGB',(100,150),'gray')
        annotation={'polygon_normalized':[[.1,.1],[.9,.1],[.9,.9],[.1,.9]]}
        protected=np.zeros((150,100),dtype='uint8');protected[30:90,30:50]=255
        _,hard,soft,_,_=target_inputs(image,annotation,size=image.size,preserve_mask=protected)
        self.assertEqual(hard.getpixel((40,60)),0)
        self.assertTrue((np.asarray(soft)[protected==255]==0).all())
        self.assertGreater(soft.getpixel((70,60)),200)
        for invalid in [protected[:10],np.ones_like(protected),np.full_like(protected,255)]:
            with self.assertRaises(ValueError):target_inputs(image,annotation,preserve_mask=invalid)


@unittest.skipUnless(importlib.util.find_spec('diffusers'),'CatVTON isolated environment required')
class SequentialUNetTests(unittest.TestCase):
    def test_actual_adapted_unet_matches_batched_forward(self):
        import torch
        from diffusers import UNet2DConditionModel
        root=Path(__file__).resolve().parents[2]
        sys.path.insert(0,str(root/'vendor/CatVTON'))
        from model.utils import init_adapter
        from model.attn_processor import SkipAttnProcessor
        from catvton_probe import sequential_unet
        torch.manual_seed(42)
        model=UNet2DConditionModel(sample_size=16,in_channels=9,out_channels=4,layers_per_block=1,
            block_out_channels=(32,64),down_block_types=('DownBlock2D','AttnDownBlock2D'),
            up_block_types=('AttnUpBlock2D','UpBlock2D'),cross_attention_dim=32,attention_head_dim=8,norm_num_groups=8).eval()
        init_adapter(model,cross_attn_cls=SkipAttnProcessor)
        sample=torch.randn(2,9,16,16)
        with torch.no_grad():
            batched=model(sample,torch.tensor(5),encoder_hidden_states=None,return_dict=False)[0]
            separate=sequential_unet(model.forward,sample,torch.tensor(5),encoder_hidden_states=None,return_dict=False)[0]
        torch.testing.assert_close(batched,separate,rtol=1e-5,atol=1e-5)


class _FakeVAE:
    def __init__(self, use_tiling=True, outcomes=None, events=None):
        self.use_tiling = use_tiling
        self.outcomes = list(outcomes or ['decoded'])
        self.events = events if events is not None else []
        self.decode_calls = []
        self.encode_tiling_history = []

    def enable_tiling(self):
        self.use_tiling = True
        self.events.append('vae.enable_tiling')

    def disable_tiling(self):
        self.use_tiling = False
        self.events.append('vae.disable_tiling')

    def encode(self, _x):
        self.encode_tiling_history.append(self.use_tiling)
        self.events.append(f'vae.encode:tiling={self.use_tiling}')
        return SimpleNamespace(shape=(1, 4, 128, 96))

    def decode(self, z, return_dict=True, generator=None):
        self.decode_calls.append({'tiling': self.use_tiling, 'z': z, 'return_dict': return_dict, 'generator': generator})
        self.events.append(f'vae.decode:tiling={self.use_tiling}')
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class _FakeUNet:
    def __init__(self, device='cuda:0', events=None, fail_on_to=None):
        import torch
        self.device = torch.device(device)
        self.move_calls = []
        self.forward_calls = []
        self.events = events if events is not None else []
        self.fail_on_to = list(fail_on_to or [])

    def parameters(self):
        return iter([SimpleNamespace(device=self.device)])

    def to(self, target):
        import torch
        target_dev = torch.device(target)
        self.move_calls.append(target_dev)
        self.events.append(f'unet.to:{target_dev}')
        if self.fail_on_to:
            err = self.fail_on_to.pop(0)
            if err is not None:
                raise err
        self.device = target_dev
        return self

    def forward(self, sample, timestep, **kwargs):
        self.forward_calls.append((sample.device, timestep))
        self.events.append(f'unet.forward:{sample.device}')
        return (sample,)


class _FakeCuda:
    def __init__(self, free_values, current_index=0, events=None, fail_after_probes=None):
        self._free_values = list(free_values)
        self._current_index = current_index
        self.events = events if events is not None else []
        self.empty_cache_calls = 0
        self.reset_peak_calls = 0
        self.mem_get_info_calls = 0
        self.fail_after_probes = fail_after_probes
        self.allocated_bytes = 2_000_000_000
        self.reserved_bytes = 2_500_000_000
        self.peak_allocated_bytes = 3_100_000_000
        self.peak_reserved_bytes = 3_400_000_000

    def current_device(self):
        return self._current_index

    def empty_cache(self):
        self.empty_cache_calls += 1
        self.events.append('cuda.empty_cache')

    def mem_get_info(self, _device=None):
        self.mem_get_info_calls += 1
        if self.fail_after_probes is not None and self.mem_get_info_calls > self.fail_after_probes:
            raise RuntimeError('CUDA telemetry error')
        val = self._free_values.pop(0) if len(self._free_values) > 1 else self._free_values[0]
        self.events.append(f'cuda.mem_get_info:{val}')
        return val, 8 * (1024 ** 3)

    def memory_allocated(self, _device=None):
        return self.allocated_bytes

    def memory_reserved(self, _device=None):
        return self.reserved_bytes

    def max_memory_allocated(self, _device=None):
        return self.peak_allocated_bytes

    def max_memory_reserved(self, _device=None):
        return self.peak_reserved_bytes

    def reset_peak_memory_stats(self):
        self.reset_peak_calls += 1
        raise AssertionError('reset_peak_memory_stats must not be called')


class _FakeGC:
    def __init__(self, events=None):
        self.calls = 0
        self.events = events if events is not None else []

    def collect(self):
        self.calls += 1
        self.events.append('gc.collect')


class AdaptiveVaeDecodeTests(unittest.TestCase):
    def _latent(self, shape=(1, 4, 128, 96), device='cuda:0'):
        import torch
        return SimpleNamespace(shape=shape, device=torch.device(device))

    def test_sufficient_vram_runs_untiled_without_unet_offload(self):
        events = []
        vae = _FakeVAE(use_tiling=True, outcomes=['untiled_ok'], events=events)
        unet = _FakeUNet(device='cuda:0', events=events)
        cuda = _FakeCuda([5_000_000_000, 4_200_000_000], events=events)
        gc_mod = _FakeGC(events=events)
        recorded = []
        z = self._latent()

        result = adaptive_vae_decode(
            vae, unet, vae.decode, z,
            min_free_bytes=3_500_000_000,
            cuda_module=cuda, gc_module=gc_mod, info_sink=recorded.append,
        )
        self.assertEqual(result, 'untiled_ok')
        self.assertEqual(unet.move_calls, [])
        self.assertEqual(len(vae.decode_calls), 1)
        self.assertFalse(vae.decode_calls[0]['tiling'])
        self.assertTrue(vae.use_tiling)
        info = recorded[-1]
        self.assertEqual(info['mode'], 'untiled')
        self.assertFalse(info['unet_offloaded'])
        self.assertFalse(info['oom_fallback'])
        self.assertIsNone(info['error_type'])

    def test_low_vram_offloads_unet_then_runs_untiled(self):
        events = []
        vae = _FakeVAE(use_tiling=True, outcomes=['untiled_after_offload'], events=events)
        unet = _FakeUNet(device='cuda:0', events=events)
        cuda = _FakeCuda([2_400_000_000, 4_100_000_000, 3_800_000_000], events=events)
        gc_mod = _FakeGC(events=events)
        recorded = []

        result = adaptive_vae_decode(
            vae, unet, vae.decode, self._latent(),
            min_free_bytes=3_500_000_000,
            cuda_module=cuda, gc_module=gc_mod, info_sink=recorded.append,
        )
        self.assertEqual(result, 'untiled_after_offload')
        self.assertEqual([d.type for d in unet.move_calls], ['cpu'])
        self.assertGreaterEqual(cuda.empty_cache_calls, 2)
        self.assertEqual(len(vae.decode_calls), 1)
        self.assertFalse(vae.decode_calls[0]['tiling'])
        self.assertTrue(vae.use_tiling)
        info = recorded[-1]
        self.assertEqual(info['mode'], 'untiled')
        self.assertTrue(info['unet_offloaded'])
        self.assertFalse(info['oom_fallback'])
        self.assertEqual(info['free_vram_before_bytes'], 2_400_000_000)
        self.assertEqual(info['free_vram_after_offload_bytes'], 4_100_000_000)
        self.assertEqual(info['free_vram_after_bytes'], 3_800_000_000)

    def test_insufficient_vram_after_offload_runs_tiled_directly(self):
        events = []
        vae = _FakeVAE(use_tiling=True, outcomes=['tiled_ok'], events=events)
        unet = _FakeUNet(device='cuda:0', events=events)
        cuda = _FakeCuda([1_500_000_000, 3_100_000_000, 2_900_000_000], events=events)
        gc_mod = _FakeGC(events=events)
        recorded = []

        result = adaptive_vae_decode(
            vae, unet, vae.decode, self._latent(),
            min_free_bytes=3_500_000_000,
            cuda_module=cuda, gc_module=gc_mod, info_sink=recorded.append,
        )
        self.assertEqual(result, 'tiled_ok')
        self.assertEqual([d.type for d in unet.move_calls], ['cpu'])
        self.assertEqual(len(vae.decode_calls), 1)
        self.assertTrue(vae.decode_calls[0]['tiling'])
        self.assertEqual(recorded[-1]['mode'], 'tiled_direct')
        self.assertTrue(recorded[-1]['unet_offloaded'])
        self.assertFalse(recorded[-1]['oom_fallback'])

    def test_untiled_oom_cleans_up_and_falls_back_to_tiled_with_same_latent(self):
        import torch
        events = []
        oom = torch.cuda.OutOfMemoryError('CUDA out of memory')
        vae = _FakeVAE(use_tiling=True, outcomes=[oom, 'fallback_ok'], events=events)
        unet = _FakeUNet(device='cuda:0', events=events)
        cuda = _FakeCuda([2_500_000_000, 4_000_000_000, 3_700_000_000], events=events)
        gc_mod = _FakeGC(events=events)
        recorded = []
        z = self._latent()

        result = adaptive_vae_decode(
            vae, unet, vae.decode, z,
            min_free_bytes=3_500_000_000,
            cuda_module=cuda, gc_module=gc_mod, info_sink=recorded.append,
        )
        self.assertEqual(result, 'fallback_ok')
        self.assertEqual(len(vae.decode_calls), 2)
        self.assertFalse(vae.decode_calls[0]['tiling'])
        self.assertTrue(vae.decode_calls[1]['tiling'])
        self.assertIs(vae.decode_calls[0]['z'], z)
        self.assertIs(vae.decode_calls[1]['z'], z)
        self.assertEqual(gc_mod.calls, 1)
        self.assertTrue(vae.use_tiling)
        # Verify exact cleanup order: failed untiled decode -> gc.collect -> empty_cache -> tiled fallback
        idx_fail = events.index('vae.decode:tiling=False')
        idx_gc = events.index('gc.collect')
        idx_cache = events.index('cuda.empty_cache', idx_gc)
        idx_fallback = events.index('vae.decode:tiling=True')
        self.assertLess(idx_fail, idx_gc)
        self.assertLess(idx_gc, idx_cache)
        self.assertLess(idx_cache, idx_fallback)
        info = recorded[-1]
        self.assertEqual(info['mode'], 'tiled_fallback')
        self.assertTrue(info['oom_fallback'])
        self.assertIsNone(info['error_type'])

    def test_double_oom_propagates_and_restores_tiling(self):
        import torch
        oom1 = torch.cuda.OutOfMemoryError('untiled OOM')
        oom2 = torch.cuda.OutOfMemoryError('tiled OOM')
        vae = _FakeVAE(use_tiling=True, outcomes=[oom1, oom2])
        unet = _FakeUNet(device='cuda:0')
        cuda = _FakeCuda([4_500_000_000, 2_000_000_000])
        gc_mod = _FakeGC()
        recorded = []

        with self.assertRaises(torch.cuda.OutOfMemoryError):
            adaptive_vae_decode(
                vae, unet, vae.decode, self._latent(),
                min_free_bytes=3_500_000_000,
                cuda_module=cuda, gc_module=gc_mod, info_sink=recorded.append,
            )
        self.assertEqual(len(vae.decode_calls), 2)
        self.assertTrue(vae.use_tiling)
        self.assertEqual([d.type for d in unet.move_calls], ['cpu'])
        self.assertEqual(recorded[-1]['mode'], 'tiled_fallback')
        self.assertTrue(recorded[-1]['oom_fallback'])
        self.assertEqual(recorded[-1]['error_type'], 'OutOfMemoryError')

    def test_non_oom_exception_does_not_fallback_and_restores_tiling(self):
        vae = _FakeVAE(use_tiling=True, outcomes=[ValueError('bad latent shape')])
        unet = _FakeUNet(device='cuda:0')
        cuda = _FakeCuda([5_000_000_000, 4_800_000_000])
        gc_mod = _FakeGC()
        recorded = []

        with self.assertRaises(ValueError):
            adaptive_vae_decode(
                vae, unet, vae.decode, self._latent(),
                min_free_bytes=3_500_000_000,
                cuda_module=cuda, gc_module=gc_mod, info_sink=recorded.append,
            )
        self.assertEqual(len(vae.decode_calls), 1)
        self.assertEqual(gc_mod.calls, 0)
        self.assertTrue(vae.use_tiling)
        self.assertFalse(recorded[-1]['oom_fallback'])
        self.assertEqual(recorded[-1]['error_type'], 'ValueError')

    def test_initial_tiling_false_is_restored_after_tiled_direct_and_fallback(self):
        import torch
        vae_direct = _FakeVAE(use_tiling=False, outcomes=['ok'])
        cuda_direct = _FakeCuda([1_000_000_000, 2_000_000_000, 1_900_000_000])
        adaptive_vae_decode(
            vae_direct, _FakeUNet('cuda:0'), vae_direct.decode, self._latent(),
            min_free_bytes=3_500_000_000, cuda_module=cuda_direct, gc_module=_FakeGC(),
        )
        self.assertTrue(vae_direct.decode_calls[0]['tiling'])
        self.assertFalse(vae_direct.use_tiling)

        vae_fb = _FakeVAE(use_tiling=False, outcomes=[torch.cuda.OutOfMemoryError('oom'), 'ok'])
        cuda_fb = _FakeCuda([5_000_000_000, 4_000_000_000])
        adaptive_vae_decode(
            vae_fb, _FakeUNet('cuda:0'), vae_fb.decode, self._latent(),
            min_free_bytes=3_500_000_000, cuda_module=cuda_fb, gc_module=_FakeGC(),
        )
        self.assertTrue(vae_fb.decode_calls[1]['tiling'])
        self.assertFalse(vae_fb.use_tiling)

    def test_multi_case_pipeline_reuse_preserves_tiled_encode_and_lazy_unet_restore(self):
        import torch
        events = []
        vae = _FakeVAE(use_tiling=True, outcomes=['case1', 'case2'], events=events)
        unet = _FakeUNet(device='cuda:0', events=events)
        cuda = _FakeCuda([2_200_000_000, 4_100_000_000, 3_900_000_000,
                          2_200_000_000, 4_100_000_000, 3_900_000_000], events=events)
        gc_mod = _FakeGC(events=events)
        orig_unet_forward = unet.forward
        unet.forward = types.MethodType(wrap_unet_forward(unet, orig_unet_forward, cuda_module=cuda), unet)
        orig_vae_decode = vae.decode
        decode_history = []
        vae.decode = types.MethodType(
            lambda _, z, return_dict=True, generator=None: adaptive_vae_decode(
                vae, unet, orig_vae_decode, z,
                return_dict=return_dict, generator=generator,
                min_free_bytes=3_500_000_000, cuda_module=cuda, gc_module=gc_mod,
                info_sink=decode_history.append,
            ),
            vae,
        )

        # Case 1: encode (tiled) -> 3 denoising steps -> decode (offloads UNet, untiled)
        sample = SimpleNamespace(shape=(1, 9, 128, 96), device=torch.device('cuda:0'))
        vae.encode(sample)
        for step in range(3):
            unet.forward(sample, step, encoder_hidden_states=None, return_dict=False)
        out1 = vae.decode(self._latent())

        self.assertEqual(out1, 'case1')
        self.assertEqual(unet.device, torch.device('cpu'))
        self.assertEqual([d.type for d in unet.move_calls], ['cpu'])
        self.assertTrue(vae.use_tiling)

        # Case 2: encode MUST still see use_tiling=True; UNet lazily restores on step 0 only
        vae.encode(sample)
        for step in range(3):
            unet.forward(sample, step, encoder_hidden_states=None, return_dict=False)
        out2 = vae.decode(self._latent())

        self.assertEqual(out2, 'case2')
        self.assertEqual(vae.encode_tiling_history, [True, True])
        self.assertEqual([str(d) for d in unet.move_calls], ['cpu', 'cuda:0', 'cpu'])
        self.assertEqual([d['tiling'] for d in vae.decode_calls], [False, False])
        self.assertEqual(len(decode_history), 2)
        self.assertTrue(vae.use_tiling)

    def test_unet_on_cpu_restores_on_first_forward_and_skips_subsequent_moves(self):
        import torch
        unet = _FakeUNet(device='cpu')
        cuda = _FakeCuda([5_000_000_000], current_index=0)
        unet.forward = types.MethodType(wrap_unet_forward(unet, unet.forward, cuda_module=cuda), unet)
        sample = SimpleNamespace(shape=(1, 9, 16, 16), device=torch.device('cuda:0'))

        for step in range(5):
            unet.forward(sample, step, encoder_hidden_states=None, return_dict=False)

        self.assertEqual(unet.move_calls, [torch.device('cuda:0')])
        self.assertEqual(len(unet.forward_calls), 5)

    def test_cuda_and_cuda0_comparison_avoids_redundant_moves_and_distinguishes_cuda1(self):
        import torch
        cuda0 = _FakeCuda([5_000_000_000], current_index=0)
        unet = _FakeUNet(device='cuda:0')

        self.assertFalse(ensure_unet_device(unet, torch.device('cuda'), cuda_module=cuda0))
        self.assertEqual(unet.move_calls, [])

        self.assertTrue(ensure_unet_device(unet, torch.device('cuda:1'), cuda_module=cuda0))
        self.assertEqual(unet.move_calls, [torch.device('cuda:1')])

    def test_decode_info_records_all_required_fields(self):
        recorded = []
        vae = _FakeVAE(use_tiling=True, outcomes=['ok'])
        unet = _FakeUNet(device='cuda:0')
        cuda = _FakeCuda([4_500_000_000, 4_100_000_000])
        adaptive_vae_decode(
            vae, unet, vae.decode, self._latent(),
            min_free_bytes=3_500_000_000, cuda_module=cuda, gc_module=_FakeGC(), info_sink=recorded.append,
        )
        info = recorded[-1]
        for key in (
            'mode',
            'unet_offloaded',
            'oom_fallback',
            'initial_tiling',
            'final_tiling',
            'free_vram_before_bytes',
            'free_vram_after_offload_bytes',
            'free_vram_after_bytes',
            'allocated_vram_before_bytes',
            'reserved_vram_before_bytes',
            'allocated_vram_after_bytes',
            'reserved_vram_after_bytes',
            'peak_allocated_vram_bytes',
            'peak_reserved_vram_bytes',
            'threshold_bytes',
            'elapsed_seconds',
            'error_type',
            'error_stage',
        ):
            self.assertIn(key, info)
        self.assertTrue(info['initial_tiling'])
        self.assertTrue(info['final_tiling'])
        self.assertEqual(info['allocated_vram_before_bytes'], 2_000_000_000)
        self.assertEqual(info['reserved_vram_before_bytes'], 2_500_000_000)
        self.assertEqual(info['peak_allocated_vram_bytes'], 3_100_000_000)
        self.assertEqual(info['peak_reserved_vram_bytes'], 3_400_000_000)
        self.assertIsNone(info['error_stage'])
        self.assertEqual(info['threshold_bytes'], 3_500_000_000)
        self.assertGreaterEqual(info['elapsed_seconds'], 0.0)

    def test_unet_offload_failure_reports_stage_restores_tiling_and_recovers_on_next_case(self):
        import torch
        vae = _FakeVAE(use_tiling=True, outcomes=['case2_ok'])
        unet = _FakeUNet(device='cuda:0', fail_on_to=[RuntimeError('CPU offload failed'), None])
        cuda = _FakeCuda([2_000_000_000, 1_900_000_000])
        recorded = []

        with self.assertRaises(RuntimeError) as ctx:
            adaptive_vae_decode(
                vae, unet, vae.decode, self._latent(),
                min_free_bytes=3_500_000_000, cuda_module=cuda, gc_module=_FakeGC(), info_sink=recorded.append,
            )
        self.assertTrue(vae.use_tiling)
        self.assertEqual(recorded[-1]['error_type'], 'RuntimeError')
        self.assertEqual(recorded[-1]['error_stage'], 'unet_offload')
        self.assertFalse(recorded[-1]['unet_offloaded'])
        self.assertIn('stage=unet_offload', getattr(ctx.exception, '__notes__', ()))
        self.assertTrue(getattr(unet, '_tryfit_device_uncertain', False))

        # Even though unet.device stayed cuda:0, _tryfit_device_uncertain forces a full restore before next case.
        self.assertTrue(ensure_unet_device(unet, torch.device('cuda:0'), cuda_module=cuda))
        self.assertFalse(getattr(unet, '_tryfit_device_uncertain', True))

    def test_unet_gpu_restore_failure_preserves_oom_type_reports_stage_and_recovers(self):
        import torch
        unet = _FakeUNet(device='cpu', fail_on_to=[torch.cuda.OutOfMemoryError('restore OOM'), None])
        cuda = _FakeCuda([5_000_000_000], current_index=0)
        stages = []
        wrapped = wrap_unet_forward(unet, unet.forward, cuda_module=cuda, on_error_stage=stages.append)
        unet.forward = types.MethodType(wrapped, unet)
        sample = SimpleNamespace(shape=(1, 9, 16, 16), device=torch.device('cuda:0'))

        with self.assertRaises(torch.cuda.OutOfMemoryError) as ctx:
            unet.forward(sample, 0, encoder_hidden_states=None, return_dict=False)
        self.assertEqual(stages, ['unet_restore'])
        self.assertIn('stage=unet_restore', getattr(ctx.exception, '__notes__', ()))
        self.assertTrue(getattr(unet, '_tryfit_device_uncertain', False))
        self.assertEqual(len(unet.forward_calls), 0)

        # Next call retries and succeeds cleanly.
        unet.forward(sample, 0, encoder_hidden_states=None, return_dict=False)
        self.assertFalse(getattr(unet, '_tryfit_device_uncertain', True))
        self.assertEqual(unet.device, torch.device('cuda:0'))
        self.assertEqual(len(unet.forward_calls), 1)

    def test_pipeline_reusable_after_decode_failure_and_restores_encode_tiling(self):
        import torch
        vae = _FakeVAE(use_tiling=True, outcomes=[ValueError('transient decode error'), 'case2_ok'])
        unet = _FakeUNet(device='cuda:0')
        cuda = _FakeCuda([2_200_000_000, 4_100_000_000, 3_900_000_000,
                          4_500_000_000, 4_200_000_000])
        orig_unet_forward = unet.forward
        unet.forward = types.MethodType(wrap_unet_forward(unet, orig_unet_forward, cuda_module=cuda), unet)
        orig_vae_decode = vae.decode
        history = []
        vae.decode = types.MethodType(
            lambda _, z, return_dict=True, generator=None: adaptive_vae_decode(
                vae, unet, orig_vae_decode, z,
                return_dict=return_dict, generator=generator,
                min_free_bytes=3_500_000_000, cuda_module=cuda, gc_module=_FakeGC(), info_sink=history.append,
            ),
            vae,
        )
        sample = SimpleNamespace(shape=(1, 9, 128, 96), device=torch.device('cuda:0'))

        vae.encode(sample)
        unet.forward(sample, 0, encoder_hidden_states=None, return_dict=False)
        with self.assertRaises(ValueError):
            vae.decode(self._latent())
        self.assertTrue(vae.use_tiling)
        self.assertEqual(history[-1]['error_type'], 'ValueError')
        self.assertEqual(history[-1]['error_stage'], 'untiled_decode')

        # Case 2 must still encode with tiling=True, restore UNet to CUDA, and succeed.
        vae.encode(sample)
        unet.forward(sample, 0, encoder_hidden_states=None, return_dict=False)
        out2 = vae.decode(self._latent())
        self.assertEqual(out2, 'case2_ok')
        self.assertEqual(vae.encode_tiling_history, [True, True])
        self.assertIsNone(history[-1]['error_type'])
        self.assertIsNone(history[-1]['error_stage'])

    def test_post_decode_telemetry_failure_does_not_mask_result_or_original_error(self):
        vae = _FakeVAE(use_tiling=True, outcomes=['ok', RuntimeError('decode boom')])
        unet = _FakeUNet(device='cuda:0')
        cuda = _FakeCuda([5_000_000_000], fail_after_probes=1)
        recorded = []

        out = adaptive_vae_decode(
            vae, unet, vae.decode, self._latent(),
            min_free_bytes=3_500_000_000, cuda_module=cuda, gc_module=_FakeGC(), info_sink=recorded.append,
        )
        self.assertEqual(out, 'ok')
        self.assertIsNone(recorded[-1]['free_vram_after_bytes'])
        self.assertIsNone(recorded[-1]['error_type'])

        cuda2 = _FakeCuda([5_000_000_000], fail_after_probes=1)
        with self.assertRaises(RuntimeError) as ctx:
            adaptive_vae_decode(
                vae, unet, vae.decode, self._latent(),
                min_free_bytes=3_500_000_000, cuda_module=cuda2, gc_module=_FakeGC(), info_sink=recorded.append,
            )
        self.assertEqual(str(ctx.exception), 'decode boom')
        self.assertEqual(recorded[-1]['error_stage'], 'untiled_decode')

    def test_threshold_scales_with_latent_area_and_preserves_fixed_overhead(self):
        base = estimate_untiled_decode_free_bytes(SimpleNamespace(shape=(1, 4, 128, 96)))
        self.assertEqual(base, UNTILED_DECODE_SAFE_FREE_BYTES)

        double_area = estimate_untiled_decode_free_bytes(SimpleNamespace(shape=(1, 4, 128, 192)))
        self.assertGreater(double_area, base)
        self.assertEqual(
            double_area - UNTILED_DECODE_FIXED_OVERHEAD_BYTES,
            2 * (base - UNTILED_DECODE_FIXED_OVERHEAD_BYTES),
        )

        tiny = estimate_untiled_decode_free_bytes(SimpleNamespace(shape=(1, 4, 16, 16)))
        self.assertGreater(tiny, UNTILED_DECODE_FIXED_OVERHEAD_BYTES)
        self.assertEqual(estimate_untiled_decode_free_bytes(SimpleNamespace(shape=(BASE_LATENT_AREA,))), base)


@unittest.skipUnless(
    os.environ.get('TRYFIT_RUN_GPU_TESTS') == '1' and importlib.util.find_spec('diffusers'),
    'Explicit GPU integration flag TRYFIT_RUN_GPU_TESTS=1 and CatVTON environment required',
)
class AdaptiveVaeDecodeGpuIntegrationTests(unittest.TestCase):
    def test_local_pipeline_adaptive_decode_smoke(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest('CUDA unavailable')
        weights = Path(__file__).resolve().parents[1] / 'models/catvton'
        if not weights.is_dir():
            self.skipTest('CatVTON weights unavailable')
        from catvton_probe import pipeline
        model = pipeline(weights)
        latent = torch.zeros((1, 4, 128, 96), device='cuda', dtype=model.weight_dtype)
        with torch.no_grad():
            out = model.vae.decode(latent).sample
        self.assertEqual(tuple(out.shape), (1, 3, 1024, 768))
        self.assertTrue(model.vae.use_tiling)
        self.assertIsNotNone(model.last_decode_info)
        self.assertIn(model.last_decode_info['mode'], {'untiled', 'tiled_direct', 'tiled_fallback'})


if __name__=='__main__':unittest.main()
