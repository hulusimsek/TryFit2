"""Diagnose skirt-detail loss on original and explicitly synthetic short-top targets."""
import argparse
import json
import time
import traceback
import uuid
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from experiment import load_rgb, local_path, sha256, write_json
from masked_outfit import MaskedOutfitPipeline


def run(*, source_framing=False):
    root = Path(__file__).resolve().parents[2]
    manifest = root / 'evaluation/manifests/trendyol-10.actual.json'
    garment = next(c for c in json.loads(manifest.read_text(encoding='utf-8'))['cases'] if c['id'] == 'skirt')
    targets = [('long-top', 'data/first-outfit/avatar-baseline.png'),
               ('short-top', 'data/waist-control/short-top.png')]
    if source_framing:
        targets=[('short-top-full-cutout','data/waist-control/short-top.png'),
                 ('short-top-cropped-cutout','data/waist-control/short-top.png')]
    dest = root / 'runs' / ('skirt-waist-' + uuid.uuid4().hex[:8]); dest.mkdir(parents=True)
    settings = dict(seed=42, num_timesteps=30, guidance_scale=1.5, num_samples=1, segmentation_free=False)
    record = {'status': 'initializing', 'quality_status': 'not_reviewed', 'cases': [], 'settings': settings,
              'preserve_upper': True, 'output_compositing': False, 'source': garment,
              'protected_regions':['face','hair','top','arms','hands','torso'],
              'source_framing_probe':source_framing,
              'implementation_sha256': {name: sha256(root / 'ai-worker/app' / name) for name in
                  ['skirt_waist_probe.py', 'masked_outfit.py', 'upper_preservation.py']},
              'target_generation': json.loads((root / 'evaluation/annotations/waist-control-generation.json').read_text(encoding='utf-8')),
              'limits': ['Short target is an imagegen edit, never a try-on result; pixels beyond the top may differ',
                         'Exploratory visibility control, not strict causal attribution or quality gate',
                         'Same real skirt source/mask and settings; no target skirt or buckle is supplied']}
    write_json(dest / 'run.json', record)
    try:
        model = MaskedOutfitPipeline(root, [garment], allow_masked_target=True, preserve_upper=True)
        record.update(status='running', source_extractions=model.provenance)
        for name, path in targets:
            model.bottom_source_cutout=('crop' if 'cropped' in name else 'full') if source_framing else None
            person_path = local_path(root, path)
            case = {'id': name, 'status': 'running', 'input': path, 'input_sha256': sha256(person_path)}
            record['cases'].append(case); write_json(dest / 'run.json', record)
            start = time.perf_counter()
            result = model(person_image=load_rgb(person_path), garment_image=load_rgb(root / garment['image']),
                           category='bottoms', garment_photo_type=garment['garment_photo_type'], **settings).images[0]
            output = dest / (name + '.png'); result.save(output)
            case.update(status='completed', output=output.name, output_sha256=sha256(output),
                        source_preparation=model.last_source_preparation,
                        elapsed_seconds=round(time.perf_counter() - start, 2))
            write_json(dest / 'run.json', record)
        panels = [('SKIRT SOURCE', load_rgb(root / garment['image']))]
        for case in record['cases']:
            panels += [(case['id'] + ' INPUT', load_rgb(root / case['input'])),
                       (case['id'] + ' OUTPUT', load_rgb(dest / case['output']))]
        board = Image.new('RGB', (320 * len(panels), 540), 'white'); draw = ImageDraw.Draw(board)
        for index, (title, picture) in enumerate(panels):
            thumb = ImageOps.contain(picture, (310, 500))
            board.paste(thumb, (index * 320 + (320 - thumb.width) // 2, 30))
            draw.text((index * 320 + 6, 8), title, fill='black')
        board.save(dest / 'comparison.jpg')
        record['status'] = 'completed'
    except Exception as error:
        record.update(status='failed', error=str(error), traceback=traceback.format_exc())
        if record['cases'] and record['cases'][-1]['status'] == 'running':
            record['cases'][-1]['status'] = 'failed'
        raise
    finally:
        write_json(dest / 'run.json', record); print('RUN_DIR=' + str(dest), flush=True)
    return dest


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-framing',action='store_true')
    run(source_framing=parser.parse_args().source_framing)
