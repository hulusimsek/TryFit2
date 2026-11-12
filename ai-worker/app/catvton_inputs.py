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


def unletterbox(image, transform, *, mask=False):
    if not isinstance(transform, dict):
        raise ValueError('Target transform dictionary required')

    def _pair(key, minimum):
        value = transform.get(key)
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(f'Invalid transform field: {key}')
        first, second = value
        if (isinstance(first, bool) or isinstance(second, bool)
                or not isinstance(first, int) or not isinstance(second, int)):
            raise ValueError(f'Transform field {key} must contain integers')
        if first < minimum or second < minimum:
            raise ValueError(f'Transform field {key} out of range')
        return first, second

    orig_w, orig_h = _pair('original_size', 1)
    res_w, res_h = _pair('resized_size', 1)
    off_x, off_y = _pair('offset', 0)
    can_w, can_h = _pair('canvas_size', 1)
    if image.size != (can_w, can_h):
        raise ValueError(f'Image size {image.size} does not match transform canvas_size {(can_w, can_h)}')
    if off_x + res_w > can_w or off_y + res_h > can_h:
        raise ValueError('Transform crop box exceeds canvas bounds')
    scale = min(can_w / orig_w, can_h / orig_h)
    expected_resized = (round(orig_w * scale), round(orig_h * scale))
    expected_offset = ((can_w - expected_resized[0]) // 2, (can_h - expected_resized[1]) // 2)
    if (res_w, res_h) != expected_resized or (off_x, off_y) != expected_offset:
        raise ValueError('Transform geometry does not match letterbox specification')
    cropped = image.crop((off_x, off_y, off_x + res_w, off_y + res_h))
    resampling = Image.Resampling.NEAREST if mask else Image.Resampling.LANCZOS
    return cropped.resize((orig_w, orig_h), resampling)


def target_inputs(image, annotation, size=(768,1024), *, preserve_mask=None, blur_radius=9):
    if isinstance(blur_radius, bool) or not isinstance(blur_radius, (int, float)) or not np.isfinite(blur_radius) or blur_radius < 0:
        raise ValueError('Invalid blur_radius')
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
    blurred = hard.filter(ImageFilter.GaussianBlur(blur_radius)) if blur_radius > 0 else hard.copy()
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
