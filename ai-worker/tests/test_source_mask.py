import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from source_mask import SourceMaskParser, SourcePoseAblation, choose_mask


class Base:
    def predict(self, image):
        return np.full(image.shape[:2], 9, dtype='uint8')


class SourceMaskTests(unittest.TestCase):
    def setUp(self):
        self.parser = SourceMaskParser(Base())
        self.mask = np.zeros((20, 10), dtype='uint8')
        self.mask[:10] = 255
        self.image = np.zeros((20, 10, 3), dtype='uint8')

    def test_source_override_keeps_target_parser_and_resizes_nearest(self):
        with self.parser.use(self.mask, 'tops', (10, 20)):
            self.assertTrue((self.parser.predict(self.image) == 9).all())
            labels = self.parser.predict(self.image[::2, ::2])
            self.assertEqual(set(np.unique(labels)), {0, 3})
            self.assertTrue((labels[:5] == 3).all())
            self.assertTrue((labels[5:] == 0).all())
        self.assertTrue((self.parser.predict(self.image) == 9).all())

    def test_call_contract_fails_and_clears_previous_mask(self):
        with self.assertRaises(RuntimeError):
            with self.parser.use(self.mask, 'tops', (10, 20)):
                self.parser.predict(self.image)
        self.assertIsNone(self.parser.active)
        with self.parser.use(self.mask, 'bottoms', (10, 20)):
            self.parser.predict(self.image)
            self.assertEqual(int(self.parser.predict(self.image)[0, 0]), 6)

    def test_invalid_usage_rejected(self):
        for options in ({'segmentation_free': False}, {'garment_photo_type': 'flat-lay'}):
            with self.assertRaises(ValueError):
                with self.parser.use(self.mask, 'tops', (10, 20), **options):
                    pass
        with self.assertRaises(ValueError):
            with self.parser.use(self.mask, 'tops', (20, 10)):
                pass

    def test_prompt_constraints_override_higher_iou(self):
        candidates = np.zeros((2, 8, 8), dtype=bool)
        candidates[0, :4] = True
        candidates[1] = True
        mask, index = choose_mask(candidates, [.8, .99], [[2, 2], [5, 5]], [1, 0])
        self.assertEqual(index, 0)
        with self.assertRaises(ValueError):
            choose_mask(candidates[1:], [.99], [[2, 2], [5, 5]], [1, 0])

    def test_masked_target_opt_in_keeps_real_target_labels_and_rejects_empty(self):
        with self.parser.use(self.mask,'bottoms',(10,20),segmentation_free=False,allow_masked_target=True):
            self.assertTrue((self.parser.predict(self.image)==9).all())
            self.assertEqual(set(np.unique(self.parser.predict(self.image))),{0,6})
        class Empty:
            def predict(_,image):return np.zeros(image.shape[:2],dtype='uint8')
        parser=SourceMaskParser(Empty())
        with self.assertRaises(ValueError):
            with parser.use(self.mask,'bottoms',(10,20),segmentation_free=False,allow_masked_target=True):
                parser.predict(self.image)
        self.assertIsNone(parser.active)

    def test_source_pose_ablation_keeps_target_and_clears_state(self):
        calls = []
        pose = SourcePoseAblation(lambda image: calls.append(image) or 'target-pose', lambda: 'empty-source')
        with pose.use():
            self.assertEqual(pose('target'), 'target-pose')
            self.assertEqual(pose('source'), 'empty-source')
        self.assertEqual(calls, ['target'])
        self.assertIsNone(pose.calls)
        with self.assertRaises(RuntimeError):
            with pose.use():
                pose('target')
        self.assertIsNone(pose.calls)
        self.assertEqual(pose('outside-context'), 'target-pose')


if __name__ == '__main__':
    unittest.main()
