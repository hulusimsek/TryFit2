import copy
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from avatar_suite import validate_profiles
from experiment import sha256


class AvatarSuiteTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.root=Path(self.directory.name)
        self.catalog={'schema_version':1,'continuous_height_weight_mapping':False,'profiles':[]}
        for i,color in enumerate(['red','green','blue']):
            p=self.root/(str(i)+'.png');Image.new('RGB',(10,16),color).save(p)
            self.catalog['profiles'].append({'id':'profile-'+str(i),'image':p.name,'image_sha256':sha256(p),'height_cm':175,'weight_kg':55+15*i,'measured':False})

    def tearDown(self):self.directory.cleanup()

    def test_distinct_real_inputs_required_not_only_different_numeric_tags(self):
        self.assertEqual(len(validate_profiles(self.catalog,self.root)),3)
        duplicate=copy.deepcopy(self.catalog)
        duplicate['profiles'][1]['image_sha256']=duplicate['profiles'][0]['image_sha256']
        duplicate['profiles'][1]['image']=duplicate['profiles'][0]['image']
        with self.assertRaises(ValueError):validate_profiles(duplicate,self.root)

    def test_modified_target_and_unsupported_measurement_claim_rejected(self):
        invalid=copy.deepcopy(self.catalog);invalid['profiles'][0]['measured']=True
        with self.assertRaises(ValueError):validate_profiles(invalid,self.root)
        Image.new('RGB',(10,16),'black').save(self.root/'0.png')
        with self.assertRaises(ValueError):validate_profiles(self.catalog,self.root)


if __name__=='__main__':unittest.main()
