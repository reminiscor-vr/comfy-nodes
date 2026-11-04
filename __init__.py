from comfy_api.latest import ComfyExtension, io
from typing_extensions import override

from .src.telegram_node import ReadTextFile, SplitText, StringList, TelegramSender

WEB_DIRECTORY = "./js"


class Reminiscorp(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            TelegramSender,
            StringList,
            ReadTextFile,
            SplitText,
        ]


async def comfy_entrypoint() -> ComfyExtension:
    return Reminiscorp()


__all__ = ["comfy_entrypoint", "WEB_DIRECTORY"]
