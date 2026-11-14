from comfy_api.latest import io


class Noop(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        template = io.MatchType.Template("T")
        return io.Schema(
            node_id="Noop",
            display_name="Noop",
            category="utils",
            inputs=[io.MatchType.Input("value", template=template)],
            outputs=[io.MatchType.Output(template=template, display_name="value")],
        )

    @classmethod
    def execute(cls, value) -> io.NodeOutput:
        return io.NodeOutput(value)
