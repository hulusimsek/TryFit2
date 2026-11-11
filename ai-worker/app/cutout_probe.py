"""Diagnostic only: treat worn-source SAM cutouts as flat-lay inputs.

This changes source pose and when masking occurs relative to pre-resize.
The pinned model has no independent photo-type embedding.
The cutouts are not actual flat-lay product photographs.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from experiment import load_rgb, sha256, write_json, run_experiment, evaluate
from outfit import create_pipeline


def run():
    root = Path(__file__).resolve().parents[2]
    ids = {'oversize-hoodie', 'denim-jacket', 'hooded-sweatshirt'}
    original = root / 'evaluation/manifests/trendyol-10.actual.json'
    manifest = json.loads(original.read_text(encoding='utf-8'))
    provenance = {}
    for case in manifest['cases']:
        if case['id'] not in ids:
            continue
        directory = root / ('runs/source-extraction-' + case['id'] + '-refined')
        meta = json.loads((directory / 'extraction.json').read_text(encoding='utf-8'))
        source = root / case['image']
        if sha256(source) != meta['annotation']['image_sha256'] or sha256(directory/'mask.png') != meta['mask_sha256']:
            raise ValueError('Source or mask changed')
        mask = np.asarray(Image.open(directory/'mask.png').convert('L')) != 0
        pixels = np.asarray(load_rgb(source))
        cutout = load_rgb(directory/'isolated.png')
        if not np.array_equal(np.asarray(cutout), np.where(mask[...,None], pixels, 127)):
            raise ValueError('Cutout differs from frozen mask applied to original photo')
        provenance[case['id']] = {'extraction': str(directory.relative_to(root)), 'original_source': case['image'],
                                  'original_sha256': sha256(source), 'cutout_sha256': sha256(directory/'isolated.png')}
        case['image'] = (directory/'isolated.png').relative_to(root).as_posix()
        case['image_sha256'] = sha256(directory/'isolated.png')
        case['garment_photo_type'] = 'flat-lay'
        case['source_notes'] += ' DIAGNOSTIC: SAM cutout of worn photo treated as flat-lay; not a real flat-lay photo.'
    manifest['purpose'] = 'Bounded cutout/photo-type probe, not a replacement ten-case baseline'
    path = root / 'runs/cutout-probe.manifest.json'
    write_json(path, manifest)
    result = run_experiment(root, path, root/'ai-worker/models', selected_ids=sorted(ids), pipeline_factory=create_pipeline)
    write_json(result/'probe.json', {'baseline':'runs/20261110T095148Z-cf9135a6',
        'controlled_changes':['SAM mask before pre-resize instead of after pre-resize', 'flat-lay preprocessing branch: skip source masking and use dummy source pose'],
        'note':'No independent photo-type embedding exists in the pinned model; this largely overlaps the no-source-pose test.',
        'unchanged':['target', 'category', 'seed42', '30 steps', 'guidance1.5'], 'inputs':provenance})
    evaluate(result)
    (root/'runs/latest-cutout-probe.txt').write_text(str(result),encoding='utf-8')
    return result


if __name__ == '__main__':
    run()
