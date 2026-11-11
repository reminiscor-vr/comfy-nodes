import torch
import torch.nn.functional as F
from comfy_api.latest import io


def _fill(ref: torch.Tensor, h: int, w: int, value: float) -> torch.Tensor:
    """Solid-color block shaped [B, h, w, C], matching ref's batch/channels/dtype/device."""
    b, c = ref.shape[0], ref.shape[-1]
    t = torch.full((b, h, w, c), value, dtype=ref.dtype, device=ref.device)
    if c == 4:
        t[..., 3] = 1.0  # opaque alpha
    return t


def _to_channels(t: torch.Tensor, c: int) -> torch.Tensor:
    if t.shape[-1] == c:
        return t
    if t.shape[-1] == 3 and c == 4:
        alpha = torch.ones((*t.shape[:-1], 1), dtype=t.dtype, device=t.device)
        return torch.cat([t, alpha], dim=-1)
    return t[..., :c]


class StackImages(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="stack_images",
            display_name="Stack Images",
            category="image/transform",
            description="Join any number of images into one, stacked horizontally or vertically.",
            inputs=[
                io.Autogrow.Input(
                    "images",
                    template=io.Autogrow.TemplatePrefix(
                        io.Image.Input("image"),
                        prefix="image",
                        min=2,
                        max=50,
                    ),
                ),
                io.Combo.Input("direction", options=["horizontal", "vertical"], default="horizontal"),
                io.Combo.Input(
                    "match_size",
                    options=["first", "smallest", "largest", "pad"],
                    default="largest",
                    tooltip=(
                        "How to equalize the cross-axis size (height for horizontal, width for vertical). "
                        "first/smallest/largest: rescale keeping aspect ratio. "
                        "pad: no scaling, pad with the spacing color, centered."
                    ),
                ),
                io.Int.Input("spacing", default=0, min=0, max=1024, step=1),
                io.Float.Input(
                    "spacing_color",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Gray value (0 = black, 1 = white) for spacing and padding.",
                ),
            ],
            outputs=[io.Image.Output()],
        )

    @classmethod
    def execute(cls, images, direction, match_size, spacing, spacing_color) -> io.NodeOutput:
        imgs = [t for t in images.values() if t is not None]
        if not imgs:
            raise ValueError("Join Images: no images connected")
        if len(imgs) == 1:
            return io.NodeOutput(imgs[0])

        horizontal = direction == "horizontal"
        cross = 1 if horizontal else 2  # tensor dim that must match (H for horizontal, W for vertical)

        # unify channels (RGB / RGBA)
        ch = max(t.shape[-1] for t in imgs)
        imgs = [_to_channels(t, ch) for t in imgs]

        # unify batch size (cycle shorter batches)
        batch = max(t.shape[0] for t in imgs)
        imgs = [t if t.shape[0] == batch else t[torch.arange(batch, device=t.device) % t.shape[0]] for t in imgs]

        # target cross-axis size
        sizes = [t.shape[cross] for t in imgs]
        if match_size == "first":
            target = sizes[0]
        elif match_size == "smallest":
            target = min(sizes)
        else:  # largest, pad
            target = max(sizes)

        processed = []
        for t in imgs:
            h, w = t.shape[1], t.shape[2]
            if match_size != "pad" and t.shape[cross] != target:
                if horizontal:
                    new_h, new_w = target, max(1, round(w * target / h))
                else:
                    new_w, new_h = target, max(1, round(h * target / w))
                t = (
                    F.interpolate(t.permute(0, 3, 1, 2), size=(new_h, new_w), mode="bilinear", align_corners=False)
                    .permute(0, 2, 3, 1)
                    .clamp(0.0, 1.0)
                )
            elif match_size == "pad" and t.shape[cross] < target:
                diff = target - t.shape[cross]
                before, after = diff // 2, diff - diff // 2
                h, w = t.shape[1], t.shape[2]
                if horizontal:
                    t = torch.cat([_fill(t, before, w, spacing_color), t, _fill(t, after, w, spacing_color)], dim=1)
                else:
                    t = torch.cat([_fill(t, h, before, spacing_color), t, _fill(t, h, after, spacing_color)], dim=2)
            processed.append(t.contiguous())

        # interleave with spacing strips
        parts = []
        for i, t in enumerate(processed):
            if i > 0 and spacing > 0:
                if horizontal:
                    parts.append(_fill(t, t.shape[1], spacing, spacing_color))
                else:
                    parts.append(_fill(t, spacing, t.shape[2], spacing_color))
            parts.append(t)

        result = torch.cat(parts, dim=2 if horizontal else 1)
        return io.NodeOutput(result)
