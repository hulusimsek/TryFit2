import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import numpy as np
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from upper_preservation import UpperPreservingPipelineMixin, preservation_alpha
from source_mask import SourceMaskParser
from upper_preservation_probe import run as run_probe


class UpperPreservationTests(unittest.TestCase):
    def test_protection_has_free_boundary_and_never_covers_lower_garment(self):
        labels = np.zeros((40, 30), dtype='uint8')
        labels[2:22, 3:27] = 3
        labels[22:38, 3:27] = 6
        alpha = preservation_alpha(labels, edge_pixels=3)
        self.assertEqual(alpha[10, 15], 1)
        self.assertEqual(alpha[21, 15], 0)
        self.assertTrue((alpha[labels == 6] == 0).all())
        self.assertTrue(((alpha > 0) & (alpha < 1)).any())

    def test_missing_upper_garment_fails_instead_of_claiming_preservation(self):
        with self.assertRaises(ValueError):
            preservation_alpha(np.zeros((20, 20), dtype='uint8'))

    def test_visible_torso_is_preserved_without_freezing_waistband_or_legs(self):
        labels=np.zeros((80,40),dtype='uint8')
        labels[2:25,5:35]=3
        labels[25:45,5:35]=16
        labels[45:51,5:35]=7
        labels[51:60,5:35]=5
        labels[60:77,5:35]=14
        alpha=preservation_alpha(labels)
        self.assertEqual(alpha[34,20],1)
        self.assertTrue((alpha[np.isin(labels,[5,7,14])]==0).all())

    def test_feet_are_opt_in_with_free_edges_and_missing_feet_fail(self):
        labels = np.zeros((60, 40), dtype='uint8')
        labels[2:22, 4:36] = 3
        labels[22:40, 4:36] = 6
        labels[40:58, 4:36] = 15
        self.assertEqual(preservation_alpha(labels)[48, 20], 0)
        alpha = preservation_alpha(labels, preserve_feet=True)
        self.assertEqual(alpha[48, 20], 1)
        self.assertEqual(alpha[40, 20], 0)
        self.assertEqual(alpha[57, 0], 1)  # Floor beside the feet, not only toe pixels.
        self.assertTrue((alpha[labels == 6] == 0).all())
        labels[labels == 15] = 0
        with self.assertRaisesRegex(ValueError, 'No feet'):
            preservation_alpha(labels, preserve_feet=True)

    def test_probe_rejects_multiple_changes_and_invalid_guidance_before_loading_model(self):
        with self.assertRaisesRegex(ValueError, 'only one'):
            run_probe([], maskless_bottom=True, guidance_scale=2.5)
        for guidance in [float('nan'), float('inf'), 0, 6]:
            with self.assertRaises(ValueError):
                run_probe([], guidance_scale=guidance)
        with self.assertRaises(ValueError):
            run_probe([], preserve_feet=True)

    def test_sampling_protects_only_selected_region_and_conditions_next_step(self):
        # A zero-velocity model exposes the constraint trajectory without GPU.
        seen = []
        class Parent:
            def _sample(self, **kwargs):
                raise AssertionError('Constrained call must use its own sampling loop')
        class Model(UpperPreservingPipelineMixin, Parent):
            pass
        model = Model()
        reference = np.full((4, 6, 3), 200, dtype='uint8')
        alpha = np.zeros((4, 6), dtype='float32'); alpha[:, :3] = 1
        model._upper_constraint = reference, alpha
        def forward(images, time, **kwargs):
            seen.append((images.clone(), float(time[0])))
            return {'v_c': torch.zeros_like(images), 'v_u': torch.zeros_like(images)}
        model.tryon_model = SimpleNamespace(forward_for_cfg=forward)
        ca = torch.zeros((1, 3, 4, 6))
        kwargs = dict(ca_images=ca, garment_images=ca, person_poses=ca,
                      garment_poses=ca, garment_categories=torch.tensor([2]), num_timesteps=3)
        torch.manual_seed(42)
        result = np.array(model._sample(**kwargs)[0])
        self.assertLessEqual(np.abs(result[:, :3].astype(int) - 200).max(), 1)
        self.assertFalse((result[:, 3:] == 200).all())
        noise = seen[0][0]
        for images, time in seen[1:]:
            expected = (1 - time) * noise[..., :3] + time * (200 / 127.5 - 1)
            torch.testing.assert_close(images[..., :3], expected)
            torch.testing.assert_close(images[..., 3:], noise[..., 3:])

    def test_default_sampler_is_unchanged(self):
        class Parent:
            def _sample(self, **kwargs): return 'original'
        class Model(UpperPreservingPipelineMixin, Parent): pass
        self.assertEqual(Model()._sample(), 'original')

    def test_source_parser_contract_and_constraint_cleanup_on_inference_failure(self):
        class Parser:
            def predict(self, image):
                labels = np.zeros(image.shape[:2], dtype='uint8')
                labels[2:18, 2:18] = 3
                return labels
        class Parent:
            def __call__(self, **kwargs):
                self.hp_model.predict(np.asarray(kwargs['person_image']))
                self.hp_model.predict(np.asarray(kwargs['garment_image']))
                raise RuntimeError('Inference failed')
        class Model(UpperPreservingPipelineMixin, Parent): pass
        model = Model()
        model.hp_model = SourceMaskParser(Parser())
        model.pre_resize = lambda picture, **kwargs: picture
        model.tryon_model = SimpleNamespace(input_shape=(30, 20))
        picture = Image.new('RGB', (20, 30), 'red')
        mask = np.zeros((30, 20), dtype='uint8'); mask[15:28] = 255
        with self.assertRaisesRegex(RuntimeError, 'Inference failed'):
            with model.hp_model.use(mask, 'bottoms', picture.size,
                                    segmentation_free=False, allow_masked_target=True):
                model(preserve_upper=True, person_image=picture, garment_image=picture,
                      category='bottoms', segmentation_free=False)
        self.assertIsNone(model._upper_constraint)
        self.assertIsNone(model.hp_model.active)

    def test_maskless_feet_constraint_keeps_real_target_and_source_call_contract(self):
        class Parser:
            def predict(self, image):
                labels = np.zeros(image.shape[:2], dtype='uint8')
                labels[2:18, 2:18] = 3
                labels[20:29, 2:18] = 15
                return labels
        class Parent:
            def __call__(self, **kwargs):
                target = self.hp_model.predict(np.asarray(kwargs['person_image']))
                source = self.hp_model.predict(np.asarray(kwargs['garment_image']))
                return target, source
        class Model(UpperPreservingPipelineMixin, Parent): pass
        model = Model(); model.hp_model = SourceMaskParser(Parser())
        model.pre_resize = lambda picture, **kwargs: picture
        model.tryon_model = SimpleNamespace(input_shape=(30, 20))
        picture = Image.new('RGB', (20, 30), 'red')
        mask = np.zeros((30, 20), dtype='uint8'); mask[15:28] = 255
        with model.hp_model.use(mask, 'bottoms', picture.size):
            target, source = model(preserve_upper=True, preserve_feet=True, person_image=picture,
                                   garment_image=picture, category='bottoms', segmentation_free=True)
        self.assertEqual(set(np.unique(target)), {0, 3, 15})
        self.assertEqual(set(np.unique(source)), {0, 6})
        self.assertIsNone(model._upper_constraint)
        self.assertIsNone(model.hp_model.active)


if __name__ == '__main__':
    unittest.main()
