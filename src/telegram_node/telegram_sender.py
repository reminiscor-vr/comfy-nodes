import asyncio
import html
import io as pyio

import httpx
import numpy as np
from comfy_api.latest import Types, io
from PIL import Image

CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


class TelegramSender(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        autogrow_template = io.Autogrow.TemplatePrefix(
            input=io.Image.Input("image"),  # template for each input
            prefix="image",  # prefix for generated input names
            min=0,  # minimum number of inputs shown
            max=10,  # maximum number of inputs allowed
        )

        video_template = io.Autogrow.TemplatePrefix(
            input=io.Video.Input("video"),
            prefix="video",
            min=0,
            max=5,
        )

        return io.Schema(
            node_id="tg_send",
            display_name="Telegram Sender",
            category="Reminiscorp",
            inputs=[
                io.String.Input("msg", default="", multiline=True),
                io.Autogrow.Input("images", template=autogrow_template, optional=True),
                io.Autogrow.Input("videos", template=video_template, optional=True),
                io.String.Input("token"),
                io.String.Input("chat_id"),
            ],
            outputs=[io.String.Output("Ok")],
        )

    @classmethod
    async def execute(
        cls,
        msg: io.String.Type,
        token: io.String.Type,
        chat_id: io.String.Type,
        images: io.Autogrow.Type = None,
        videos: io.Autogrow.Type = None,
    ) -> io.NodeOutput:
        url = f"https://api.telegram.org/bot{token}/"

        frames = []
        for tensor in (images or {}).values():
            if tensor is None:  # unconnected / empty branch
                continue
            if tensor.ndim == 3:
                tensor = tensor.unsqueeze(0)
            frames.extend(tensor)

        clips = [v for v in (videos or {}).values() if v is not None]

        has_message = bool(msg)
        if not frames and not clips and not has_message:
            return io.NodeOutput("Nothing")

        async with httpx.AsyncClient(timeout=300) as client:
            if not frames and not clips:
                response = await client.post(url + "sendMessage", json={"chat_id": chat_id, "text": msg})
                await _check(response)
                return io.NodeOutput("Ok")

            if msg and len(msg) <= CAPTION_LIMIT:
                caption, msg_to_send = msg, ""
            else:
                caption, msg_to_send = "", msg

            sent = 0  # caption goes on the very first media item

            for i, data in enumerate(frames):
                png = await asyncio.to_thread(tensor_to_png_bytes, data)
                r = await client.post(
                    url + "sendPhoto",
                    data={"chat_id": chat_id, "caption": caption if sent == 0 else ""},
                    files={"photo": (f"image_{i}.png", png, "image/png")},
                )
                await _check(r)
                sent += 1

            for i, clip in enumerate(clips):
                mp4, width, height, duration = await asyncio.to_thread(video_to_mp4, clip)
                r = await client.post(
                    url + "sendVideo",
                    data={
                        "chat_id": chat_id,
                        "caption": caption if sent == 0 else "",
                        "width": width,
                        "height": height,
                        "duration": duration,
                        "supports_streaming": "true",
                    },
                    files={"video": (f"video_{i}.mp4", mp4, "video/mp4")},
                )
                await _check(r)
                sent += 1

            for chunk in split_text(msg_to_send):
                r = await client.post(
                    url + "sendMessage",
                    json={"chat_id": chat_id, "text": expandable(chunk), "parse_mode": "HTML"},
                )
                await _check(r)

        return io.NodeOutput("Sent")


def video_to_mp4(video) -> tuple[bytes, int, int, int]:
    """Encode a ComfyUI VIDEO to H.264 MP4 in memory (Telegram's preferred format)."""
    width, height = video.get_dimensions()
    duration = int(round(video.get_duration()))
    buf = pyio.BytesIO()
    video.save_to(buf, format=Types.VideoContainer.MP4, codec=Types.VideoCodec.H264)
    return buf.getvalue(), width, height, duration


def tensor_to_png_bytes(img) -> bytes:
    # img: [H, W, C] float tensor in 0..1
    arr = (img.detach().cpu().numpy().clip(0, 1) * 255).round().astype(np.uint8)
    if arr.shape[-1] == 1:  # grayscale
        arr = arr[..., 0]
    buf = pyio.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def split_text(text: str, limit: int = TEXT_LIMIT) -> list[str]:
    chunks = []
    while len(text) > limit:
        # prefer breaking at a newline, then a space
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            cut = text.rfind(" ", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks


async def _check(response: httpx.Response):
    if response.is_error:
        raise RuntimeError(f"Telegram {response.status_code}: {response.text}")


def spoiler(text: str) -> str:
    return f"<tg-spoiler>{html.escape(text)}</tg-spoiler>"


def expandable(text: str) -> str:
    return f"<blockquote expandable>{html.escape(text)}</blockquote>"
