"""Controlled lower-stage target-masking test; no output compositing or retries."""
import argparse
import json
import time
import traceback
import uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from experiment import load_rgb,sha256,write_json
from masked_outfit import MaskedOutfitPipeline


def run(suite_dir):
    import torch
    from PIL import Image
    from fashn_vton.preprocessing import create_clothing_agnostic_image
    root=Path(__file__).resolve().parents[2]
    suite_dir=Path(suite_dir).resolve()
    suite=json.loads((suite_dir/'suite.json').read_text(encoding='utf-8'))
    if suite['status']!='completed' or len(suite['profiles'])!=3:raise ValueError('Completed three-profile baseline required')
    dest=root/'runs'/('feet-input-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]);dest.mkdir(parents=True)
    record={'schema_version':1,'status':'initializing','quality_status':'not_reviewed','profiles':[],
        'baseline_suite':suite_dir.relative_to(root).as_posix(),'baseline_suite_sha256':sha256(suite_dir/'suite.json'),
        'controlled_change':'Only lower-stage segmentation_free: True -> False; same previous top output, garment and seed',
        'settings':{'seed':42,'num_timesteps':30,'guidance_scale':1.5,'num_samples':1,'segmentation_free':False},
        'output_compositing':False,'limitations':['Real target human parsing, explicit source-mask override opt-in',
            'Mask-conditioned inference can change body or garment shape; visual checks required','No measured height/weight or fit model',
            'Three-profile probe cannot change the ten-product quality gate']}
    write_json(dest/'run.json',record)
    try:
        model=MaskedOutfitPipeline(root,suite['same_items'],allow_masked_target=True)
        lower=next(i for i in suite['same_items'] if i['category']=='bottoms')
        if sha256(root/lower['image'])!=lower['image_sha256']:raise ValueError('Garment changed')
        garment=load_rgb(root/lower['image']);record['source_extractions']=model.provenance;record['status']='running'
        for profile in suite['profiles']:
            directory=root/profile['run_dir'];person_path=directory/'01-top.png';person=load_rgb(person_path)
            item={'id':profile['id'],'label':profile['label'],'status':'running','quality_status':'not_reviewed',
                'person_image':person_path.relative_to(root).as_posix(),'person_sha256':sha256(person_path),
                'previous_raw':(directory/'02-bottom-raw.png').relative_to(root).as_posix(),
                'previous_raw_sha256':sha256(directory/'02-bottom-raw.png')}
            record['profiles'].append(item);write_json(dest/'run.json',record)
            # Diagnose the exact upstream conditioning operation before inference.
            resized=model.pipeline.pre_resize(person,allow_upsampling=False)
            pixels=np.array(resized);labels=model.hp_model.predict(pixels)
            ca=create_clothing_agnostic_image(pixels.copy(),labels.copy(),[5,6,7],body_coverage='lower',disable_masking=False)
            Image.fromarray(ca).save(dest/(profile['id']+'-masked-input.png'))
            Image.fromarray(labels.astype('uint8')).save(dest/(profile['id']+'-target-labels.png'))
            feet=labels==15
            if feet.sum()<30:raise ValueError('Target parsing found no usable feet')
            item['conditioning_feet_pixels']=int(feet.sum())
            item['conditioning_changed_feet_pixels']=int(np.any(ca[feet]!=pixels[feet],axis=1).sum())
            start=time.perf_counter();print('PROFILE_START='+profile['id'],flush=True)
            try:
                torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize()
                result=model(person_image=person,garment_image=garment,category='bottoms',garment_photo_type=lower['garment_photo_type'],**record['settings']).images[0]
                torch.cuda.synchronize();result.save(dest/(profile['id']+'.png'))
                item.update(status='completed',output=profile['id']+'.png',output_sha256=sha256(dest/(profile['id']+'.png')),
                    peak_allocated_gib=round(torch.cuda.max_memory_allocated()/2**30,3))
            except Exception as error:
                item.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
            finally:
                item['elapsed_seconds']=round(time.perf_counter()-start,2);write_json(dest/'run.json',record)
        record['status']='completed'
    except Exception as error:
        record.update(status='failed',error=str(error),traceback=traceback.format_exc())
        if record['profiles'] and record['profiles'][-1]['status']=='running':record['profiles'][-1]['status']='failed'
        raise
    finally:
        write_json(dest/'run.json',record);print('RUN_DIR='+str(dest),flush=True)
    (root/'runs/latest-feet-input-probe.txt').write_text(str(dest),encoding='utf-8')
    return dest


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('suite_dir',type=Path);run(parser.parse_args().suite_dir)
