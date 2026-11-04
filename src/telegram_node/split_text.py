from comfy_api.latest import io


class SplitText(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="SplitText",
            display_name="Split Text",
            category="utils/text",
            description="Splits multiline text by a separator into a list of strings.",
            inputs=[
                io.String.Input("text", default="", multiline=True),
                io.String.Input("separator", default="\\n", multiline=False),
                io.Boolean.Input("strip", default=True),
                io.Boolean.Input("skip_empty", default=True),
                io.Boolean.Input("regex", default=False),
            ],
            outputs=[
                io.String.Output(display_name="items", is_output_list=True),
                io.Int.Output(display_name="count"),
            ],
        )

    @classmethod
    def execute(cls, text: str, separator: str, strip: bool, skip_empty: bool, regex: bool) -> io.NodeOutput:
        import re

        # allow typing escapes like \n, \t in the single-line separator field
        sep = separator.encode("utf-8").decode("unicode_escape") if not regex else separator

        if sep == "":
            parts = [text]
        elif regex:
            parts = re.split(sep, text)
        else:
            parts = text.split(sep)

        if strip:
            parts = [p.strip() for p in parts]
        if skip_empty:
            parts = [p for p in parts if p]

        return io.NodeOutput(parts, len(parts))
