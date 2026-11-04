from comfy_api.latest import io


class StringList(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="StringList",
            display_name="String List",
            category="utils/text",
            inputs=[
                io.String.Input("text", multiline=True, default=""),
            ],
            outputs=[
                io.String.Output(display_name="string", is_output_list=True),
            ],
        )

    @classmethod
    async def execute(cls, text: str) -> io.NodeOutput:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return io.NodeOutput(lines)
