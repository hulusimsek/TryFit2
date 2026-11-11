"""Real local UI job: fixed approved catalog, no remote or fallback generation."""
import argparse
import copy
import json
import re
import shutil
import traceback
from pathlib import Path
from avatar_suite import validate_profiles
from experiment import sha256,write_json
from masked_outfit import MaskedOutfitPipeline
from protect_outfit import run as compose


def run(job_dir):
    root=Path(__file__).resolve().parents[2]
    job_dir=Path(job_dir).resolve()
    if job_dir.parent!=root/'runs/local-jobs' or not re.fullmatch('[a-f0-9]{32}',job_dir.name):
        raise ValueError('Job must be an application-generated project directory')
    try:
        request=json.loads((job_dir/'request.json').read_text(encoding='utf-8'))
        catalog=json.loads((root/'evaluation/manifests/avatar-profiles.json').read_text(encoding='utf-8'))
        profiles=validate_profiles(catalog,root)
        profile=next(p for p in profiles if p['id']==request['profileId'])
        cases=json.loads((root/'evaluation/manifests/trendyol-10.actual.json').read_text(encoding='utf-8'))['cases']
        if request['topId'] not in {'tshirt','patterned-blouse'} or request['bottomId'] not in {'wide-trousers','skirt'}:
            raise ValueError('Choose approved example garments')
        upper=next(c for c in cases if c['id']==request['topId'] and c['category']=='tops')
        lower=next(c for c in cases if c['id']==request['bottomId'] and c['category']=='bottoms')
        selection=json.loads((root/'evaluation/manifests/tshirt-trousers.outfit.json').read_text(encoding='utf-8'))
        selection['items']=[copy.deepcopy(upper),copy.deepcopy(lower)]
        selection['avatar'].update(image=profile['image'],height_cm=profile['height_cm'],weight_kg=profile['weight_kg'],
            visual_profile_id=profile['id'],source=profile['source'],measured=False,match_precision=profile['match_precision'],
            note='Predefined synthetic visual profile, not body reconstruction from height and weight')
        path=job_dir/'selection.json';write_json(path,selection)
        tuck=request.get('tuckTop',False)
        if not isinstance(tuck,bool) or (tuck and lower['id']!='skirt'):
            raise ValueError('Tucking is supported only for the approved skirt')
        if lower['id']=='skirt':
            from local_skirt import run as run_skirt
            selection['tuck_top']=tuck;write_json(path,selection)
            run_skirt(job_dir)
            return
        # The remaining approved trousers keep their existing FASHN method.
        maskless_bottom=lower['id']=='wide-trousers'
        model=MaskedOutfitPipeline(root,selection['items'],allow_masked_target=True,preserve_upper=True,
            preserve_feet=maskless_bottom)
        result=compose(path,pipeline=model,bottom_segmentation_free=maskless_bottom,extra_metadata={
            'local_job':job_dir.relative_to(root).as_posix(),'source_extractions':model.provenance,
            'method':'Target-maskless upper stage; upper-interior constrained lower stage; trousers use maskless target with feet/floor constraint, skirt uses masked target',
            'bottom_target_masked':not maskless_bottom,
            'feet_preservation':{'enabled':maskless_bottom,'method':'Feet interior and lower-background reference trajectory with ankle transition'},
            'upper_preservation':{'enabled':True,'method':'Noise-matched reference trajectory at each lower-stage Euler step',
                'regions':['face','hair','top','arms','hands','torso'],'edge_pixels_at_864_height':6,
                'limits':'Garment boundary remains generated; source identity, waistband and physical fit are not guaranteed'},
            'output':'Actual raw second-stage inference, no output compositing',
            'limits':['Selected example products only','Three unmeasured visual profiles','No physical fit guarantee','Research human-parser license restriction']})
        raw=result/'02-bottom-raw.png'
        shutil.copy2(raw,job_dir/'result.png')
        write_json(job_dir/'outcome.json',{'status':'completed','runDirectory':result.relative_to(root).as_posix(),
            'outputSha256':sha256(raw),'outputCompositing':False,'upperPreservation':True,
            'feetPreservation':maskless_bottom,'bottomTargetMasked':not maskless_bottom,'request':request})
    except Exception as error:
        write_json(job_dir/'outcome.json',{'status':'failed','error':str(error),'traceback':traceback.format_exc()})
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--job-dir',type=Path,required=True);run(parser.parse_args().job_dir)
