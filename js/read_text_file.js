import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "reminiscorp.ReadTextFile.upload",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "ReadTextFile") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);

            const fileWidget = this.widgets.find((w) => w.name === "file");

            const input = document.createElement("input");
            input.type = "file";
            input.accept = ".txt,.md,.json,.csv,.yaml,.yml,.log,text/*";
            input.style.display = "none";
            document.body.appendChild(input);
            this._uploadInput = input;

            input.onchange = async () => {
                const file = input.files?.[0];
                if (!file) return;

                try {
                    const body = new FormData();
                    body.append("image", file); // endpoint field name; works for any file
                    body.append("type", "input");
                    body.append("overwrite", "true");

                    const resp = await api.fetchApi("/upload/image", {
                        method: "POST",
                        body,
                    });
                    if (resp.status !== 200) {
                        alert(`Upload failed: ${resp.status} ${resp.statusText}`);
                        return;
                    }

                    const data = await resp.json();
                    const name = data.subfolder ? `${data.subfolder}/${data.name}` : data.name;

                    if (!fileWidget.options.values.includes(name)) {
                        fileWidget.options.values.push(name);
                    }
                    fileWidget.value = name;
                    fileWidget.callback?.(name);
                    app.graph.setDirtyCanvas(true);
                } catch (err) {
                    alert(`Upload failed: ${err}`);
                } finally {
                    input.value = "";
                }
            };

            this.addWidget("button", "Upload text file", null, () => input.click());

            return result;
        };

        const onRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            this._uploadInput?.remove();
            return onRemoved?.apply(this, arguments);
        };
    },
});