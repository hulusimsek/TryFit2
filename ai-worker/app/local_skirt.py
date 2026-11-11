"""Real local FASHN upper -> isolated CatVTON skirt; no cached-result fallback."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
from PIL import Image
from experiment import load_rgb,local_path,sha256,write_json
from outfit import validate_selection
from catvton_inputs import target_inputs,letterbox
from catvton_skirt_probe import prepare_source
from local_skirt_inputs import skirt_inputs

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
    if set(record['files'])!=required:raise ValueError('Unexpected prepared artifacts')
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
    annotation,preserve,background_alpha=skirt_inputs(labels,tuck_top=selection.get('tuck_top',False))
    target,hard,soft,overlay,transform=target_inputs(result,annotation,preserve_mask=preserve)
    fade,_=letterbox(background_alpha,(768,1024),mask=True)
    soft=Image.fromarray(np.rint(np.asarray(soft).astype(float)*np.asarray(fade)/255).astype('uint8'))
    hard=Image.fromarray((np.asarray(soft)>=128).astype('uint8')*255)
    preview=np.array(target);edited=np.asarray(hard)>0
    preview[edited]=(preview[edited]*.5+np.array([0,180,120])*.5).astype('uint8')
    overlay=Image.fromarray(preview)
    condition,source=prepare_source(ROOT,skirt)
    for name,image in [('cat-target.png',target),('cat-hard-mask.png',hard),('cat-soft-mask.png',soft),
                       ('cat-preserve.png',preserve),('cat-mask-preview.jpg',overlay),('cat-condition.png',condition)]:
        image.save(directory/name)
    files=['01-top.png','cat-target.png','cat-hard-mask.png','cat-soft-mask.png','cat-preserve.png','cat-condition.png']
    write_json(directory/'skirt-handoff.json',{'selection_sha256':sha256(directory/'selection.json'),
        'files':{name:sha256(directory/name) for name in files},'annotation':annotation,'target_transform':transform,
        'source':source,'upper_source_masks':model.provenance,'upper_elapsed_seconds':round(time.perf_counter()-start,2)})
    print('TOP_COMPLETED',flush=True)


def lower(directory):
    import torch
    from catvton_probe import pipeline
    record=verify_prepared(directory)
    weights=ROOT/'ai-worker/models/catvton'
    provenance=json.loads((weights/'provenance.json').read_text(encoding='utf-8'))
    for item in provenance['files']:
        if sha256(weights/item['relative_path'])!=item['sha256']:raise ValueError('CatVTON weights changed')
    model=pipeline(weights)
    from utils import repaint_result
    start=time.perf_counter();torch.manual_seed(42);np.random.seed(42)
    target=load_rgb(directory/'cat-target.png')
    with Image.open(directory/'cat-soft-mask.png') as opened:mask=opened.copy()
    raw=model(image=target,condition_image=load_rgb(directory/'cat-condition.png'),mask=mask,
        num_inference_steps=50,guidance_scale=2.5,height=1024,width=768,
        generator=torch.Generator(device='cuda').manual_seed(42),eta=1.0)[0]
    primary=repaint_result(raw,target,mask)
    raw.save(directory/'02-skirt-raw.png');primary.save(directory/'02-skirt-repaint.png')
    write_json(directory/'catvton-outcome.json',{'status':'completed','raw_sha256':sha256(directory/'02-skirt-raw.png'),
        'output_sha256':sha256(directory/'02-skirt-repaint.png'),'elapsed_seconds':round(time.perf_counter()-start,2),
        'model_provenance':provenance,'settings':{'seed':42,'steps':50,'guidance':2.5,'eta':1.0},
        'method':'Actual CatVTON inference; repaint copies target at zero edit alpha','handoff_sha256':sha256(directory/'skirt-handoff.json')})


def run(directory):
    import shutil
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
    shutil.copy2(directory/'02-skirt-repaint.png',directory/'result.png')
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
