"""Runtime skirt edit envelope and explicitly requested upper wearing style."""
import numpy as np
import cv2
from PIL import Image


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
    end=min(height-1,int(garments.max() if len(garments) else ys.max())+max(2,round(height*.005)))
    waist=cut if tuck_top else int(top_y.max())
    hip=min(end-1,waist+round(height*.13))
    knee=min(end-1,waist+round(height*.27))
    low_rows=lower & (np.indices(labels.shape)[0]>=np.quantile(ys,.8))
    low_x=np.where(low_rows)[1]
    left=max(0,int(xs.min())-padding);right=min(width-1,int(xs.max())+padding)
    bottom_left=max(0,int(low_x.min())-max(2,padding//3))
    bottom_right=min(width-1,int(low_x.max())+max(2,padding//3))
    points=[(int(xs.min()),start),(int(xs.max()),start),(right,hip),(bottom_right,knee),
            (bottom_right,end),(bottom_left,end),(bottom_left,knee),(left,hip)]
    # Background is editable only in a bounded expansion near the mini-skirt.
    # Calf/hand surroundings remain the actual target floor rather than generated texture.
    distance=cv2.distanceTransform((~lower).astype('uint8'),cv2.DIST_L2,5)
    outward=np.clip((padding-distance)/max(1,padding*.65),0,1)
    rows=np.indices(labels.shape)[0]
    vertical=np.clip((waist+height*.27-rows)/max(1,height*.06),0,1)
    background_alpha=np.ones(labels.shape,dtype='float32')
    background_alpha[labels==0]=(outward*vertical)[labels==0]
    annotation={'polygon_normalized':[[x/(width-1),y/(height-1)] for x,y in points],
        'method':'Runtime real target parsing; skirt envelope; explicit preservation applied after mask blur',
        'tuck_top':tuck_top,'tuck_cut_row':cut if tuck_top else None,
        'style_limits':'Tucking permits regeneration of the lower 22% of the detected top height; garment edges and fit are approximate'}
    return annotation,Image.fromarray(protected.astype('uint8')*255),Image.fromarray(np.rint(background_alpha*255).astype('uint8'))
