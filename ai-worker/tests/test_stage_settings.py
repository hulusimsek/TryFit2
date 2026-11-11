import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import protect_outfit
from experiment import sha256


class StageSettingsTests(unittest.TestCase):
    def test_only_bottom_uses_masked_target_and_record_matches_actual_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'runs').mkdir()
            for name,color in [('avatar','gray'),('tee','red'),('pants','blue')]:Image.new('RGB',(20,30),color).save(root/(name+'.png'))
            selection={'avatar':{'height_cm':175,'weight_kg':65,'image':'avatar.png'},'items':[
                {'id':name,'category':category,'garment_photo_type':'model','image':name+'.png','image_sha256':sha256(root/(name+'.png'))}
                for name,category in [('tee','tops'),('pants','bottoms')]]}
            path=root/'selection.json';path.write_text(json.dumps(selection),encoding='utf-8')
            labels=np.zeros((30,20),dtype='uint8');labels[3:15,4:16]=3
            class Fake:
                hp_model=SimpleNamespace(predict=lambda _:labels)
                def __init__(self):self.calls=[]
                def __call__(self,**kwargs):
                    self.calls.append(kwargs)
                    return SimpleNamespace(images=[Image.new('RGB',(20,30),'red' if kwargs['category']=='tops' else 'blue')])
            model=Fake()
            with patch.object(protect_outfit,'__file__',str(root/'ai-worker/app/protect_outfit.py')):
                dest=protect_outfit.run(path,pipeline=model,bottom_segmentation_free=False)
            self.assertTrue(model.calls[0]['segmentation_free'])
            self.assertFalse(model.calls[1]['segmentation_free'])
            record=json.loads((dest/'run.json').read_text())
            self.assertTrue(record['stage_settings']['top']['segmentation_free'])
            self.assertFalse(record['stage_settings']['bottom']['segmentation_free'])
            self.assertEqual(record['status'],'completed')


if __name__=='__main__':unittest.main()
