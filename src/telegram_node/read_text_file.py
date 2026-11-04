import os

import folder_paths
from comfy_api.latest import io

TEXT_EXTS = {".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".log"}


def list_text_files() -> list[str]:
    root = folder_paths.get_input_directory()
    files = []
    for dirpath, _, names in os.walk(root):
        for name in names:
            if os.path.splitext(name)[1].lower() in TEXT_EXTS:
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                files.append(rel.replace("\\", "/"))
    return sorted(files)


def resolve(file: str) -> str | None:
    """Resolve a name inside the input dir; None if it escapes or is missing."""
    root = os.path.realpath(folder_paths.get_input_directory())
    path = os.path.realpath(os.path.join(root, file))
    if os.path.commonpath([root, path]) != root or not os.path.isfile(path):
        return None
    return path


class ReadTextFile(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReadTextFile",
            display_name="Read Text File",
            category="utils/text",
            description="Reads a text file from the input directory. Has an upload button.",
            inputs=[
                io.Combo.Input("file", options=list_text_files()),
                io.String.Input("encoding", default="utf-8", multiline=False),
            ],
            outputs=[io.String.Output(display_name="text")],
        )

    @classmethod
    def validate_inputs(cls, file: str):
        # Needed so freshly uploaded files pass validation even if the
        # cached combo options don't contain them yet.
        if resolve(file) is None:
            return f"file not found: {file}"
        return True

    @classmethod
    def fingerprint_inputs(cls, file: str, encoding: str):
        path = resolve(file)
        return os.path.getmtime(path) if path else float("nan")

    @classmethod
    def execute(cls, file: str, encoding: str) -> io.NodeOutput:
        with open(resolve(file), "r", encoding=encoding) as f:
            return io.NodeOutput(f.read())
