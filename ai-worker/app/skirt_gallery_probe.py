"""Compare preselected photos of the same skirt; no catalog or default changes."""
import json
import time
import traceback
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image, ImageDraw, ImageOps
from experiment import load_rgb, local_path, sha256, write_json
from masked_outfit import MaskedOutfitPipeline


def validate_sources(manifest, root, original):
    cases=manifest.get('cases',[])
    if manifest.get('schema_version')!=1 or manifest.get('selection_before_inference') is not True:
        raise ValueError('Preselected source comparison required')
    if (len(cases)<2 or len({c['id'] for c in cases})!=len(cases)
            or len({c['image_sha256'] for c in cases})!=len(cases)):
        raise ValueError('Distinct baseline and alternative sources required')
    expected=urlsplit(original['product_url'])
    for case in cases:
        url=urlsplit(case['product_url'])
        if (url.scheme,url.netloc,url.path)!=(expected.scheme,expected.netloc,expected.path):
            raise ValueError('All sources must belong to the original product listing')
        if case['category']!='bottoms' or case['garment_photo_type']!='model':
            raise ValueError('Worn skirt sources required')
        if sha256(local_path(root,case['image']))!=case['image_sha256']:
            raise ValueError('Source image changed')
    if not any(c['id']==original['id'] and c['image_sha256']==original['image_sha256'] for c in cases):
        raise ValueError('Original baseline must be retained')
    return cases


def run():
    root=Path(__file__).resolve().parents[2]
    path=root/'evaluation/manifests/skirt-gallery-comparison.json'
    manifest=json.loads(path.read_text(encoding='utf-8'))
    original=next(c for c in json.loads((root/'evaluation/manifests/trendyol-10.actual.json').read_text(encoding='utf-8'))['cases'] if c['id']=='skirt')
    cases=validate_sources(manifest,root,original)
    target=root/'data/waist-control/short-top.png'
    settings=dict(seed=42,num_timesteps=30,guidance_scale=1.5,num_samples=1,segmentation_free=False)
    dest=root/'runs'/('skirt-gallery-'+uuid.uuid4().hex[:8]);dest.mkdir(parents=True)
    record={'status':'initializing','quality_status':'not_reviewed','cases':[],
        'settings':settings,'target':'data/waist-control/short-top.png','target_sha256':sha256(target),
        'selection':manifest,'selection_sha256':sha256(path),'preserve_upper':True,
        'protected_regions':['face','hair','top','arms','hands','torso'],'output_compositing':False,
        'implementation_sha256':{n:sha256(root/'ai-worker/app'/n) for n in
            ['skirt_gallery_probe.py','masked_outfit.py','upper_preservation.py']},
        'limits':['Alternative worn photos also change pose, framing, resolution and source mask; not a pose-only test',
                  'Researcher-assisted SAM masks','Synthetic short-top target, not measured body fit',
                  'Same listing verified; photo origin not independently authenticated','No general quality gate change']}
    write_json(dest/'run.json',record)
    try:
        model=MaskedOutfitPipeline(root,cases,allow_masked_target=True,preserve_upper=True)
        record.update(status='running',source_extractions=model.provenance)
        for source in cases:
            entry={'id':source['id'],'status':'running','source_sha256':source['image_sha256']}
            record['cases'].append(entry);write_json(dest/'run.json',record)
            start=time.perf_counter()
            output=model(person_image=load_rgb(target),garment_image=load_rgb(root/source['image']),
                category='bottoms',garment_photo_type='model',**settings).images[0]
            result=dest/(source['id']+'.png');output.save(result)
            entry.update(status='completed',output=result.name,output_sha256=sha256(result),
                elapsed_seconds=round(time.perf_counter()-start,2))
            write_json(dest/'run.json',record)
        panels=[('SYNTHETIC CONTROL',load_rgb(target))]
        for source,entry in zip(cases,record['cases'],strict=True):
            panels.extend([(source['id']+' SOURCE',load_rgb(root/source['image'])),
                           (source['id']+' OUTPUT',load_rgb(dest/entry['output']))])
        board=Image.new('RGB',(320*len(panels),540),'white');draw=ImageDraw.Draw(board)
        for i,(title,picture) in enumerate(panels):
            thumb=ImageOps.contain(picture,(310,500));board.paste(thumb,(i*320+(320-thumb.width)//2,30))
            draw.text((i*320+6,8),title,fill='black')
        board.save(dest/'comparison.jpg');record['status']='completed'
    except Exception as error:
        record.update(status='failed',error=str(error),traceback=traceback.format_exc())
        if record['cases'] and record['cases'][-1]['status']=='running':record['cases'][-1]['status']='failed'
        raise
    finally:
        write_json(dest/'run.json',record);print('RUN_DIR='+str(dest),flush=True)
    return dest


if __name__=='__main__':run()
