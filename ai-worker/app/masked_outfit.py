"""Compose two actual VTON transfers using frozen source instance masks."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from experiment import load_rgb, local_path, sha256, write_json, command_output
from outfit import create_pipeline, validate_selection
from protect_outfit import run as compose
from source_mask import SourceMaskParser


def fingerprint(picture):
    return picture.size, hashlib.sha256(picture.tobytes()).hexdigest()


def source_cutout(picture, mask, *, crop=False):
    """Keep frozen garment pixels; optional framing changes no source detail."""
    mask=np.asarray(mask)
    if mask.shape!=(picture.height,picture.width) or not np.isin(mask,[0,1,255]).all():
        raise ValueError('Invalid source cutout mask')
    foreground=mask!=0
    if not foreground.any() or foreground.all():
        raise ValueError('Source cutout requires foreground and background')
    pixels=np.where(foreground[...,None],np.asarray(picture),127).astype('uint8')
    bounds=(0,0,picture.width,picture.height)
    if crop:
        ys,xs=np.where(foreground)
        padding=max(1,round(max(xs.max()-xs.min()+1,ys.max()-ys.min()+1)*.12))
        bounds=(max(0,int(xs.min())-padding),max(0,int(ys.min())-padding),
                min(picture.width,int(xs.max())+padding+1),min(picture.height,int(ys.max())+padding+1))
    return Image.fromarray(pixels).crop(bounds),bounds


class MaskedOutfitPipeline:
    def __init__(self,root,items,*,allow_masked_target=False,preserve_upper=False,preserve_feet=False,
                 bottom_source_cutout=None):
        if bottom_source_cutout not in (None,'full','crop'):
            raise ValueError('Unknown source cutout framing')
        if preserve_feet and not preserve_upper:
            raise ValueError('Feet preservation requires upper preservation')
        self.allow_masked_target=allow_masked_target
        self.preserve_upper=preserve_upper
        self.preserve_feet=preserve_feet
        self.bottom_source_cutout=bottom_source_cutout
        self.last_source_preparation=None
        self.entries={}
        self.provenance={}
        for item in items:
            source=local_path(root,item['image'])
            directory=local_path(root,'runs/source-extraction-'+item['id']+'-refined')
            metadata=json.loads((directory/'extraction.json').read_text(encoding='utf-8'))
            if (sha256(source)!=item['image_sha256'] or metadata['annotation']['image_sha256']!=item['image_sha256']
                    or metadata['annotation']['id']!=item['id'] or metadata['annotation']['category']!=item['category']
                    or sha256(directory/'mask.png')!=metadata['mask_sha256']):
                raise ValueError('Source and instance mask provenance mismatch')
            picture=load_rgb(source)
            with Image.open(directory/'mask.png') as opened:
                mask=np.array(opened.convert('L'))
            if mask.shape!=(picture.height,picture.width):
                raise ValueError('Source mask geometry mismatch')
            key=fingerprint(picture)
            if key in self.entries:
                raise ValueError('Ambiguous identical source images')
            self.entries[key]=(item['category'],mask)
            self.provenance[item['id']]={'directory':directory.relative_to(root).as_posix(),'metadata':metadata}
        self.pipeline=create_pipeline(root/'ai-worker/models',parser_factory=SourceMaskParser)
        self.inference_dtype=self.pipeline.inference_dtype

    @property
    def hp_model(self):
        # Outside a source-mask context, semantic top-preservation uses real parsing.
        return self.pipeline.hp_model

    def __call__(self,**kwargs):
        self.last_source_preparation=None
        if self.preserve_upper and kwargs['category']=='bottoms':
            kwargs['preserve_upper']=True
            if self.preserve_feet:
                kwargs['preserve_feet']=True
        entry=self.entries.get(fingerprint(kwargs['garment_image']))
        if entry is None or entry[0]!=kwargs['category']:
            raise ValueError('Missing or mismatched garment instance mask')
        if self.bottom_source_cutout is not None and kwargs['category']=='bottoms':
            if (not kwargs['segmentation_free'] and not self.allow_masked_target) or kwargs['garment_photo_type']!='model':
                raise ValueError('Source cutout requires worn source and explicit masked-target opt-in')
            prepared,bounds=source_cutout(kwargs['garment_image'],entry[1],crop=self.bottom_source_cutout=='crop')
            self.last_source_preparation={'framing':self.bottom_source_cutout,'crop_bounds':bounds,
                'prepared_size':prepared.size,'prepared_rgb_sha256':fingerprint(prepared)[1],
                'photo_type':'flat-lay preprocessing of worn-photo cutout, not a real flat-lay photo',
                'changes':['source mask before pre-resize','dummy source pose','skip upstream source masking']}
            kwargs['garment_image']=prepared
            kwargs['garment_photo_type']='flat-lay'
            return self.pipeline(**kwargs)
        with self.hp_model.use(entry[1],kwargs['category'],kwargs['garment_image'].size,
                               segmentation_free=kwargs['segmentation_free'],garment_photo_type=kwargs['garment_photo_type'],
                               allow_masked_target=self.allow_masked_target):
            return self.pipeline(**kwargs)


def run(selection_path, *, masked_bottom=False):
    root=Path(__file__).resolve().parents[2]
    selection_path=Path(selection_path)
    selection=json.loads(selection_path.read_text(encoding='utf-8'))
    items=validate_selection(selection,root)
    pipeline=MaskedOutfitPipeline(root,items,allow_masked_target=masked_bottom)
    metadata={'method':'Researcher-assisted SAM source instance mask on both pieces, original source poses retained',
        'baseline_outfit':'runs/protected-outfit-90dfb46e' if {i['id'] for i in items}=={'tshirt','wide-trousers'} else None,
        'source_extractions':pipeline.provenance,'dtype':str(pipeline.inference_dtype),
        'fashn_commit':command_output(['git','-C',str(root/'vendor/fashn-vton-1.5'),'rev-parse','HEAD']),
        'model_provenance':json.loads((root/'model-provenance.json').read_text(encoding='utf-8')),
        'limits':['Source masks are researcher-assisted, not automatic','Height/weight are profile metadata, not measured avatar reconstruction',
                  'Two-piece example does not change the ten-case 7/10 baseline','FASHN human parser research-license restriction remains']}
    result=compose(selection_path,pipeline=pipeline,extra_metadata=metadata,
                   bottom_segmentation_free=not masked_bottom)
    write_json(result/'source-mask-provenance.json',metadata)
    (root/'runs/latest-masked-outfit.txt').write_text(str(result),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--selection',type=Path,default=Path('evaluation/manifests/tshirt-trousers.outfit.json'))
    parser.add_argument('--masked-bottom',action='store_true',help='Use target masking only for the bottom transfer')
    args=parser.parse_args()
    run(args.selection,masked_bottom=args.masked_bottom)
