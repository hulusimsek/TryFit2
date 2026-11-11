"""Auditable source cutouts and a manually annotated, fixed target mask."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def letterbox(image, size, *, mask=False):
    width, height = size
    scale = min(width/image.width, height/image.height)
    new_size = (round(image.width*scale), round(image.height*scale))
    resized = image.resize(new_size, Image.Resampling.NEAREST if mask else Image.Resampling.LANCZOS)
    canvas = Image.new('L' if mask else 'RGB', size, 0 if mask else (220,220,220))
    offset = ((width-new_size[0])//2, (height-new_size[1])//2)
    canvas.paste(resized, offset)
    return canvas, {'original_size':list(image.size), 'resized_size':list(new_size), 'offset':list(offset), 'canvas_size':list(size)}


def target_inputs(image, annotation, size=(768,1024), *, preserve_mask=None):
    def polygon_points(values):
        points = np.asarray(values, dtype=float)
        if points.ndim!=2 or points.shape[1]!=2 or len(points)<3 or not np.isfinite(points).all() or (points<0).any() or (points>1).any():
            raise ValueError('Invalid target polygon')
        return [tuple(p) for p in np.rint(points * [image.width-1,image.height-1]).astype(int)]
    mask = Image.new('L', image.size, 0)
    drawing=ImageDraw.Draw(mask)
    drawing.polygon(polygon_points(annotation['polygon_normalized']), fill=255)
    for excluded in annotation.get('exclusion_polygons_normalized',[]):
        drawing.polygon(polygon_points(excluded),fill=0)
    canvas, transform = letterbox(image, size)
    hard, mask_transform = letterbox(mask, size, mask=True)
    if transform != mask_transform:
        raise ValueError('Mask and target geometry differ')
    blurred = hard.filter(ImageFilter.GaussianBlur(9))
    if preserve_mask is not None:
        protected=np.asarray(preserve_mask)
        if (protected.shape!=(image.height,image.width) or not np.isin(protected,[0,255]).all()
                or not protected.any() or (protected!=0).all()):
            raise ValueError('Preservation mask must be a nontrivial binary mask matching the target')
        protected,protected_transform=letterbox(Image.fromarray(protected.astype('uint8')),size,mask=True)
        if protected_transform!=transform:raise ValueError('Preservation geometry differs')
        protected=np.asarray(protected)>0
        # Blur the original edit envelope, then exclude protected pixels. Blurring
        # after exclusion would let soft edit alpha leak back into hands/top.
        hard_pixels=np.array(hard);hard_pixels[protected]=0
        soft_pixels=np.array(blurred);soft_pixels[protected]=0
        hard=Image.fromarray(hard_pixels);blurred=Image.fromarray(soft_pixels)
    preview = np.asarray(canvas).copy()
    selected = np.asarray(hard)>0
    preview[selected] = (preview[selected]*.5 + np.array([0,180,120])*.5).astype('uint8')
    return canvas, hard, blurred, Image.fromarray(preview), transform


def source_cutout(source, mask):
    mask = np.asarray(mask)
    if mask.shape != (source.height,source.width) or not np.isin(mask,[0,1,255]).all():
        raise ValueError('Source and mask geometry or values invalid')
    selected = mask!=0
    if not selected.any() or selected.all():
        raise ValueError('Nontrivial source mask required')
    ys,xs=np.where(selected)
    box=(max(0,int(xs.min())-12),max(0,int(ys.min())-12),min(source.width,int(xs.max())+13),min(source.height,int(ys.max())+13))
    pixels=np.where(selected[...,None],np.asarray(source),255).astype('uint8')
    return Image.fromarray(pixels).crop(box), list(box)
