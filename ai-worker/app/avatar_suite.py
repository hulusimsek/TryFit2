"""Same genuine two-stage outfit inference on three explicit synthetic presets.

Preset labels are not a measured height/weight-to-body function.
"""
import copy
import json
import math
import re
import traceback
import uuid
from datetime import datetime,timezone
from pathlib import Path
from experiment import local_path,sha256,write_json,command_output
from outfit import validate_selection
from masked_outfit import MaskedOutfitPipeline
from protect_outfit import run as compose


def validate_profiles(catalog,root):
    if catalog.get('schema_version')!=1 or catalog.get('continuous_height_weight_mapping') is not False:
        raise ValueError('Explicit uncalibrated visual-preset catalog required')
    profiles=catalog.get('profiles',[])
    identifiers=[p.get('id','') for p in profiles]
    if len(profiles)!=3 or len(set(identifiers))!=3 or any(not re.fullmatch('[a-z0-9-]+',i) for i in identifiers):
        raise ValueError('Three unique safe profile identifiers required')
    if len({p.get('image_sha256') for p in profiles})!=3:
        raise ValueError('Three distinct actual avatar images required, not relabeled copies')
    for profile in profiles:
        if profile.get('measured') is not False:
            raise ValueError('Synthetic presets cannot claim measured body dimensions')
        for key in ['height_cm','weight_kg']:
            value=profile.get(key)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
                raise ValueError('Invalid illustrative profile value')
        if sha256(local_path(root,profile['image']))!=profile['image_sha256']:
            raise ValueError('Synthetic profile image changed')
    return profiles


def run(*,masked_bottom=False):
    root=Path(__file__).resolve().parents[2]
    catalog_path=root/'evaluation/manifests/avatar-profiles.json'
    catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
    profiles=validate_profiles(catalog,root)
    base_path=root/'evaluation/manifests/tshirt-trousers.outfit.json'
    base=json.loads(base_path.read_text(encoding='utf-8'))
    items=validate_selection(base,root)
    dest=root/'runs'/('avatar-suite-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6])
    dest.mkdir(parents=True)
    record={'schema_version':1,'status':'initializing','quality_status':'not_reviewed','profiles':[],
        'catalog_sha256':sha256(catalog_path),'outfit_selection_sha256':sha256(base_path),
        'catalog':catalog,'same_items':items,'reused_existing_outputs':False,
        'settings':{'seed':42,'num_timesteps':30,'guidance_scale':1.5,'num_samples':1,'segmentation_free':True},
        'bottom_segmentation_free':not masked_bottom,
        'purpose':'Same two selected garments on three different synthetic visual presets',
        'limitations':['Visual presets were edited with built-in image_gen; outfits are local FASHN VTON results',
            'Illustrative height/weight tags are not measured body reconstruction or continuous numeric mapping',
            'Same garment photos, not a physical same-size garment simulation: no product measurements or cloth mechanics',
            'Source SAM masks are researcher-assisted','Different visual presets may also have small identity/lighting differences',
            'Research human-parser license restriction remains','Existing ten-product 7/10 quality baseline unchanged']}
    write_json(dest/'suite.json',record)
    try:
        pipeline=MaskedOutfitPipeline(root,items,allow_masked_target=masked_bottom)
        import torch
        record['environment']={'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'dtype':str(pipeline.inference_dtype)}
        record['upstream_commit']=command_output(['git','-C',str(root/'vendor/fashn-vton-1.5'),'rev-parse','HEAD'])
        (dest/'pip-freeze.txt').write_text(command_output([__import__('sys').executable,'-m','pip','freeze'])['stdout'],encoding='utf-8')
        record['status']='running'
        for profile in profiles:
            selection=copy.deepcopy(base)
            selection['purpose']='Synthetic visual-preset comparison; not measured body fit'
            selection['avatar'].update(image=profile['image'],height_cm=profile['height_cm'],weight_kg=profile['weight_kg'],
                visual_profile_id=profile['id'],source=profile['source'],measured=False,
                match_precision=profile['match_precision'],note='Illustrative visual preset only; no calibrated numeric height/weight body mapping')
            path=dest/(profile['id']+'.selection.json');write_json(path,selection)
            item={'id':profile['id'],'label':profile['label'],'status':'running','quality_status':'not_reviewed',
                'avatar_image':profile['image'],'avatar_sha256':profile['image_sha256'],'selection':path.relative_to(root).as_posix()}
            record['profiles'].append(item);write_json(dest/'suite.json',record)
            print('PROFILE_START='+profile['id'],flush=True)
            result=compose(path,pipeline=pipeline,bottom_segmentation_free=not masked_bottom,extra_metadata={'suite':dest.relative_to(root).as_posix(),
                'profile':profile,'source_extractions':pipeline.provenance,'dtype':str(pipeline.inference_dtype),
                'scope':'Different synthetic targets, same frozen garment inputs and sampling settings; not fit estimation'})
            item.update(status='completed',run_dir=result.relative_to(root).as_posix(),preferred_output='02-bottom-raw.png',
                raw_sha256=sha256(result/'02-bottom-raw.png'),protected_sha256=sha256(result/'03-protected-outfit.png'))
            write_json(dest/'suite.json',record)
        record['status']='completed'
    except Exception as error:
        record.update(status='failed',error=str(error),traceback=traceback.format_exc())
        if record['profiles'] and record['profiles'][-1]['status']=='running':record['profiles'][-1]['status']='failed'
        raise
    finally:
        write_json(dest/'suite.json',record)
        print('SUITE_DIR='+str(dest),flush=True)
    (root/'runs/latest-avatar-suite.txt').write_text(str(dest),encoding='utf-8')
    return dest


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--masked-bottom',action='store_true')
    run(masked_bottom=parser.parse_args().masked_bottom)
