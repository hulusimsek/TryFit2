import json
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from local_skirt_inputs import prepare_skirt_masks, skirt_inputs
from catvton_inputs import letterbox
import local_skirt
from experiment import sha256


class SkirtRuntimeTests(unittest.TestCase):
    def labels(self):
        labels=np.zeros((80,60),dtype='uint8');labels[5:40,15:45]=3
        labels[40:65,15:45]=6;labels[65:73,17:43]=14;labels[73:78,17:43]=15
        labels[30:45,7:12]=13
        return labels

    def test_tucking_releases_only_lower_top_and_keeps_hands_feet_protected(self):
        labels=self.labels()
        plain,protected,_=skirt_inputs(labels)
        tucked,tucked_mask,fade=skirt_inputs(labels,tuck_top=True)
        self.assertTrue((np.asarray(protected)[labels==3]==255).all())
        self.assertEqual(np.asarray(tucked_mask)[20,30],255)
        self.assertEqual(np.asarray(tucked_mask)[38,30],0)
        self.assertTrue((np.asarray(tucked_mask)[np.isin(labels,[13,15])]==255).all())
        self.assertTrue(tucked['tuck_top']);self.assertIsNone(plain['tuck_cut_row'])
        self.assertEqual(np.asarray(fade)[70,0],0)
        self.assertEqual(np.asarray(fade)[50,30],255)

    def test_missing_body_parts_fail_before_generation(self):
        for missing in [3,6,15]:
            labels=self.labels();labels[labels==missing]=0
            if missing==6:labels[labels==14]=0
            with self.assertRaises(ValueError):skirt_inputs(labels)

    def test_prepared_artifact_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'selection.json').write_text('{}')
            names=['01-top.png','cat-target.png','cat-hard-mask.png','cat-soft-mask.png','cat-preserve.png','cat-condition.png']
            for name in names:(root/name).write_bytes(b'validation-only')
            (root/'skirt-handoff.json').write_text(json.dumps({'selection_sha256':sha256(root/'selection.json'),
                'files':{name:sha256(root/name) for name in names}}))
            local_skirt.verify_prepared(root)
            (root/'cat-soft-mask.png').write_bytes(b'changed')
            with self.assertRaises(ValueError):local_skirt.verify_prepared(root)

    def test_child_failure_does_not_create_a_success_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);job=root/'runs/local-jobs'/('a'*32);job.mkdir(parents=True)
            python=root/'.venv-catvton/Scripts/python.exe';python.parent.mkdir(parents=True);python.touch()
            with patch.object(local_skirt,'ROOT',root),patch.object(local_skirt.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'upper')) as run:
                with self.assertRaises(subprocess.CalledProcessError):local_skirt.run(job)
                self.assertEqual(run.call_count,1)
            self.assertFalse((job/'result.png').exists());self.assertFalse((job/'outcome.json').exists())

    def test_outer_background_never_enters_partial_halo_or_lower_leg_paint_area(self):
        labels=np.zeros((864,576),dtype='uint8')
        labels[80:350,210:366]=3
        labels[350:780,215:361]=6
        labels[780:840,220:356]=15
        labels[240:470,170:195]=13
        target_img=Image.new('RGB',(576,864),(208,207,208))
        for tuck_top in (False,True):
            _,hard,soft,_,_,_,transform=prepare_skirt_masks(target_img,labels,tuck_top=tuck_top)
            self.assertEqual(transform['original_size'],[576,864])
            soft_arr=np.asarray(soft)
            hard_arr=np.asarray(hard)
            self.assertTrue(np.array_equal(hard_arr,(soft_arr>=128).astype('uint8')*255))
            bg_canvas,_=letterbox(Image.fromarray((labels==0).astype('uint8')*255),(768,1024),mask=True)
            bg_mask=np.asarray(bg_canvas)==255
            # Zero partial-alpha (1..254) pixels on outer background so CatVTON & repaint share exact boundary.
            partial_bg=((soft_arr>0)&(soft_arr<255)&bg_mask)
            self.assertEqual(int(partial_bg.sum()),0)
            # Below the mini-skirt hem (lower thighs/calves/ankles), no outer background enters >=128.
            self.assertEqual(int(((hard_arr[640:,:]>0) & bg_mask[640:,:]).sum()),0)
            # Far outside hip flare, no background enters >=128.
            self.assertEqual(int(((hard_arr[:,:250]>0) & bg_mask[:,:250]).sum()),0)
            if tuck_top:
                # Waist seam interior feather still operates inside top below cut (row ~290 @864 -> ~344 @1024).
                cut_rows=soft_arr[340:360,384]
                self.assertTrue(((cut_rows>0)&(cut_rows<255)).any())
            # Ankle seam interior feather above feet still operates inside lower legs.
            ankle_rows=soft_arr[910:930,384]
            self.assertTrue(((ankle_rows>0)&(ankle_rows<255)).any())

    def test_local_skirt_run_unletterboxes_576x864_result_while_preserving_debug_repaint(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);job=root/'runs/local-jobs'/('b'*32);job.mkdir(parents=True)
            python=root/'.venv-catvton/Scripts/python.exe';python.parent.mkdir(parents=True);python.touch()
            (job/'selection.json').write_text(json.dumps({'tuck_top':True}),encoding='utf-8')
            names=['01-top.png','cat-target.png','cat-hard-mask.png','cat-soft-mask.png','cat-preserve.png','cat-condition.png']
            for name in names:Image.new('RGB',(10,10),(10,20,30)).save(job/name)
            _,transform=letterbox(Image.new('RGB',(576,864)),(768,1024))
            handoff={'selection_sha256':sha256(job/'selection.json'),
                     'files':{name:sha256(job/name) for name in names},
                     'target_transform':transform}
            (job/'skirt-handoff.json').write_text(json.dumps(handoff),encoding='utf-8')
            repaint_canvas=Image.new('RGB',(768,1024),(220,220,220))
            repaint_canvas.paste(Image.new('RGB',(683,1024),(28,32,38)),(42,0))
            repaint_canvas.save(job/'02-skirt-raw.png')
            repaint_canvas.save(job/'02-skirt-repaint.png')
            (job/'catvton-outcome.json').write_text(json.dumps({
                'status':'completed',
                'raw_sha256':sha256(job/'02-skirt-raw.png'),
                'output_sha256':sha256(job/'02-skirt-repaint.png'),
                'handoff_sha256':sha256(job/'skirt-handoff.json'),
            }),encoding='utf-8')
            with patch.object(local_skirt,'ROOT',root),patch.object(local_skirt.subprocess,'run'):
                local_skirt.run(job)
            with Image.open(job/'02-skirt-repaint.png') as rep_im:
                self.assertEqual(rep_im.size,(768,1024))
            with Image.open(job/'result.png') as res_im:
                self.assertEqual(res_im.size,(576,864))
                self.assertFalse(np.all(np.asarray(res_im)==(220,220,220),axis=2).any())
                self.assertEqual(res_im.getpixel((288,432)),(28,32,38))

    def test_aline_skirt_envelope_does_not_taper_along_thighs_and_stays_binary(self):
        labels=np.zeros((864,576),dtype='uint8')
        # Anatomical hip widening then sharp thigh taper toward knees/ankles.
        for y in range(353,771):
            if y<=420:half=89
            elif y<=530:half=max(62,round(89-(y-420)*0.22))
            else:half=max(32,round(65-(y-530)*0.12))
            labels[y,288-half:288+half]=6
        labels[139:388,225:351]=3
        labels[771:835,235:341]=15
        # Hanging arms/hands separated from hips, ending around fingertip row 491.
        labels[268:491,170:188]=12
        labels[268:491,388:406]=13
        target_img=Image.new('RGB',(576,864),(208,207,208))

        def span(arr,y):
            xs=np.where(arr[y]>0)[0]
            return int(xs[-1]-xs[0]+1) if len(xs) else 0

        for tuck_top in (False,True):
            _,hard,soft,preserve,_,annotation,_=prepare_skirt_masks(target_img,labels,tuck_top=tuck_top)
            soft_arr=np.asarray(soft)
            hard_arr=np.asarray(hard)
            pres_canvas,_=letterbox(preserve,(768,1024),mask=True)
            bg_canvas,_=letterbox(Image.fromarray((labels==0).astype('uint8')*255),(768,1024),mask=True)
            bg_mask=np.asarray(bg_canvas)==255

            # Outer boundary remains strictly binary 0/255 (previous dark-halo fix preserved).
            self.assertEqual(int(((soft_arr>0)&(soft_arr<255)&bg_mask).sum()),0)
            self.assertTrue(np.array_equal(hard_arr,(soft_arr>=128).astype('uint8')*255))
            # Protected regions never enter soft or hard masks.
            self.assertEqual(int(((soft_arr>0)&(np.asarray(pres_canvas)>0)).sum()),0)

            waist_864=annotation['tuck_cut_row'] if tuck_top else 387
            hip_864=waist_864+round(864*.13)
            hem_864=waist_864+round(864*.21)
            sy=1024/864.0
            waist_w=span(hard_arr,round((waist_864+(12 if tuck_top else 0))*sy))
            hip_w=span(hard_arr,round(hip_864*sy))
            mid_w=span(hard_arr,round(((hip_864+hem_864)/2)*sy))
            hem_w=span(hard_arr,round(hem_864*sy))
            # A-line envelope never collapses inward toward tapering thighs and stays wide at hem.
            self.assertGreater(waist_w,0)
            self.assertGreaterEqual(hip_w,waist_w)
            self.assertGreaterEqual(mid_w,hip_w)
            self.assertGreaterEqual(hem_w,hip_w)
            # Lower leg region well below hem still blocks outer background painting.
            below_hem=round((hem_864+35)*sy)
            self.assertEqual(int(((hard_arr[below_hem:,:]>0)&bg_mask[below_hem:,:]).sum()),0)

    def test_close_arms_and_hands_near_fuller_hips_never_enter_skirt_mask(self):
        labels=np.zeros((864,576),dtype='uint8')
        labels[138:378,200:376]=3
        for y in range(365,770):
            half=112 if y<=435 else max(52,round(112-(y-435)*0.25))
            labels[y,288-half:288+half]=6
        labels[770:835,230:346]=15
        # Only 4 px gap from widest fuller hip (176..400 vs 171 / 405).
        labels[265:440,152:172]=12
        labels[440:492,155:172]=13
        labels[265:440,404:424]=12
        labels[440:492,404:421]=13
        target_img=Image.new('RGB',(576,864),(208,207,208))

        for tuck_top in (False,True):
            _,hard,soft,preserve,_,_,_=prepare_skirt_masks(target_img,labels,tuck_top=tuck_top)
            soft_arr=np.asarray(soft)
            hard_arr=np.asarray(hard)
            pres_canvas,_=letterbox(preserve,(768,1024),mask=True)
            arm_canvas,_=letterbox(Image.fromarray(np.isin(labels,[12,13]).astype('uint8')*255),(768,1024),mask=True)
            arm_mask=np.asarray(arm_canvas)>0
            self.assertEqual(int(((soft_arr>0)&(np.asarray(pres_canvas)>0)).sum()),0)
            self.assertEqual(int(((soft_arr>0)&arm_mask).sum()),0)
            # Outer background mask must stay strictly between arms/hands on every arm row.
            for y in range(hard_arr.shape[0]):
                if not (hard_arr[y]>0).any() or not arm_mask[y].any():
                    continue
                mx=np.where(hard_arr[y]>0)[0]
                ax=np.where(arm_mask[y])[0]
                al=ax[ax<mx[0]];ar=ax[ax>mx[-1]]
                if len(al):self.assertGreater(int(mx[0]-al[-1]),1)
                if len(ar):self.assertGreater(int(ar[0]-mx[-1]),1)

    def test_narrow_silhouette_avoids_hem_wing_flare_and_bridges_thigh_gap(self):
        labels = np.zeros((864, 576), dtype=np.uint8)
        labels[80:350, 218:358] = 3
        # Narrow hips (155 px < 0.195 * 864) with separated slim legs below hem.
        for y in range(350, 495):
            half = int(round(77 - 12 * ((y - 350) / 145)))
            labels[y, 288 - half:288 + half] = 6
        for y in range(495, 780):
            labels[y, 224:278] = 6
            labels[y, 298:352] = 6
        labels[780:840, 226:276] = 15
        labels[780:840, 298:348] = 15
        # Hanging forearms and hands close to hips/thighs without overlapping narrow silhouette.
        labels[265:440, 178:198] = 12
        labels[440:478, 180:198] = 13
        labels[265:440, 378:398] = 12
        labels[440:478, 378:396] = 13
        target_img = Image.new('RGB', (576, 864), (208, 207, 208))
        bg_canvas, _ = letterbox(Image.fromarray((labels == 0).astype('uint8') * 255), (768, 1024), mask=True)
        outer_labels = (labels == 0).copy()
        outer_labels[495:780, 224:352] = False
        outer_bg_canvas, _ = letterbox(Image.fromarray(outer_labels.astype('uint8') * 255), (768, 1024), mask=True)
        arm_canvas, _ = letterbox(Image.fromarray(np.isin(labels, [12, 13]).astype('uint8') * 255), (768, 1024), mask=True)
        bg_mask = np.asarray(bg_canvas) > 0
        outer_bg_mask = np.asarray(outer_bg_canvas) > 0
        arm_mask = np.asarray(arm_canvas) > 0
        sy = 1024 / 864

        for tuck_top in (False, True):
            _, hard, soft, preserve, _, _, _ = prepare_skirt_masks(target_img, labels, tuck_top=tuck_top)
            soft_arr = np.asarray(soft)
            hard_arr = np.asarray(hard)
            self.assertEqual(int(((soft_arr > 0) & (soft_arr < 255) & bg_mask).sum()), 0)
            self.assertEqual(int(((soft_arr > 0) & arm_mask).sum()), 0)
            waist_864 = round(80 + 0.78 * (349 - 80)) if tuck_top else 349
            hip_864 = waist_864 + round(864 * 0.13)
            hem_864 = waist_864 + round(864 * 0.21)
            hip_w = int((hard_arr[round(hip_864 * sy)] > 0).sum())
            hem_w = int((hard_arr[round(hem_864 * sy)] > 0).sum())
            self.assertLessEqual(hem_w, hip_w)
            below_taper = round((hem_864 + round(864 * 0.015)) * sy)
            self.assertEqual(int(((hard_arr[below_taper:, :] > 0) & outer_bg_mask[below_taper:, :]).sum()), 0)
            bridge_row = round((hem_864 + round(864 * 0.02)) * sy)
            bridge_cols = np.where(hard_arr[bridge_row] > 0)[0]
            self.assertTrue(len(bridge_cols) > 0 and int(np.diff(bridge_cols).max()) == 1)

    def test_lower_records_vae_decode_and_failure_telemetry_without_gpu(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            weights = root / 'ai-worker/models/catvton'
            weights.mkdir(parents=True)
            (weights / 'provenance.json').write_text(json.dumps({'files': []}), encoding='utf-8')

            job = root / 'runs/local-jobs' / ('b' * 32)
            job.mkdir(parents=True)
            (job / 'selection.json').write_text('{}', encoding='utf-8')
            names = ['01-top.png', 'cat-target.png', 'cat-hard-mask.png', 'cat-soft-mask.png', 'cat-preserve.png', 'cat-condition.png']
            for name in names:
                mode = 'L' if 'mask' in name or 'preserve' in name else 'RGB'
                Image.new(mode, (768, 1024), 128 if mode == 'L' else (20, 30, 40)).save(job / name)
            (job / 'skirt-handoff.json').write_text(json.dumps({
                'selection_sha256': sha256(job / 'selection.json'),
                'files': {name: sha256(job / name) for name in names},
            }), encoding='utf-8')

            decode_info = {
                'mode': 'untiled',
                'unet_offloaded': True,
                'oom_fallback': False,
                'initial_tiling': True,
                'final_tiling': True,
                'error_stage': None,
            }

            class _OkModel:
                def __init__(self):
                    self.last_decode_info = decode_info
                    self.last_error_stage = None

                def __call__(self, **_kwargs):
                    return [Image.new('RGB', (768, 1024), (50, 60, 70))]

            class _FailModel:
                def __init__(self):
                    self.last_decode_info = {**decode_info, 'mode': 'tiled_fallback', 'oom_fallback': True, 'error_stage': 'tiled_fallback_decode', 'error_type': 'OutOfMemoryError'}
                    self.last_error_stage = 'tiled_fallback_decode'

                def __call__(self, **_kwargs):
                    raise RuntimeError('simulated decode failure')

            fake_utils = SimpleNamespace(repaint_result=lambda raw, _t, _m: raw)
            fake_probe = SimpleNamespace(pipeline=lambda _w: _OkModel())
            with patch.object(local_skirt, 'ROOT', root), \
                 patch.dict(sys.modules, {'utils': fake_utils, 'catvton_probe': fake_probe}), \
                 patch('torch.cuda.is_available', return_value=False):
                local_skirt.lower(job)

            ok_outcome = json.loads((job / 'catvton-outcome.json').read_text(encoding='utf-8'))
            self.assertEqual(ok_outcome['status'], 'completed')
            self.assertEqual(ok_outcome['vae_decode'], decode_info)
            self.assertIn('peak_allocated_gib', ok_outcome)
            self.assertIn('peak_reserved_gib', ok_outcome)

            fake_probe_fail = SimpleNamespace(pipeline=lambda _w: _FailModel())
            with patch.object(local_skirt, 'ROOT', root), \
                 patch.dict(sys.modules, {'utils': fake_utils, 'catvton_probe': fake_probe_fail}), \
                 patch('torch.cuda.is_available', return_value=False):
                with self.assertRaises(RuntimeError):
                    local_skirt.lower(job)

            fail_outcome = json.loads((job / 'catvton-outcome.json').read_text(encoding='utf-8'))
            self.assertEqual(fail_outcome['status'], 'failed')
            self.assertEqual(fail_outcome['error_type'], 'RuntimeError')
            self.assertEqual(fail_outcome['error_stage'], 'tiled_fallback_decode')
            self.assertEqual(fail_outcome['vae_decode']['mode'], 'tiled_fallback')


if __name__=='__main__':unittest.main()
