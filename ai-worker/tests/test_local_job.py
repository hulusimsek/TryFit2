import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import local_job
from experiment import sha256


class LocalJobTests(unittest.TestCase):
    def test_job_directory_cannot_escape_application_job_root(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            with self.assertRaises(ValueError):local_job.run(path)
            self.assertFalse((path/'outcome.json').exists())

    def test_unsupported_product_records_failure_without_loading_gpu_or_fallback_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifests=root/'evaluation/manifests';manifests.mkdir(parents=True)
            profiles=[]
            for i,color in enumerate(['red','green','blue']):
                image=root/(str(i)+'.png');Image.new('RGB',(10,16),color).save(image)
                profiles.append({'id':'p'+str(i),'image':image.name,'image_sha256':sha256(image),'height_cm':175,'weight_kg':55+i*10,'measured':False})
            (manifests/'avatar-profiles.json').write_text(json.dumps({'schema_version':1,'continuous_height_weight_mapping':False,'profiles':profiles}),encoding='utf-8')
            (manifests/'trendyol-10.actual.json').write_text(json.dumps({'cases':[]}),encoding='utf-8')
            job=root/'runs/local-jobs'/('a'*32);job.mkdir(parents=True)
            (job/'request.json').write_text(json.dumps({'profileId':'p0','topId':'../../unknown','bottomId':'skirt'}),encoding='utf-8')
            with patch.object(local_job,'__file__',str(root/'ai-worker/app/local_job.py')),patch.object(local_job,'MaskedOutfitPipeline') as factory:
                with self.assertRaises(ValueError):local_job.run(job)
                factory.assert_not_called()
            self.assertEqual(json.loads((job/'outcome.json').read_text())['status'],'failed')
            self.assertFalse((job/'result.png').exists())


if __name__=='__main__':unittest.main()
