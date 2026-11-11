import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from experiment import sha256
from skirt_gallery_probe import validate_sources


class GalleryComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'source.jpg').write_bytes(b'validation-only source hash input')
        (self.root/'alternative.jpg').write_bytes(b'distinct validation-only source hash input')
        self.original={'id':'skirt','product_url':'https://www.trendyol.com/shop/skirt-p-811422352',
            'category':'bottoms','garment_photo_type':'model','image':'source.jpg',
            'image_sha256':sha256(self.root/'source.jpg')}
        self.manifest={'schema_version':1,'selection_before_inference':True,
            'cases':[self.original,{**self.original,'id':'skirt-gallery-3','image':'alternative.jpg',
                                   'image_sha256':sha256(self.root/'alternative.jpg')}]}

    def tearDown(self):self.temp.cleanup()

    def test_same_listing_and_original_source_are_retained(self):
        self.assertEqual(len(validate_sources(self.manifest,self.root,self.original)),2)

    def test_different_product_or_missing_baseline_rejected(self):
        for mutation in ['other-product','missing-baseline']:
            manifest=copy.deepcopy(self.manifest)
            if mutation=='other-product':manifest['cases'][1]['product_url']='https://www.trendyol.com/shop/skirt-p-999'
            else:manifest['cases'][0]['id']='replacement'
            with self.assertRaises(ValueError):validate_sources(manifest,self.root,self.original)

    def test_changed_source_and_path_escape_rejected(self):
        for value in ['bad-hash','../outside.jpg']:
            manifest=copy.deepcopy(self.manifest)
            if value=='bad-hash':manifest['cases'][1]['image_sha256']='0'*64
            else:manifest['cases'][1]['image']=value
            with self.assertRaises(ValueError):validate_sources(manifest,self.root,self.original)

    def test_unfixed_selection_and_duplicate_ids_rejected(self):
        manifest=copy.deepcopy(self.manifest);manifest['selection_before_inference']=False
        with self.assertRaises(ValueError):validate_sources(manifest,self.root,self.original)
        manifest=copy.deepcopy(self.manifest);manifest['cases'][1]['id']='skirt'
        with self.assertRaises(ValueError):validate_sources(manifest,self.root,self.original)
        manifest=copy.deepcopy(self.manifest);manifest['cases'][1]['image_sha256']=self.original['image_sha256']
        with self.assertRaises(ValueError):validate_sources(manifest,self.root,self.original)


if __name__=='__main__':unittest.main()
