import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from experiment import sha256
from source_mask import SourceMaskParser
from masked_outfit import MaskedOutfitPipeline,source_cutout


class BaseParser:
    def predict(self,image):return np.full(image.shape[:2],9,dtype='uint8')


class FakePipeline:
    inference_dtype='test-only'
    def __init__(self):self.hp_model=SourceMaskParser(BaseParser())
    def __call__(self,**kwargs):
        self.last_kwargs=kwargs
        target=self.hp_model.predict(np.asarray(kwargs['person_image']))
        source=self.hp_model.predict(np.asarray(kwargs['garment_image']))
        return target,source


class MaskedOutfitTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.root=Path(self.directory.name)
        self.items=[]
        for name,category,color in [('tee','tops','blue'),('pants','bottoms','black')]:
            source=self.root/(name+'.png');Image.new('RGB',(10,16),color).save(source)
            directory=self.root/'runs'/('source-extraction-'+name+'-refined');directory.mkdir(parents=True)
            mask=np.zeros((16,10),dtype='uint8');mask[2:14,2:8]=255;Image.fromarray(mask).save(directory/'mask.png')
            metadata={'annotation':{'id':name,'category':category,'image_sha256':sha256(source)},'mask_sha256':sha256(directory/'mask.png')}
            (directory/'extraction.json').write_text(json.dumps(metadata),encoding='utf-8')
            self.items.append({'id':name,'category':category,'image':source.name,'image_sha256':sha256(source)})

    def tearDown(self):self.directory.cleanup()

    def test_each_piece_gets_its_own_mask_and_composition_parsing_stays_available(self):
        with patch('masked_outfit.create_pipeline',return_value=FakePipeline()):
            model=MaskedOutfitPipeline(self.root,self.items)
        for item,expected in zip(self.items,[3,6]):
            target,source=model(person_image=Image.new('RGB',(10,16),'red'),garment_image=Image.open(self.root/item['image']).convert('RGB'),category=item['category'],segmentation_free=True,garment_photo_type='model')
            self.assertTrue((target==9).all());self.assertEqual(set(np.unique(source)),{0,expected})
        self.assertTrue((model.hp_model.predict(np.zeros((16,10,3),dtype='uint8'))==9).all())
        with self.assertRaises(ValueError):
            model(garment_image=Image.new('RGB',(10,16),'green'),category='tops')

    def test_changed_mask_rejected_before_reserving_pipeline(self):
        Image.new('L',(10,16),255).save(self.root/'runs/source-extraction-tee-refined/mask.png')
        with patch('masked_outfit.create_pipeline') as factory:
            with self.assertRaises(ValueError):MaskedOutfitPipeline(self.root,self.items)
            factory.assert_not_called()

    def test_upper_constraint_is_only_enabled_for_bottom_when_requested(self):
        pipeline=FakePipeline()
        with patch('masked_outfit.create_pipeline',return_value=pipeline):
            model=MaskedOutfitPipeline(self.root,self.items,allow_masked_target=True,preserve_upper=True)
        for item in self.items:
            model(person_image=Image.new('RGB',(10,16),'red'),
                  garment_image=Image.open(self.root/item['image']).convert('RGB'),category=item['category'],
                  segmentation_free=item['category']=='tops',garment_photo_type='model')
            self.assertEqual(pipeline.last_kwargs.get('preserve_upper',False),item['category']=='bottoms')

    def test_cutout_crops_without_changing_selected_pixels_and_rejects_bad_masks(self):
        pixels=np.arange(60*40*3,dtype='uint8').reshape(60,40,3)
        picture=Image.fromarray(pixels)
        mask=np.zeros((60,40),dtype='uint8');mask[20:40,10:30]=255
        result,bounds=source_cutout(picture,mask,crop=True)
        x,y,right,bottom=bounds
        expected=np.where(mask[...,None]!=0,pixels,127)[y:bottom,x:right]
        np.testing.assert_array_equal(np.asarray(result),expected)
        self.assertLess(result.height,picture.height)
        self.assertTrue((np.asarray(result)[0]==127).all())
        for invalid in [np.zeros_like(mask),np.full_like(mask,255),mask[:10]]:
            with self.assertRaises(ValueError):source_cutout(picture,invalid,crop=True)

    def test_cutout_is_opt_in_and_does_not_consume_source_mask_context(self):
        pipeline=FakePipeline()
        with patch('masked_outfit.create_pipeline',return_value=pipeline):
            model=MaskedOutfitPipeline(self.root,self.items,allow_masked_target=True,
                                      bottom_source_cutout='crop',preserve_upper=True)
        item=self.items[1]
        kwargs=dict(person_image=Image.new('RGB',(10,16),'red'),
                    garment_image=Image.open(self.root/item['image']).convert('RGB'),category='bottoms',
                    segmentation_free=False,garment_photo_type='model')
        target,source=model(**kwargs)
        self.assertTrue((target==9).all());self.assertTrue((source==9).all())
        self.assertEqual(pipeline.last_kwargs['garment_photo_type'],'flat-lay')
        self.assertTrue(pipeline.last_kwargs['preserve_upper'])
        self.assertIsNone(model.hp_model.active)
        self.assertEqual(model.last_source_preparation['framing'],'crop')
        model.allow_masked_target=False
        with self.assertRaises(ValueError):model(**kwargs)
        self.assertIsNone(model.last_source_preparation)


if __name__=='__main__':unittest.main()
