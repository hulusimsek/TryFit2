import json
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from local_skirt_inputs import skirt_inputs
import local_skirt
from experiment import sha256


class SkirtRuntimeTests(unittest.TestCase):
    def labels(self):
        labels=np.zeros((80,60),dtype='uint8');labels[5:40,15:45]=3
        labels[40:65,15:45]=6;labels[65:73,17:43]=14;labels[73:78,17:43]=15
        labels[30:45,7:12]=13
        return labels

    def test_tucking_releases_only_lower_top_and_keeps_hands_feet_protected(self):
        labels=self.labels()
        plain,protected,_=skirt_inputs(labels)
        tucked,tucked_mask,fade=skirt_inputs(labels,tuck_top=True)
        self.assertTrue((np.asarray(protected)[labels==3]==255).all())
        self.assertEqual(np.asarray(tucked_mask)[20,30],255)
        self.assertEqual(np.asarray(tucked_mask)[38,30],0)
        self.assertTrue((np.asarray(tucked_mask)[np.isin(labels,[13,15])]==255).all())
        self.assertTrue(tucked['tuck_top']);self.assertIsNone(plain['tuck_cut_row'])
        self.assertEqual(np.asarray(fade)[70,0],0)
        self.assertEqual(np.asarray(fade)[50,30],255)

    def test_missing_body_parts_fail_before_generation(self):
        for missing in [3,6,15]:
            labels=self.labels();labels[labels==missing]=0
            if missing==6:labels[labels==14]=0
            with self.assertRaises(ValueError):skirt_inputs(labels)

    def test_prepared_artifact_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'selection.json').write_text('{}')
            names=['01-top.png','cat-target.png','cat-hard-mask.png','cat-soft-mask.png','cat-preserve.png','cat-condition.png']
            for name in names:(root/name).write_bytes(b'validation-only')
            (root/'skirt-handoff.json').write_text(json.dumps({'selection_sha256':sha256(root/'selection.json'),
                'files':{name:sha256(root/name) for name in names}}))
            local_skirt.verify_prepared(root)
            (root/'cat-soft-mask.png').write_bytes(b'changed')
            with self.assertRaises(ValueError):local_skirt.verify_prepared(root)

    def test_child_failure_does_not_create_a_success_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);job=root/'runs/local-jobs'/('a'*32);job.mkdir(parents=True)
            python=root/'.venv-catvton/Scripts/python.exe';python.parent.mkdir(parents=True);python.touch()
            with patch.object(local_skirt,'ROOT',root),patch.object(local_skirt.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'upper')) as run:
                with self.assertRaises(subprocess.CalledProcessError):local_skirt.run(job)
                self.assertEqual(run.call_count,1)
            self.assertFalse((job/'result.png').exists());self.assertFalse((job/'outcome.json').exists())


if __name__=='__main__':unittest.main()
