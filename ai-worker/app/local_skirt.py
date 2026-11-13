"""Real local FASHN upper -> isolated CatVTON skirt; no cached-result fallback."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from experiment import load_rgb,local_path,sha256,write_json
from outfit import validate_selection
from catvton_inputs import unletterbox
from catvton_skirt_probe import prepare_source
from local_skirt_inputs import prepare_skirt_masks

ROOT=Path(__file__).resolve().parents[2]


def checked_directory(directory):
    import re
    directory=Path(directory).resolve()
    if directory.parent!=ROOT/'runs/local-jobs' or not re.fullmatch('[a-f0-9]{32}',directory.name):
        raise ValueError('Application job directory required')
    return directory


def verify_prepared(directory):
    record=json.loads((directory/'skirt-handoff.json').read_text(encoding='utf-8'))
    if sha256(directory/'selection.json')!=record['selection_sha256']:raise ValueError('Selection changed')
    required={'01-top.png','cat-target.png','cat-hard-mask.png','cat-soft-mask.png','cat-preserve.png','cat-condition.png'}
    optional={'cat-repaint-mask.png'}
    record_files=set(record['files'])
    if not (required <= record_files <= (required | optional)):
        raise ValueError('Unexpected prepared artifacts')
    for name,digest in record['files'].items():
        if sha256(local_path(directory,name))!=digest:raise ValueError('Prepared artifact changed')
    return record


def upper(directory):
    from masked_outfit import MaskedOutfitPipeline
    selection=json.loads((directory/'selection.json').read_text(encoding='utf-8'))
    items=validate_selection(selection,ROOT)
    top_item=next(i for i in items if i['category']=='tops');skirt=next(i for i in items if i['category']=='bottoms')
    if skirt['id']!='skirt':raise ValueError('Only approved skirt supported')
    model=MaskedOutfitPipeline(ROOT,items)
    start=time.perf_counter()
    result=model(person_image=load_rgb(local_path(ROOT,selection['avatar']['image'])),
        garment_image=load_rgb(local_path(ROOT,top_item['image'])),category='tops',garment_photo_type=top_item['garment_photo_type'],
        seed=42,num_timesteps=30,guidance_scale=1.5,segmentation_free=True,num_samples=1).images[0]
    result.save(directory/'01-top.png')
    labels=model.hp_model.predict(np.asarray(result))
    masks=prepare_skirt_masks(result,labels,tuck_top=selection.get('tuck_top',False))
    target,hard,soft,preserve,overlay,annotation,transform=masks
    repaint_mask=getattr(masks,'repaint_soft',soft)
    condition,source=prepare_source(ROOT,skirt)
    for name,image in [('cat-target.png',target),('cat-hard-mask.png',hard),('cat-soft-mask.png',soft),
                       ('cat-preserve.png',preserve),('cat-mask-preview.jpg',overlay),('cat-condition.png',condition),
                       ('cat-repaint-mask.png',repaint_mask)]:
        image.save(directory/name)
    files=['01-top.png','cat-target.png','cat-hard-mask.png','cat-soft-mask.png','cat-preserve.png','cat-condition.png','cat-repaint-mask.png']
    write_json(directory/'skirt-handoff.json',{'selection_sha256':sha256(directory/'selection.json'),
        'files':{name:sha256(directory/name) for name in files},'annotation':annotation,'target_transform':transform,
        'source':source,'upper_source_masks':model.provenance,'upper_elapsed_seconds':round(time.perf_counter()-start,2)})
    print('TOP_COMPLETED',flush=True)


def _connected_from_seeds(mask, seeds):
    """Return 8-connected components of mask that intersect seeds."""
    if not mask.any() or not seeds.any():
        return np.zeros(mask.shape, dtype=bool)
    _, labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    seed_ids = np.unique(labels[seeds])
    seed_ids = seed_ids[seed_ids > 0]
    if not len(seed_ids):
        return np.zeros(mask.shape, dtype=bool)
    return np.isin(labels, seed_ids)


def _non_letterbox_mask(target_arr):
    """Exclude symmetric or edge-bounded uniform letterbox padding strips when present."""
    height, width, _ = target_arr.shape
    keep = np.ones((height, width), dtype=bool)
    max_pad_x = width // 3
    max_pad_y = height // 3

    def _strip_edge(axis_len, limit, slice_fn, ref_px):
        count = 0
        while count < limit and np.all(slice_fn(count) == ref_px):
            count += 1
        if 0 < count < limit:
            nxt = slice_fn(count)
            if float(np.median(np.abs(nxt - ref_px).max(axis=1))) > 2.0:
                return count
        return 0

    left_pad = _strip_edge(width, max_pad_x, lambda x: target_arr[:, x], target_arr[0, 0])
    right_pad = _strip_edge(width, max_pad_x, lambda x: target_arr[:, width - 1 - x], target_arr[0, width - 1])
    top_pad = _strip_edge(height, max_pad_y, lambda y: target_arr[y, :], target_arr[0, 0])
    bot_pad = _strip_edge(height, max_pad_y, lambda y: target_arr[height - 1 - y, :], target_arr[height - 1, 0])
    if left_pad:
        keep[:, :left_pad] = False
    if right_pad:
        keep[:, width - right_pad:] = False
    if top_pad:
        keep[:top_pad, :] = False
    if bot_pad:
        keep[height - bot_pad:, :] = False
    return keep


def _estimate_exterior_background(target_arr, raw_arr, edit_mask):
    """Estimate row-wise target and raw studio background from unmasked exterior pixels."""
    height, width, _ = target_arr.shape
    ext = (~edit_mask) & _non_letterbox_mask(target_arr)
    if not ext.any():
        ext = ~edit_mask
    t_med0 = np.median(target_arr[ext], axis=0)
    bg_ext = ext & (np.abs(target_arr - t_med0).max(axis=2) <= 18.0)
    if not bg_ext.any():
        bg_ext = ext
    t_global = np.median(target_arr[bg_ext], axis=0)
    r_global = np.median(raw_arr[bg_ext], axis=0)
    t_row = np.tile(t_global, (height, 1)).astype(np.float32)
    r_row = np.tile(r_global, (height, 1)).astype(np.float32)
    win = max(4, round(height * 0.025))
    min_pts = max(8, width // 40)
    for y in range(height):
        y0, y1 = max(0, y - win), min(height, y + win + 1)
        m = bg_ext[y0:y1]
        if int(m.sum()) >= min_pts:
            t_row[y] = np.median(target_arr[y0:y1][m], axis=0)
            r_row[y] = np.median(raw_arr[y0:y1][m], axis=0)
    return t_row, r_row, bg_ext


def restore_raw_background(raw, target, mask):
    """Conservatively restore exterior-connected studio background in raw before repaint."""
    raw_img = raw.convert('RGB')
    target_img = target.convert('RGB')
    mask_img = mask.convert('L')
    if raw_img.size != target_img.size or raw_img.size != mask_img.size:
        raise ValueError('Raw, target and mask sizes must match')

    raw_arr = np.asarray(raw_img, dtype=np.float32)
    target_arr = np.asarray(target_img, dtype=np.float32)
    mask_arr = np.asarray(mask_img)
    edit = mask_arr > 0
    if not edit.any() or edit.all():
        return raw_img.copy()

    height, width, _ = raw_arr.shape
    t_row, r_row, bg_ext = _estimate_exterior_background(target_arr, raw_arr, edit)
    if not bg_ext.any():
        return raw_img.copy()

    raw_chroma = raw_arr.max(axis=2) - raw_arr.min(axis=2)
    raw_rb = raw_arr[:, :, 0] - raw_arr[:, :, 2]
    rbg_chroma = (r_row.max(axis=1) - r_row.min(axis=1))[:, None]
    rbg_rb = (r_row[:, 0] - r_row[:, 2])[:, None]
    chroma_diff = np.abs(raw_chroma - rbg_chroma)
    rb_diff = raw_rb - rbg_rb
    raw_lum = raw_arr.mean(axis=2)
    rbg_lum = r_row.mean(axis=1)[:, None]

    # Separate skin pixels explicitly via warm chroma and depressed blue channel relative to background.
    is_skin = edit & (rb_diff >= 14.0) & (chroma_diff >= 12.0) & (raw_arr[:, :, 2] < r_row[:, None, 2] - 8.0)

    k3 = np.ones((3, 3), np.uint8)
    dr_max = np.abs(raw_arr - r_row[:, None, :]).max(axis=2)
    dt_max = np.abs(target_arr - t_row[:, None, :]).max(axis=2)

    # 1. Broad studio background where both target and raw agree with local exterior background.
    cand_bg_target = edit & (~is_skin) & (dt_max <= 10.0) & (dr_max <= 7.5) & (chroma_diff <= 7.0)
    bg_target_seeds = (cv2.dilate(bg_ext.astype(np.uint8), k3) > 0) & cand_bg_target
    bg_target_conn = _connected_from_seeds(cand_bg_target, bg_target_seeds)

    # 2. Narrow exposed background strip along bare legs (where target had leggings, not background).
    base_ext = bg_ext | bg_target_conn
    strip_lim = max(4, round(height * 0.008))
    dist_base = cv2.distanceTransform((~base_ext).astype(np.uint8), cv2.DIST_L2, 5)
    dist_skin = (cv2.distanceTransform((~is_skin).astype(np.uint8), cv2.DIST_L2, 5)
                 if is_skin.any() else np.full((height, width), 1e6, dtype=np.float32))
    cand_bg_strip = (
        edit
        & (~bg_target_conn)
        & (~is_skin)
        & (dist_base <= strip_lim + 0.5)
        & (dist_skin <= strip_lim + 2.5)
        & (dr_max <= 8.5)
        & (chroma_diff <= 7.5)
    )
    union_bg = bg_target_conn | cand_bg_strip
    bg_conn = _connected_from_seeds(union_bg, (cv2.dilate(bg_ext.astype(np.uint8), k3) > 0) & union_bg)

    # 3. Thin 1-2 px neutral overshoot rim strictly sandwiched between exterior background and skin;
    #    reject any connected bright component that reaches deeper into a light-colored garment or buckle.
    ext_plus_bg = bg_ext | bg_conn
    dist_ext = cv2.distanceTransform((~ext_plus_bg).astype(np.uint8), cv2.DIST_L2, 5)
    bright_non_bg = edit & (~is_skin) & (~bg_conn) & (raw_lum >= rbg_lum - 12.0)
    bright_core = bright_non_bg & ((dist_ext > 2.5) | (dist_skin > 3.0))
    touches_core = _connected_from_seeds(bright_non_bg, bright_core)
    r_lum_diff = raw_lum - rbg_lum
    cand_rim = (
        bright_non_bg
        & (~touches_core)
        & (dist_ext <= 2.5)
        & (dist_skin <= 2.5)
        & (r_lum_diff >= -4.0)
        & (r_lum_diff <= 28.0)
        & (raw_arr.min(axis=2) >= r_row.min(axis=1)[:, None] - 8.0)
        & (chroma_diff <= 14.0)
        & (rb_diff <= 14.0)
    )

    union_all = bg_conn | cand_rim
    restore_mask = _connected_from_seeds(union_all, (cv2.dilate(bg_ext.astype(np.uint8), k3) > 0) & union_all)
    if not restore_mask.any():
        return raw_img.copy()

    target_is_flat_bg = dt_max <= 5.0
    target_bg_val = np.where(target_is_flat_bg[:, :, None], target_arr, t_row[:, None, :])
    restored = raw_arr.copy()
    restored[restore_mask] = target_bg_val[restore_mask]
    return Image.fromarray(np.rint(np.clip(restored, 0, 255)).astype(np.uint8))


def lower(directory):
    import torch
    from catvton_probe import pipeline
    verify_prepared(directory)
    weights=ROOT/'ai-worker/models/catvton'
    provenance=json.loads((weights/'provenance.json').read_text(encoding='utf-8'))
    for item in provenance['files']:
        if sha256(weights/item['relative_path'])!=item['sha256']:raise ValueError('CatVTON weights changed')
    use_cuda=torch.cuda.is_available()
    def _cuda_gib(fn_name):
        if not use_cuda:return None
        fn=getattr(torch.cuda,fn_name,None)
        if not callable(fn):return None
        try:return round(fn()/2**30,3)
        except Exception:return None
    start=time.perf_counter()
    model=None
    try:
        model=pipeline(weights)
        from utils import repaint_result
        torch.manual_seed(42);np.random.seed(42)
        target=load_rgb(directory/'cat-target.png')
        with Image.open(directory/'cat-soft-mask.png') as opened:mask=opened.copy()
        repaint_path=directory/'cat-repaint-mask.png'
        if repaint_path.is_file():
            with Image.open(repaint_path) as opened:repaint_mask=opened.copy()
        else:
            repaint_mask=mask
        if use_cuda:
            torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize()
        generator=torch.Generator(device='cuda' if use_cuda else 'cpu').manual_seed(42)
        raw=model(image=target,condition_image=load_rgb(directory/'cat-condition.png'),mask=mask,
            num_inference_steps=50,guidance_scale=2.5,height=1024,width=768,
            generator=generator,eta=1.0)[0]
        if use_cuda:
            torch.cuda.synchronize()
        raw_for_repaint=restore_raw_background(raw,target,repaint_mask)
        primary=repaint_result(raw_for_repaint,target,repaint_mask)
        raw.save(directory/'02-skirt-raw.png');primary.save(directory/'02-skirt-repaint.png')
        write_json(directory/'catvton-outcome.json',{'status':'completed','raw_sha256':sha256(directory/'02-skirt-raw.png'),
            'output_sha256':sha256(directory/'02-skirt-repaint.png'),'elapsed_seconds':round(time.perf_counter()-start,2),
            'peak_allocated_gib':_cuda_gib('max_memory_allocated'),'peak_reserved_gib':_cuda_gib('max_memory_reserved'),
            'vae_decode':getattr(model,'last_decode_info',None),
            'model_provenance':provenance,'settings':{'seed':42,'steps':50,'guidance':2.5,'eta':1.0},
            'method':'Actual CatVTON inference; repaint copies target at zero edit alpha','handoff_sha256':sha256(directory/'skirt-handoff.json')})
    except Exception as error:
        decode_info=getattr(model,'last_decode_info',None)
        error_stage=('pipeline_init' if model is None else
            (getattr(model,'last_error_stage',None) or (decode_info or {}).get('error_stage') or 'catvton_inference'))
        write_json(directory/'catvton-outcome.json',{'status':'failed','error':str(error),'error_type':type(error).__name__,
            'error_stage':error_stage,'elapsed_seconds':round(time.perf_counter()-start,2),
            'peak_allocated_gib':_cuda_gib('max_memory_allocated'),'peak_reserved_gib':_cuda_gib('max_memory_reserved'),
            'vae_decode':decode_info,'handoff_sha256':sha256(directory/'skirt-handoff.json')})
        raise


def save_final_result(directory, record, destination=None):
    """Un-letterbox 02-skirt-repaint.png back to the original target size using target_transform."""
    out_path = Path(destination) if destination is not None else directory / 'result.png'
    with Image.open(directory / '02-skirt-repaint.png') as repaint:
        final_image = unletterbox(repaint.convert('RGB'), record.get('target_transform'))
    final_image.save(out_path)
    return out_path


def run(directory):
    directory=checked_directory(directory)
    cat_python=ROOT/'.venv-catvton/Scripts/python.exe'
    if not cat_python.is_file():raise FileNotFoundError('CatVTON research environment unavailable')
    for phase,python in [('upper',sys.executable),('lower',str(cat_python))]:
        if phase=='upper':print('Running inference: upper stage',flush=True)
        subprocess.run([str(python),'-u',str(Path(__file__).resolve()),phase,'--job-dir',str(directory)],
            check=True,cwd=ROOT,stdout=sys.stdout,stderr=sys.stderr,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if phase=='upper':
            verify_prepared(directory)
            print('TOP_COMPLETED',flush=True)
    record=verify_prepared(directory)
    outcome=json.loads((directory/'catvton-outcome.json').read_text(encoding='utf-8'))
    if (outcome['status']!='completed' or sha256(directory/'02-skirt-repaint.png')!=outcome['output_sha256']
            or sha256(directory/'skirt-handoff.json')!=outcome['handoff_sha256']):raise ValueError('Skirt output verification failed')
    save_final_result(directory, record)
    selection=json.loads((directory/'selection.json').read_text(encoding='utf-8'))
    write_json(directory/'outcome.json',{'status':'completed','runDirectory':directory.relative_to(ROOT).as_posix(),
        'outputSha256':sha256(directory/'result.png'),'engine':'fashn-catvton-skirt-v1','outputCompositing':True,
        'tuckTop':selection.get('tuck_top',False),'upperPreservation':'All parsed upper pixels except explicitly tucked hem',
        'feetPreservation':True,'limits':['Research-only CatVTON/human-parser licenses','Approximate cut and fit',
            'Preserved pixels copied by repaint; not learned identity preservation']})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['upper','lower']);parser.add_argument('--job-dir',required=True)
    args=parser.parse_args();directory=checked_directory(args.job_dir)
    (upper if args.phase=='upper' else lower)(directory)
