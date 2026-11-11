"""Controlled source-instance experiment. Original source pose is retained.

SAM points are research annotations, not automatic product selection.
"""
from contextlib import contextmanager
import numpy as np
from PIL import Image


def choose_mask(masks, scores, coords, labels):
    masks = np.asarray(masks, dtype=bool)
    coords = np.asarray(coords, dtype=int)
    labels = np.asarray(labels, dtype=bool)
    if masks.ndim != 3 or len(scores) != len(masks) or coords.shape != (len(labels), 2):
        raise ValueError("Invalid mask candidates or points")
    if not len(labels) or not labels.any() or labels.all():
        raise ValueError("Both positive and negative source points are required")
    if np.any(coords < 0) or np.any(coords[:, 0] >= masks.shape[2]) or np.any(coords[:, 1] >= masks.shape[1]):
        raise ValueError("Points outside image")
    valid = [i for i, mask in enumerate(masks)
             if np.array_equal(mask[coords[:, 1], coords[:, 0]], labels)
             and np.isfinite(scores[i]) and 0 < mask.mean() < 1]
    if not valid:
        raise ValueError("No SAM candidate satisfies all annotated points")
    index = max(valid, key=lambda i: scores[i])
    return masks[index], index


class SourceMaskParser:
    """Override only the second, source parsing call in the pinned FASHN pipeline."""
    def __init__(self, base):
        self.base = base
        self.active = None

    @contextmanager
    def use(self, mask, category, source_size, *, segmentation_free=True, garment_photo_type="model", allow_masked_target=False):
        if self.active is not None:
            raise RuntimeError("Nested source mask context")
        if (not segmentation_free and allow_masked_target is not True) or garment_photo_type != "model":
            raise ValueError("Masked target requires explicit opt-in with real target parsing; worn source required")
        label = {"tops": 3, "bottoms": 6, "one-pieces": 4}[category]
        mask = np.asarray(mask)
        if mask.ndim != 2 or mask.shape != (source_size[1], source_size[0]) or not np.isin(mask, [0, 1, 255]).all():
            raise ValueError("Source mask geometry or values invalid")
        if not mask.any() or (mask != 0).all():
            raise ValueError("Source mask must contain foreground and background")
        self.active = {"mask": Image.fromarray((mask != 0).astype('uint8')), "label": label, "calls": 0,
                       "size": source_size, "validate_target": not segmentation_free}
        try:
            yield
            if self.active["calls"] != 2:
                raise RuntimeError("Pinned parser call contract changed")
        finally:
            self.active = None

    def predict(self, image):
        if self.active is None:
            return self.base.predict(image)
        state = self.active
        state["calls"] += 1
        if state["calls"] == 1:
            prediction = self.base.predict(image)
            if state["validate_target"] and (prediction.shape != image.shape[:2] or not np.any(prediction)
                                              or not np.isin(prediction, np.arange(18)).all()):
                raise ValueError("Masked target requires a valid nonempty real human parsing result")
            return prediction
        if state["calls"] != 2:
            raise RuntimeError("Unexpected extra parser call")
        height, width = image.shape[:2]
        # FASHN pre-resizes proportionally before parsing; reject other geometry.
        original_w, original_h = state["size"]
        if abs(width / height - original_w / original_h) > 2 / height:
            raise ValueError("Source aspect ratio changed")
        mask = np.asarray(state["mask"].resize((width, height), Image.Resampling.NEAREST))
        return (mask * state["label"]).astype('uint8')


class SourcePoseAblation:
    """Keep target pose, replace only source pose with the upstream empty pose."""
    def __init__(self, base, empty_pose_factory):
        self.base = base
        self.empty_pose_factory = empty_pose_factory
        self.calls = None

    @contextmanager
    def use(self):
        if self.calls is not None:
            raise RuntimeError("Nested pose ablation")
        self.calls = 0
        try:
            yield
            if self.calls != 2:
                raise RuntimeError("Pinned pose call contract changed")
        finally:
            self.calls = None

    def __call__(self, image):
        if self.calls is None:
            return self.base(image)
        self.calls += 1
        if self.calls == 1:
            return self.base(image)
        if self.calls == 2:
            return self.empty_pose_factory()
        raise RuntimeError("Unexpected extra pose call")
