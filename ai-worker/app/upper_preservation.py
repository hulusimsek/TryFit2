"""Optional pixel-space flow constraint for the second outfit stage.

The protected interior follows the same noise-to-image trajectory as the
sampler. This changes inference, rather than compositing the finished output.
Garment edges remain free for the new waistband and silhouette to meet.
"""
import cv2
import numpy as np


def preservation_alpha(labels, edge_pixels=6, *, preserve_feet=False):
    labels = np.asarray(labels)
    if labels.ndim != 2 or not np.isin(labels, np.arange(18)).all():
        raise ValueError("Invalid target parsing for upper preservation")
    if not np.any(labels == 3):
        raise ValueError("No upper garment to preserve")
    # The feet option is separate: it changes possible trouser/foot occlusion.
    # Torso skin (16) belongs to the unchanged upper body too. Without it a
    # bottom swap can fill a visible midriff with a new, higher waistband.
    regions = [1, 2, 3, 12, 13, 16] + ([15] if preserve_feet else [])
    if preserve_feet and not np.any(labels == 15):
        raise ValueError("No feet to preserve")
    protected = np.isin(labels, regions).astype(np.uint8)
    distance = cv2.distanceTransform(protected, cv2.DIST_L2, 5)
    alpha = np.clip((distance - 1) / max(1, edge_pixels), 0, 1).astype(np.float32)
    if preserve_feet:
        # Feet alone can leave generated cloth hanging around the protected toes.
        # Keep the surrounding floor too, with a smooth transition at ankle level.
        # Never freeze the reference lower garment or bare legs into the result.
        start = np.where(labels == 15)[0].min()
        ramp = np.clip((np.arange(labels.shape[0]) - start) / max(1, 2 * edge_pixels), 0, 1)
        floor_and_feet = np.isin(labels, [0, 15])
        alpha = np.maximum(alpha, ramp[:, None] * floor_and_feet).astype(np.float32)
    return alpha


class UpperPreservingPipelineMixin:
    def __call__(self, *, preserve_upper=False, preserve_feet=False, **kwargs):
        if preserve_feet and not preserve_upper:
            raise ValueError("Feet preservation requires the reference constraint")
        if not preserve_upper:
            return super().__call__(**kwargs)
        if kwargs.get("category") != "bottoms":
            raise ValueError("Upper preservation requires a lower stage")
        if getattr(self, "_upper_constraint", None) is not None:
            raise RuntimeError("Nested upper preservation")
        from fashn_vton.preprocessing import ResizePad

        person = self.pre_resize(kwargs["person_image"], allow_upsampling=False)
        pixels = np.asarray(person)
        # Do not consume the source-mask wrapper's two-call target/source contract.
        parser = getattr(self.hp_model, "base", self.hp_model)
        labels = parser.predict(pixels)
        if labels.shape != pixels.shape[:2]:
            raise ValueError("Target parsing geometry mismatch")
        alpha = preservation_alpha(labels, edge_pixels=max(2, round(person.height * 6 / 864)),
                                   preserve_feet=preserve_feet)
        h, w = self.tryon_model.input_shape
        # Separate transforms avoid overwriting upstream unpadding state.
        transform = ResizePad((w, h), backend="opencv")
        reference = transform(pixels)
        alpha = transform(alpha, interpolation=cv2.INTER_LINEAR)
        self._upper_constraint = reference, alpha
        try:
            return super().__call__(**kwargs)
        finally:
            self._upper_constraint = None

    def _sample(self, **kwargs):
        constraint = getattr(self, "_upper_constraint", None)
        if constraint is None:
            return super()._sample(**kwargs)
        import torch
        from fashn_vton.utils import get_rf_schedule, tensor_to_pil

        ca = kwargs["ca_images"]
        reference, alpha = constraint
        reference = torch.as_tensor(reference.copy(), device=ca.device).permute(2, 0, 1)
        reference = (reference.float() / 127.5 - 1).to(ca.dtype).unsqueeze(0)
        alpha = torch.as_tensor(alpha.copy(), device=ca.device, dtype=ca.dtype)[None, None]
        count = kwargs.get("num_timesteps", 30)
        schedule = get_rf_schedule(num_steps=count, mu=kwargs.get("time_shift_mu", 1.5))
        noise = torch.randn_like(ca)
        images = noise.clone()
        inputs = {key: kwargs[key] for key in (
            "ca_images", "garment_images", "person_poses", "garment_poses", "garment_categories")}
        for index, (current, following) in enumerate(zip(schedule[:-1], schedule[1:])):
            time = torch.full((ca.shape[0],), current, device=ca.device, dtype=ca.dtype)
            prediction = self.tryon_model.forward_for_cfg(images, time, **inputs)
            conditional, unconditional = prediction["v_c"], prediction["v_u"]
            skip = kwargs.get("skip_cfg_last_n_steps", 1)
            velocity = (conditional if skip > 0 and index >= count - skip else
                        unconditional + kwargs.get("guidance_scale", 1.5) * (conditional - unconditional))
            images = images + (following - current) * velocity
            known = (1 - following) * noise + following * reference
            images = images * (1 - alpha) + known * alpha
        images = images.float().clamp_(-1, 1)
        return [tensor_to_pil(image, unnormalize=True) for image in images]
