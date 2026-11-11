"""Pin public CatVTON research weights and dependencies; verify Hub LFS hashes."""
import concurrent.futures
import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'ai-worker/models/catvton'
REPOS = [
    ('zhengchong/CatVTON', ['mix-48k-1024/attention/model.safetensors'], 'adapter'),
    ('booksforcharlie/stable-diffusion-inpainting', ['unet/config.json', 'unet/diffusion_pytorch_model.bin', 'scheduler/scheduler_config.json'], 'base'),
    ('stabilityai/sd-vae-ft-mse', ['config.json', 'diffusion_pytorch_model.bin'], 'vae'),
]


def request(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TryFitNextResearch/1.0'}),timeout=45)


def metadata(repo):
    for attempt in range(5):
        try:
            with request('https://huggingface.co/api/models/'+repo+'?blobs=true') as response:
                return json.load(response)
        except Exception:
            if attempt == 4:raise
            time.sleep(1)


def download(entry):
    path=DEST/entry['relative_path'];path.parent.mkdir(parents=True,exist_ok=True)
    for attempt in range(4):
        try:
            if not path.exists():
                partial=path.with_suffix(path.suffix+'.part')
                with request(entry['url']) as response,partial.open('wb') as stream:
                    total=0;next_update=256*1024**2
                    while block:=response.read(4*1024**2):
                        stream.write(block);total+=len(block)
                        if total>=next_update:
                            print(entry['relative_path'],round(total/1024**2),'MiB',flush=True);next_update+=256*1024**2
                    if response.headers.get('Content-Length') and total!=int(response.headers['Content-Length']):
                        raise IOError('Incomplete download')
                partial.replace(path)
            digest=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
            if entry.get('expected_sha256') and digest!=entry['expected_sha256']:
                path.unlink();raise ValueError('Hub LFS checksum mismatch')
            if entry.get('expected_bytes') and path.stat().st_size!=entry['expected_bytes']:
                path.unlink();raise ValueError('Hub size mismatch')
            entry.update(sha256=digest,bytes=path.stat().st_size)
            print('VERIFIED',entry['relative_path'],flush=True)
            return entry
        except Exception as error:
            print('RETRY',entry['relative_path'],type(error).__name__,str(error),flush=True)
            if attempt==3:raise
            time.sleep(1)


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    record={'license':'CatVTON: CC BY-NC-SA 4.0, research comparison only','repositories':{},'files':[]}
    entries=[]
    for repo,files,subdir in REPOS:
        info=metadata(repo);revision=info['sha'];record['repositories'][repo]=revision
        siblings={v['rfilename']:v for v in info['siblings']}
        for filename in files:
            sibling=siblings[filename];lfs=sibling.get('lfs') or {}
            entries.append({'repo':repo,'revision':revision,'filename':filename,'relative_path':subdir+'/'+filename,
                'url':f'https://huggingface.co/{repo}/resolve/{revision}/{filename}',
                'expected_sha256':lfs.get('sha256'),'expected_bytes':sibling.get('size')})
    (DEST/'download-plan.json').write_text(json.dumps(record|{'files':entries},indent=2),encoding='utf-8')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        record['files']=list(pool.map(download,entries))
    (DEST/'provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('CATVTON_WEIGHTS_READY',flush=True)


if __name__=='__main__':main()
