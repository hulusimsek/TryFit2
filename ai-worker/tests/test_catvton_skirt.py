import json
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from catvton_skirt_probe import prepare_source,load_preservation_mask
from experiment import sha256


class SkirtSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        Image.new('RGB',(40,60),(15,25,35)).save(self.root/'source.png')
        self.case={'id':'skirt','category':'bottoms','image':'source.png',
                   'image_sha256':sha256(self.root/'source.png')}
        self.extraction=self.root/'runs/source-extraction-skirt-refined';self.extraction.mkdir(parents=True)
        mask=np.zeros((60,40),dtype='uint8');mask[20:40,10:30]=255
        Image.fromarray(mask).save(self.extraction/'mask.png')
        self.metadata={'annotation':{'id':'skirt','category':'bottoms','image_sha256':self.case['image_sha256']},
                       'mask_sha256':sha256(self.extraction/'mask.png')}
        self.save()

    def save(self):
        (self.extraction/'extraction.json').write_text(json.dumps(self.metadata),encoding='utf-8')

    def tearDown(self):self.temp.cleanup()

    def test_verified_cutout_retains_source_pixels(self):
        condition,metadata=prepare_source(self.root,self.case)
        left,top,_,_=metadata['crop_box']
        self.assertEqual(condition.getpixel((20-left,30-top)),(15,25,35))
        self.assertEqual(metadata['source_sha256'],self.case['image_sha256'])

    def test_wrong_mask_identity_or_changed_pixels_rejected(self):
        self.metadata['annotation']['id']='other-skirt';self.save()
        with self.assertRaises(ValueError):prepare_source(self.root,self.case)
        self.metadata['annotation']['id']='skirt';self.save()
        Image.new('L',(40,60),255).save(self.extraction/'mask.png')
        with self.assertRaises(ValueError):prepare_source(self.root,self.case)

    def test_preservation_mask_is_bound_to_target_and_hash(self):
        path=self.extraction/'mask.png'
        annotation={'image_sha256':self.case['image_sha256'],'preserve_mask_image':path.relative_to(self.root).as_posix(),
                    'preserve_mask_target_sha256':self.case['image_sha256'],'preserve_mask_sha256':sha256(path)}
        self.assertEqual(load_preservation_mask(self.root,annotation).size,(40,60))
        annotation['preserve_mask_target_sha256']='0'*64
        with self.assertRaises(ValueError):load_preservation_mask(self.root,annotation)
        annotation['preserve_mask_target_sha256']=self.case['image_sha256'];annotation['preserve_mask_sha256']='0'*64
        with self.assertRaises(ValueError):load_preservation_mask(self.root,annotation)


if __name__=='__main__':unittest.main()
