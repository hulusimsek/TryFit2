import importlib.util
import sys
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from catvton_inputs import letterbox, source_cutout, target_inputs


class InputTests(unittest.TestCase):
    def test_target_mask_and_full_body_share_identical_letterbox(self):
        picture=Image.new('RGB',(100,150),(30,40,50))
        canvas,transform=letterbox(picture,(768,1024))
        self.assertEqual(canvas.size,(768,1024))
        self.assertEqual(transform['resized_size'],[683,1024])
        mask=Image.new('L',picture.size,255)
        padded,mask_transform=letterbox(mask,(768,1024),mask=True)
        self.assertEqual(transform,mask_transform)
        self.assertEqual(padded.getpixel((0,512)),0)
        self.assertEqual(canvas.getpixel((384,0)),(30,40,50))
        self.assertEqual(canvas.getpixel((384,1023)),(30,40,50))

    def test_cutout_preserves_selected_pixels_and_uses_white_background(self):
        picture=Image.new('RGB',(60,80),(12,34,56))
        mask=np.zeros((80,60),dtype='uint8');mask[20:60,20:40]=255
        cutout,box=source_cutout(picture,mask)
        self.assertEqual(cutout.getpixel((25-box[0],30-box[1])),(12,34,56))
        self.assertEqual(cutout.getpixel((0,0)),(255,255,255))
        with self.assertRaises(ValueError):source_cutout(picture,mask[:10])

    def test_invalid_target_annotation_rejected(self):
        with self.assertRaises(ValueError):target_inputs(Image.new('RGB',(20,30)),{'polygon_normalized':[[0,0],[2,0],[1,1]]})

    def test_hand_exclusion_holes_are_aligned_and_validated(self):
        image=Image.new('RGB',(100,150),'gray')
        annotation={'polygon_normalized':[[.2,.2],[.8,.2],[.8,.8],[.2,.8]],
                    'exclusion_polygons_normalized':[[[.3,.3],[.5,.3],[.5,.5],[.3,.5]]]}
        _,hard,_,_,_=target_inputs(image,annotation,size=image.size)
        self.assertEqual(hard.getpixel((40,60)),0)
        self.assertEqual(hard.getpixel((60,60)),255)
        annotation['exclusion_polygons_normalized']=[[[0,0],[float('nan'),0],[1,1]]]
        with self.assertRaises(ValueError):target_inputs(image,annotation)

    def test_preservation_mask_blocks_soft_alpha_without_disabling_other_edits(self):
        image=Image.new('RGB',(100,150),'gray')
        annotation={'polygon_normalized':[[.1,.1],[.9,.1],[.9,.9],[.1,.9]]}
        protected=np.zeros((150,100),dtype='uint8');protected[30:90,30:50]=255
        _,hard,soft,_,_=target_inputs(image,annotation,size=image.size,preserve_mask=protected)
        self.assertEqual(hard.getpixel((40,60)),0)
        self.assertTrue((np.asarray(soft)[protected==255]==0).all())
        self.assertGreater(soft.getpixel((70,60)),200)
        for invalid in [protected[:10],np.ones_like(protected),np.full_like(protected,255)]:
            with self.assertRaises(ValueError):target_inputs(image,annotation,preserve_mask=invalid)


@unittest.skipUnless(importlib.util.find_spec('diffusers'),'CatVTON isolated environment required')
class SequentialUNetTests(unittest.TestCase):
    def test_actual_adapted_unet_matches_batched_forward(self):
        import torch
        from diffusers import UNet2DConditionModel
        root=Path(__file__).resolve().parents[2]
        sys.path.insert(0,str(root/'vendor/CatVTON'))
        from model.utils import init_adapter
        from model.attn_processor import SkipAttnProcessor
        from catvton_probe import sequential_unet
        torch.manual_seed(42)
        model=UNet2DConditionModel(sample_size=16,in_channels=9,out_channels=4,layers_per_block=1,
            block_out_channels=(32,64),down_block_types=('DownBlock2D','AttnDownBlock2D'),
            up_block_types=('AttnUpBlock2D','UpBlock2D'),cross_attention_dim=32,attention_head_dim=8,norm_num_groups=8).eval()
        init_adapter(model,cross_attn_cls=SkipAttnProcessor)
        sample=torch.randn(2,9,16,16)
        with torch.no_grad():
            batched=model(sample,torch.tensor(5),encoder_hidden_states=None,return_dict=False)[0]
            separate=sequential_unet(model.forward,sample,torch.tensor(5),encoder_hidden_states=None,return_dict=False)[0]
        torch.testing.assert_close(batched,separate,rtol=1e-5,atol=1e-5)


if __name__=='__main__':unittest.main()
