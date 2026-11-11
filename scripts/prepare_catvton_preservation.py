"""Prepare immutable CPU-parser preservation masks for CatVTON research targets."""
import argparse
import io
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ai-worker/app'))
from experiment import load_rgb,local_path,sha256


def write_once(path, data):
    if path.exists():
        if path.read_bytes()!=data:raise FileExistsError(f'Existing artifact differs: {path}')
        return
    path.write_bytes(data)


def run(annotations, output_dir):
    from fashn_human_parser import FashnHumanParser
    dest=local_path(ROOT,output_dir);dest.mkdir(parents=True,exist_ok=True)
    model=FashnHumanParser(model_id=str(ROOT/'ai-worker/models/human-parser'),device='cpu')
    records=[]
    for name in annotations:
        path=local_path(ROOT,name);spec=json.loads(path.read_text(encoding='utf-8'))
        source=local_path(ROOT,spec['image'])
        if sha256(source)!=spec['image_sha256']:raise ValueError('Annotated target changed')
        picture=load_rgb(source);labels=model.predict(np.asarray(picture))
        if labels.shape!=(picture.height,picture.width) or not np.isin(labels,np.arange(18)).all() or not (labels==3).any():
            raise ValueError('Valid matching target parsing with an upper garment required')
        binary=np.isin(labels,[1,2,3,12,13,15,16]).astype('uint8')*255
        if not binary.any() or (binary!=0).all():raise ValueError('Nontrivial preservation mask required')
        stem=path.name.removesuffix('.catvton.json');output=dest/(stem+'-preserve.png')
        buffer=io.BytesIO();Image.fromarray(binary).save(buffer,format='PNG');write_once(output,buffer.getvalue())
        records.append({'id':stem,'target':spec['image'],'target_sha256':spec['image_sha256'],
            'preserve_mask_image':output.relative_to(ROOT).as_posix(),'preserve_mask_sha256':sha256(output),
            'preserve_mask_target_sha256':spec['image_sha256']})
    encoded=json.dumps({'parser':'Local FASHN human parser on CPU','labels':[1,2,3,12,13,15,16],
        'purpose':'Explicit repaint preservation, not model-learned identity or measured fit','targets':records},indent=2).encode('utf-8')
    write_once(dest/'preservation-preparation.json',encoded)
    print(encoded.decode('utf-8'))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--annotation',action='append',required=True)
    parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();run(args.annotation,args.output_dir)
