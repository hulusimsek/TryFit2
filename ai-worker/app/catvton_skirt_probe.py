"""Bounded second-model skirt comparison; never changes the local engine."""
import json
import random
import sys
import time
import traceback
import uuid
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from catvton_inputs import target_inputs, source_cutout
from catvton_probe import pipeline
from experiment import load_rgb, local_path, sha256, write_json, command_output
from skirt_gallery_probe import validate_sources


def prepare_source(root, case):
    source=local_path(root,case['image'])
    extraction=local_path(root,'runs/source-extraction-'+case['id']+'-refined')
    metadata=json.loads((extraction/'extraction.json').read_text(encoding='utf-8'))
    annotation=metadata['annotation']
    if (annotation['id']!=case['id'] or annotation['category']!=case['category']
            or annotation['image_sha256']!=case['image_sha256'] or sha256(source)!=case['image_sha256']
            or sha256(extraction/'mask.png')!=metadata['mask_sha256']):
        raise ValueError('Source/mask identity or hash mismatch')
    with Image.open(extraction/'mask.png') as mask:
        condition,box=source_cutout(load_rgb(source),mask)
    return condition,{'source_sha256':case['image_sha256'],'mask_sha256':metadata['mask_sha256'],
        'crop_box':box,'extraction':extraction.relative_to(root).as_posix()}


def load_preservation_mask(root, annotation):
    if 'preserve_mask_image' not in annotation:return None
    path=local_path(root,annotation['preserve_mask_image'])
    if (annotation.get('preserve_mask_target_sha256')!=annotation['image_sha256']
            or sha256(path)!=annotation['preserve_mask_sha256']):
        raise ValueError('Preservation mask changed or belongs to another target')
    with Image.open(path) as opened:return opened.copy()


def run(*, annotation_path=None, case_ids=None):
    import torch
    root=Path(__file__).resolve().parents[2]
    selection_path=root/'evaluation/manifests/skirt-gallery-comparison.json'
    selection=json.loads(selection_path.read_text(encoding='utf-8'))
    original=next(c for c in json.loads((root/'evaluation/manifests/trendyol-10.actual.json').read_text(encoding='utf-8'))['cases'] if c['id']=='skirt')
    sources=validate_sources(selection,root,original)
    if case_ids is not None:
        if not case_ids or len(set(case_ids))!=len(case_ids) or not set(case_ids)<={c['id'] for c in sources}:
            raise ValueError('Unique selected source IDs from the comparison manifest required')
        sources=[c for c in sources if c['id'] in case_ids]
    annotation_path=local_path(root,annotation_path or 'evaluation/annotations/short-top-lower.catvton.json')
    annotation=json.loads(annotation_path.read_text(encoding='utf-8'))
    target_path=local_path(root,annotation['image'])
    if sha256(target_path)!=annotation['image_sha256']:raise ValueError('Target annotation changed')
    preserve=load_preservation_mask(root,annotation)
    target,hard,mask,overlay,transform=target_inputs(load_rgb(target_path),annotation,preserve_mask=preserve)
    dest=root/'runs'/('catvton-skirt-'+uuid.uuid4().hex[:8]);dest.mkdir(parents=True)
    settings={'seed':42,'num_inference_steps':50,'guidance_scale':2.5,'eta':1.0,'width':768,'height':1024}
    record={'status':'initializing','quality_status':'not_reviewed','model':'CatVTON mix-48k-1024',
        'cases':[],'settings':settings,'selection':selection,'selection_sha256':sha256(selection_path),
        'selected_case_ids':[c['id'] for c in sources],
        'target_sha256':sha256(target_path),'target_annotation':annotation,'target_transform':transform,
        'target_annotation_sha256':sha256(annotation_path),'target_image':annotation['image'],
        'fashn_comparison':'runs/skirt-gallery-910be7db' if sha256(target_path)=='a46dc2610aa705f14ca1c291fda29d119bccb49ba46725585a87126be34993d6' else None,
        'raw_and_repaint_saved_separately':True,
        'strict_preservation':preserve is not None,
        'preservation_output_method':'Repaint copies target at zero edit alpha; raw model output may still change these regions',
        'limitations':['Researcher-assisted source masks and fixed manual lower-target mask',
            'Different preprocessing, resolution and sampler from FASHN; not architecture-only ablation',
            'Repaint copies target outside mask; identity preservation there is not learned by the model',
            'Synthetic visual target or saved real first-stage outfit output, not measured fit','CatVTON CC BY-NC-SA 4.0: research only'],
        'implementation_sha256':{name:sha256(root/'ai-worker/app'/name) for name in
            ['catvton_skirt_probe.py','catvton_probe.py','catvton_inputs.py']}}
    write_json(dest/'run.json',record)
    for name,image in [('target-canvas.png',target),('target-mask-hard.png',hard),
                       ('target-mask-blurred.png',mask),('target-mask-overlay.jpg',overlay)]:image.save(dest/name)
    try:
        weights=root/'ai-worker/models/catvton'
        provenance=json.loads((weights/'provenance.json').read_text(encoding='utf-8'))
        for entry in provenance['files']:
            if sha256(weights/entry['relative_path'])!=entry['sha256']:raise ValueError('Checkpoint changed')
        record['model_provenance']=provenance
        record['upstream_commit']=command_output(['git','-C',str(root/'vendor/CatVTON'),'rev-parse','HEAD'])
        record['environment']={'torch':torch.__version__,'cuda':torch.version.cuda,
            'gpu':torch.cuda.get_device_name(0),'python':sys.version,'dtype':'bfloat16'}
        (dest/'pip-freeze.txt').write_text(command_output([sys.executable,'-m','pip','freeze'])['stdout'],encoding='utf-8')
        prepared={}
        for source in sources:
            condition,metadata=prepare_source(root,source)
            path=dest/(source['id']+'-condition.png');condition.save(path)
            prepared[source['id']]=(condition,{**metadata,'condition_sha256':sha256(path)})
        write_json(dest/'run.json',record)
        model=pipeline(weights)
        from utils import repaint_result
        record['status']='running'
        for source in sources:
            identifier=source['id'];condition,metadata=prepared[identifier]
            case={'id':identifier,'status':'running',**metadata};record['cases'].append(case)
            write_json(dest/'run.json',record);start=time.perf_counter()
            try:
                torch.manual_seed(42);np.random.seed(42);random.seed(42)
                torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize()
                raw=model(image=target,condition_image=condition,mask=mask,
                    num_inference_steps=50,guidance_scale=2.5,height=1024,width=768,
                    generator=torch.Generator(device='cuda').manual_seed(42),eta=1.0)[0]
                torch.cuda.synchronize();primary=repaint_result(raw,target,mask)
                raw.save(dest/(identifier+'-raw.png'));primary.save(dest/(identifier+'.png'))
                case.update(status='completed',raw_output=identifier+'-raw.png',output=identifier+'.png',
                    raw_sha256=sha256(dest/(identifier+'-raw.png')),output_sha256=sha256(dest/(identifier+'.png')),
                    peak_allocated_gib=round(torch.cuda.max_memory_allocated()/2**30,3))
            except Exception as error:
                case.update(status='failed',error=str(error));raise
            finally:
                case['elapsed_seconds']=round(time.perf_counter()-start,2);write_json(dest/'run.json',record)
        panels=[('SYNTHETIC TARGET',target)]
        for case in record['cases']:
            identifier=case['id']
            panels.extend([(identifier+' CONDITION',load_rgb(dest/(identifier+'-condition.png'))),
                (identifier+' RAW',load_rgb(dest/case['raw_output'])),(identifier+' REPAINT',load_rgb(dest/case['output']))])
        board=Image.new('RGB',(280*len(panels),480),'white');draw=ImageDraw.Draw(board)
        for index,(title,picture) in enumerate(panels):
            thumb=ImageOps.contain(picture,(270,440));board.paste(thumb,(index*280+(280-thumb.width)//2,30))
            draw.text((index*280+5,8),title,fill='black')
        board.save(dest/'comparison.jpg');record['status']='completed'
    except Exception as error:
        record.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
    finally:
        write_json(dest/'run.json',record);print('RUN_DIR='+str(dest),flush=True)
    return dest


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--annotation')
    parser.add_argument('--case',action='append')
    args=parser.parse_args();run(annotation_path=args.annotation,case_ids=args.case)
