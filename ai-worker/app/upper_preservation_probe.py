"""Repeat only the bottom stage from completed, masked-bottom outfit runs."""
import argparse
import gc
import json
import time
import traceback
import uuid
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from experiment import load_rgb, local_path, sha256, write_json
from masked_outfit import MaskedOutfitPipeline
from outfit import validate_selection
from upper_preservation import preservation_alpha


def run(baselines, *, maskless_bottom=False, guidance_scale=None, preserve_feet=False):
    if maskless_bottom and guidance_scale is not None:
        raise ValueError('Change only one lower-stage variable per comparison')
    if guidance_scale is not None and (not np.isfinite(guidance_scale) or not 1 <= guidance_scale <= 5):
        raise ValueError('Probe guidance must be finite and between 1 and 5')
    if preserve_feet and not maskless_bottom:
        raise ValueError('Compare feet preservation against the maskless upper-constrained probe')
    root = Path(__file__).resolve().parents[2]
    dest = root / 'runs' / ('upper-preservation-' + uuid.uuid4().hex[:8])
    dest.mkdir(parents=True)
    record = {'status': 'running', 'quality_status': 'not_reviewed', 'cases': [],
              'controlled_change': 'Only bottom-stage upper-preservation flow constraint; identical saved top, source, seed and masked-target settings',
              'output_compositing': False}
    record['lower_stage_change'] = ('segmentation_free=True' if maskless_bottom else
                                    f'guidance_scale={guidance_scale}' if guidance_scale is not None else 'none')
    record['preserve_feet'] = preserve_feet
    record['preserve_feet_method'] = 'feet_and_lower_background' if preserve_feet else 'disabled'
    record['implementation_sha256'] = {name: sha256(root / 'ai-worker' / 'app' / name)
        for name in ['upper_preservation.py', 'masked_outfit.py', 'upper_preservation_probe.py']}
    if maskless_bottom or guidance_scale is not None:
        record['controlled_change'] = ('Upper constraint remains enabled as in the prior constrained run; '
            'change only ' + record['lower_stage_change'] + '. Baseline directory supplies the identical saved top and source; '
            'its previous image is unconstrained, so compare against the matching prior constrained probe for attribution.')
    if preserve_feet:
        record['controlled_change'] = ('Add only feet-interior constraint compared with matching maskless upper-constrained probe; '
            'same top, source, seed and settings. Baseline image in board is the earlier unconstrained output.')
    write_json(dest / 'run.json', record)
    try:
        for index, baseline in enumerate(baselines):
            baseline = local_path(root, Path(baseline).as_posix())
            previous = json.loads((baseline / 'run.json').read_text(encoding='utf-8'))
            original_settings = previous.get('stage_settings', {}).get('bottom', previous['settings'])
            if previous['status'] != 'completed' or (original_settings['segmentation_free'] and
                                                    not (maskless_bottom and preserve_feet)):
                raise ValueError('Completed masked-bottom baseline required, or explicit maskless-feet regression')
            selection = json.loads((baseline / 'selection.json').read_text(encoding='utf-8'))
            items = validate_selection(selection, root)
            lower = next(item for item in items if item['category'] == 'bottoms')
            model = MaskedOutfitPipeline(root, items, allow_masked_target=True, preserve_upper=True,
                                        preserve_feet=preserve_feet)
            person_path = baseline / '01-top.png'
            person = load_rgb(person_path)
            case = {'baseline': baseline.relative_to(root).as_posix(), 'status': 'running',
                    'top_sha256': sha256(person_path), 'baseline_sha256': sha256(baseline / '02-bottom-raw.png'),
                    'selection_sha256': sha256(baseline / 'selection.json'),
                    'settings': dict(original_settings), 'source_extractions': model.provenance,
                    'baseline_bottom_segmentation_free': original_settings['segmentation_free']}
            if maskless_bottom:
                case['settings']['segmentation_free'] = True
            if guidance_scale is not None:
                case['settings']['guidance_scale'] = guidance_scale
            record['cases'].append(case); write_json(dest / 'run.json', record)
            start = time.perf_counter()
            result = model(person_image=person, garment_image=load_rgb(root / lower['image']),
                           category='bottoms', garment_photo_type=lower['garment_photo_type'], **case['settings']).images[0]
            output = dest / f'{index}-constrained.png'; result.save(output)
            # Compare against the unchanged first-stage garment, in output coordinates.
            resized = model.pipeline.pre_resize(person, allow_upsampling=False)
            labels = model.hp_model.predict(np.array(resized))
            alpha = preservation_alpha(labels, max(2, round(resized.height * 6 / 864)))
            alpha = np.asarray(Image.fromarray(alpha).resize(result.size, Image.Resampling.BILINEAR))
            core = alpha >= .999
            upper = np.asarray(Image.fromarray((labels == 3).astype('uint8')).resize(
                result.size, Image.Resampling.NEAREST)).astype(bool) & core
            if not core.any() or not upper.any():
                raise ValueError('No measurable protected upper interior')
            top = np.asarray(person.resize(result.size, Image.Resampling.LANCZOS)).astype(float)
            before = np.asarray(load_rgb(baseline / '02-bottom-raw.png')).astype(float)
            after = np.asarray(result).astype(float)
            case.update(status='completed', output=output.name, output_sha256=sha256(output),
                        elapsed_seconds=round(time.perf_counter() - start, 2), protected_pixels=int(core.sum()),
                        before_mean_channel_error=float(np.abs(before - top)[core].mean()),
                        after_mean_channel_error=float(np.abs(after - top)[core].mean()),
                        upper_before_mean_channel_error=float(np.abs(before - top)[upper].mean()),
                        upper_after_mean_channel_error=float(np.abs(after - top)[upper].mean()))
            panels = [('TOP INPUT', person), ('PREVIOUS', load_rgb(baseline / '02-bottom-raw.png')),
                      ('CONSTRAINED', result), ('BOTTOM SOURCE', load_rgb(root / lower['image']))]
            board = Image.new('RGB', (1280, 540), 'white'); draw = ImageDraw.Draw(board)
            for column, (title, picture) in enumerate(panels):
                thumb = ImageOps.contain(picture, (310, 500))
                board.paste(thumb, (column * 320 + (320 - thumb.width) // 2, 30))
                draw.text((column * 320 + 8, 8), title, fill='black')
            board.save(dest / f'{index}-comparison.jpg')
            write_json(dest / 'run.json', record)
            del model
            gc.collect()
        record['status'] = 'completed'
    except Exception as error:
        record.update(status='failed', error=str(error), traceback=traceback.format_exc())
        raise
    finally:
        write_json(dest / 'run.json', record)
        print('RUN_DIR=' + str(dest), flush=True)
    return dest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('baselines', nargs='+')
    variant = parser.add_mutually_exclusive_group()
    variant.add_argument('--maskless-bottom', action='store_true')
    variant.add_argument('--guidance-scale', type=float)
    parser.add_argument('--preserve-feet', action='store_true')
    args = parser.parse_args()
    run(args.baselines, maskless_bottom=args.maskless_bottom, guidance_scale=args.guidance_scale,
        preserve_feet=args.preserve_feet)
