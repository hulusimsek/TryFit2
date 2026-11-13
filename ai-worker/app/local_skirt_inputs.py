"""Runtime skirt edit envelope and explicitly requested upper wearing style."""
import numpy as np
import cv2
from PIL import Image


def _aline_skirt_envelope(labels, lower, *, waist, hip, hem):
    """Build a binary waist-to-hem A-line mask that does not narrow along thighs or touch outer arms."""
    height, width = labels.shape
    arm_mask = np.isin(labels, [12, 13])
    arm_gap = max(2, round(height * 0.004))
    base_flare = max(2, round(height * 0.008))
    aline_extra = max(1, round(height * 0.008))
    has_lower = lower.any(axis=1)
    band_end = max(waist, hem)
    valid_y = np.where(has_lower[waist:band_end + 1])[0] + waist
    editable_bg = np.zeros(labels.shape, dtype=bool)
    if not len(valid_y):
        return editable_bg, None

    band_len = band_end - waist + 1
    row_left = np.full(band_len, width, dtype=float)
    row_right = np.full(band_len, -1.0, dtype=float)
    for y in range(waist, band_end + 1):
        idx = y - waist
        if has_lower[y]:
            lx = np.where(lower[y])[0]
            row_left[idx] = float(lx.min())
            row_right[idx] = float(lx.max())
        elif idx > 0 and row_left[idx - 1] < width:
            row_left[idx] = row_left[idx - 1]
            row_right[idx] = row_right[idx - 1]
    first_idx = int(valid_y[0]) - waist
    if first_idx > 0:
        row_left[:first_idx] = row_left[first_idx]
        row_right[:first_idx] = row_right[first_idx]

    # Never collapse inward toward narrowing thighs between waist/hip and hem.
    cum_left = np.minimum.accumulate(row_left)
    cum_right = np.maximum.accumulate(row_right)
    ys_band = np.arange(waist, band_end + 1)
    hip_idx = min(band_len - 1, max(0, hip - waist))
    hip_span = float(cum_right[hip_idx] - cum_left[hip_idx] + 1)
    # Narrow pelvis silhouettes avoid excess hem wing flare above slim thighs so CatVTON keeps skirt geometry.
    narrow_silhouette = hip_span < round(height * 0.195)
    if narrow_silhouette:
        out_flare = float(base_flare)
    else:
        flare_t = np.clip((ys_band - hip) / max(1, band_end - hip), 0.0, 1.0)
        out_flare = base_flare + aline_extra * flare_t
    env_left = np.clip(np.floor(cum_left - out_flare), 0, width - 1).astype(int)
    env_right = np.clip(np.ceil(cum_right + out_flare), 0, width - 1).astype(int)

    arm_left_bound = np.zeros(band_len, dtype=int)
    arm_right_bound = np.full(band_len, width - 1, dtype=int)
    for idx, y in enumerate(ys_band):
        left_lim = max(0, min(width - 1, int(row_left[idx])))
        right_lim = max(0, min(width - 1, int(row_right[idx])))
        al = np.where(arm_mask[y, :left_lim])[0]
        ar = np.where(arm_mask[y, right_lim + 1:])[0] + right_lim + 1
        if len(al):
            arm_left_bound[idx] = int(al.max()) + arm_gap
        if len(ar):
            arm_right_bound[idx] = int(ar.min()) - arm_gap

    env_left = np.maximum(env_left, arm_left_bound)
    env_right = np.minimum(env_right, arm_right_bound)
    hip_left = int(env_left[hip_idx])
    hip_right = int(env_right[hip_idx])
    for idx in range(1, band_len):
        if ys_band[idx] > hip:
            if narrow_silhouette:
                # Hold a steady hip-width drape below forearms instead of pinching at wrists then flaring at hem.
                env_left[idx] = max(env_left[idx], hip_left, arm_left_bound[idx])
                env_right[idx] = min(env_right[idx], hip_right, arm_right_bound[idx])
            else:
                # Smooth outward progression below fingertips avoids an abrupt horizontal ledge.
                env_left[idx] = max(env_left[idx], env_left[idx - 1] - 1, arm_left_bound[idx])
                env_right[idx] = min(env_right[idx], env_right[idx - 1] + 1, arm_right_bound[idx])
        if has_lower[ys_band[idx]]:
            env_left[idx] = min(env_left[idx], int(row_left[idx]))
            env_right[idx] = max(env_right[idx], int(row_right[idx]))

    for idx, y in enumerate(ys_band):
        if env_left[idx] <= env_right[idx]:
            editable_bg[y, env_left[idx]:env_right[idx] + 1] = True

    if narrow_silhouette:
        taper_len = min(max(2, round(height * 0.01)), (height - 1) - band_end)
        if taper_len > 0:
            hem_left = int(env_left[-1])
            hem_right = int(env_right[-1])
            cur_left, cur_right = hem_left, hem_right
            for dy in range(1, taper_len + 1):
                y = band_end + dy
                if has_lower[y]:
                    lx = np.where(lower[y])[0]
                    target_left, target_right = int(lx.min()), int(lx.max())
                else:
                    target_left, target_right = cur_left, cur_right
                cur_left, cur_right = target_left, target_right
                t = dy / (taper_len + 1)
                tl = int(round(hem_left + (target_left - hem_left) * t))
                tr = int(round(hem_right + (target_right - hem_right) * t))
                al = np.where(arm_mask[y, :target_left])[0]
                ar = np.where(arm_mask[y, target_right + 1:])[0] + target_right + 1
                if len(al):
                    tl = max(tl, int(al.max()) + arm_gap)
                if len(ar):
                    tr = min(tr, int(ar.min()) - arm_gap)
                if has_lower[y]:
                    tl = min(tl, target_left)
                    tr = max(tr, target_right)
                if tl <= tr:
                    editable_bg[y, tl:tr + 1] = True

        bridge_len = min(max(taper_len, round(height * 0.03)), (height - 1) - band_end)
        for dy in range(taper_len + 1, bridge_len + 1):
            y = band_end + dy
            if has_lower[y]:
                lx = np.where(lower[y])[0]
                tl, tr = int(lx.min()), int(lx.max())
                if tl <= tr:
                    editable_bg[y, tl:tr + 1] = True

    return editable_bg, (hip_left, hip_right, int(env_left[-1]), int(env_right[-1]))


def skirt_inputs(labels, *, tuck_top=False):
    labels=np.asarray(labels)
    if labels.ndim!=2 or not np.isin(labels,np.arange(18)).all():raise ValueError('Invalid target parsing')
    top=labels==3;lower=np.isin(labels,[5,6,7,14])
    if not top.any() or not lower.any() or not (labels==15).any():
        raise ValueError('Upper garment, lower body and visible feet required')
    height,width=labels.shape;top_y=np.where(top)[0];ys,xs=np.where(lower)
    cut=int(round(top_y.min()+.78*(top_y.max()-top_y.min())))
    protected=np.isin(labels,[1,2,3,12,13,15,16])
    if tuck_top:protected[top & (np.indices(labels.shape)[0]>=cut)]=False
    padding=max(3,round(height*.02))
    start=max(0,min(int(ys.min()),cut if tuck_top else int(top_y.max()))-round(height*.045))
    garments=np.where(np.isin(labels,[5,6,7]))[0]
    feet_y=np.where(labels==15)[0]
    end=min(height-1,max(int(garments.max() if len(garments) else ys.max()),int(feet_y.min()))+max(2,round(height*.005)))
    waist=cut if tuck_top else int(top_y.max())
    hip=min(end-1,waist+round(height*.13))
    hem=min(end-1,max(hip,cut+round(height*.21)))
    knee=min(end-1,max(hem,waist+round(height*.27)))
    low_rows=lower & (np.indices(labels.shape)[0]>=np.quantile(ys,.8))
    low_x=np.where(low_rows)[1]
    left=max(0,int(xs.min())-padding);right=min(width-1,int(xs.max())+padding)
    bottom_left=max(0,int(low_x.min())-max(2,padding//3))
    bottom_right=min(width-1,int(low_x.max())+max(2,padding//3))
    # Background is editable in a solid A-line waist-to-hem envelope so CatVTON (>=128)
    # and repaint share the exact outer boundary without narrowing along upper thighs.
    editable_bg, bounds = _aline_skirt_envelope(labels, lower, waist=waist, hip=hip, hem=hem)
    if bounds is not None:
        left_hip, right_hip, left_hem, right_hem = bounds
        left = min(left, left_hip)
        right = max(right, right_hip)
        left_hem = min(left_hem, left)
        right_hem = max(right_hem, right)
    else:
        left_hem, right_hem = left, right
    points=[(int(xs.min()),start),(int(xs.max()),start),(right,hip),(right_hem,hem),(bottom_right,knee),
            (bottom_right,end),(bottom_left,end),(bottom_left,knee),(left_hem,hem),(left,hip)]
    rows=np.indices(labels.shape)[0]
    feet_distance=cv2.distanceTransform((labels!=15).astype('uint8'),cv2.DIST_L2,5)
    feet_fade=np.clip(feet_distance/max(4,round(height*.008)),0,1)
    background_alpha=np.ones(labels.shape,dtype='float32')
    background_alpha[labels==0]=editable_bg[labels==0].astype('float32')
    background_alpha*=feet_fade
    if tuck_top:
        # Feather downward from the tuck cut so VAE tone shifts in repaint do not form a hard horizontal bar.
        tuck_fade=np.clip((rows-cut)/max(4,round(height*.007)),0,1)
        background_alpha*=np.where(top,tuck_fade,1)
    annotation={'polygon_normalized':[[x/(width-1),y/(height-1)] for x,y in points],
        'method':'Runtime real target parsing; A-line skirt envelope; explicit preservation applied after mask blur',
        'tuck_top':tuck_top,'tuck_cut_row':cut if tuck_top else None,
        'style_limits':'Tucking permits regeneration of the lower 22% of the detected top height; garment edges and fit are approximate'}
    return annotation,Image.fromarray(protected.astype('uint8')*255),Image.fromarray(np.rint(background_alpha*255).astype('uint8'))


class SkirtMasks(tuple):
    """Container preserving 7-tuple return arity while providing repaint masks."""
    def __new__(cls, target, hard, soft, preserve, overlay, annotation, transform, *,
                repaint_soft=None, repaint_hard=None):
        instance = super().__new__(cls, (target, hard, soft, preserve, overlay, annotation, transform))
        instance.target = target
        instance.hard = hard
        instance.soft = soft
        instance.preserve = preserve
        instance.overlay = overlay
        instance.annotation = annotation
        instance.transform = transform
        instance.repaint_soft = repaint_soft if repaint_soft is not None else soft
        instance.repaint_hard = repaint_hard if repaint_hard is not None else hard
        return instance


def prepare_skirt_masks(target_image, labels, *, tuck_top=False, size=(768, 1024)):
    """Prepare CatVTON target canvas and aligned hard/soft masks from parsed target labels.

    Both tucked and untucked skirt flows use the unified waist-to-hem diffusion geometry
    (cut -> hem). In untucked flow, CatVTON synthesizes the skirt under the t-shirt to
    avoid aspect-ratio compression aliasing and color drift, while repaint_soft zeros out
    the t-shirt to keep FASHN 01-top.png intact in final compositing.
    """
    from catvton_inputs import letterbox, target_inputs

    diff_annotation, diff_preserve, diff_bg_alpha = skirt_inputs(labels, tuck_top=True)
    target, _, soft, _, transform = target_inputs(
        target_image,
        diff_annotation,
        size=size,
        preserve_mask=diff_preserve,
        blur_radius=0,
    )
    fade, fade_transform = letterbox(diff_bg_alpha, size, mask=True)
    if fade_transform != transform:
        raise ValueError('Fade mask and target geometry differ')
    soft = Image.fromarray(np.rint(np.asarray(soft).astype(float) * np.asarray(fade) / 255).astype('uint8'))
    hard = Image.fromarray((np.asarray(soft) >= 128).astype('uint8') * 255)
    preview = np.array(target)
    edited = np.asarray(hard) > 0
    preview[edited] = (preview[edited] * .5 + np.array([0, 180, 120]) * .5).astype('uint8')

    if tuck_top:
        repaint_soft = soft.copy()
        repaint_hard = hard.copy()
        annotation = diff_annotation
    else:
        top_canvas, _ = letterbox(Image.fromarray((np.asarray(labels) == 3).astype('uint8') * 255), size, mask=True)
        top_mask = np.asarray(top_canvas) > 0
        repaint_soft_arr = np.asarray(soft).copy()
        repaint_soft_arr[top_mask] = 0
        repaint_soft = Image.fromarray(repaint_soft_arr)
        repaint_hard = Image.fromarray((repaint_soft_arr >= 128).astype('uint8') * 255)
        annotation = {**diff_annotation, 'tuck_top': False, 'tuck_cut_row': None}

    return SkirtMasks(
        target,
        hard,
        soft,
        diff_preserve,
        Image.fromarray(preview),
        annotation,
        transform,
        repaint_soft=repaint_soft,
        repaint_hard=repaint_hard,
    )
