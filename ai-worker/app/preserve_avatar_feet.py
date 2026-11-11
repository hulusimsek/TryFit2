"""Explicit optional compositing, not a claim that neural inference kept feet."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from experiment import load_rgb,sha256,write_json
from protect_outfit import preservation_metrics


def preserve(target,raw,labels):
    if target.size!=raw.size or labels.shape!=(raw.height,raw.width):
        raise ValueError('Foot preservation requires aligned geometry')
    binary=(labels==15).astype('uint8')*255
    if np.count_nonzero(binary)<30:
        raise ValueError('No usable bare-foot region found; no fallback replacement')
    alpha=cv2.GaussianBlur(binary,(3,3),0).astype('float32')/255
    image=np.rint(np.asarray(target).astype('float32')*alpha[...,None]+
                  np.asarray(raw).astype('float32')*(1-alpha[...,None])).clip(0,255).astype('uint8')
    result=Image.fromarray(image);mask=Image.fromarray(binary)
    checks=preservation_metrics(target,raw,result,mask)
    return result,mask,checks


def run(suite_dir):
    from fashn_human_parser import FashnHumanParser
    root=Path(__file__).resolve().parents[2]
    suite_dir=Path(suite_dir)
    record=json.loads((suite_dir/'suite.json').read_text(encoding='utf-8'))
    if record['status']!='completed':raise ValueError('Completed real outfit suite required')
    parser=FashnHumanParser(model_id=str(root/'ai-worker/models/human-parser'),device='cpu')
    for profile in record['profiles']:
        directory=root/profile['run_dir'];raw=load_rgb(directory/'02-bottom-raw.png')
        original=root/profile['avatar_image']
        if sha256(original)!=profile['avatar_sha256']:raise ValueError('Target changed')
        target=load_rgb(original)
        if abs(target.width/target.height-raw.width/raw.height)>1e-5:raise ValueError('Unaligned target aspect ratio')
        target=target.resize(raw.size,Image.Resampling.LANCZOS)
        labels=parser.predict(np.asarray(target))
        result,mask,checks=preserve(target,raw,labels)
        result.save(directory/'04-feet-preserved.png');mask.save(directory/'foot-preservation-mask.png')
        metadata={'method':'Explicit source-target foot pixels (human parser label 15), 3x3 edge feather; all other pixels from actual raw outfit',
            'not_neural_body_preservation':True,'raw_input':'02-bottom-raw.png','raw_sha256':sha256(directory/'02-bottom-raw.png'),
            'target_sha256':profile['avatar_sha256'],'output_sha256':sha256(directory/'04-feet-preserved.png'),
            'preservation_checks':checks,'limitations':['Semantic mask quality and occlusion boundaries require visual review','Original raw inference remains unchanged']}
        write_json(directory/'foot-preservation.json',metadata)
        profile['foot_preservation']=metadata
        print(profile['id'],checks,flush=True)
    write_json(suite_dir/'suite.json',record)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('suite_dir',type=Path);run(parser.parse_args().suite_dir)
