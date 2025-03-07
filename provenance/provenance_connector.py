import copy
import uuid

class ProvenanceConnector:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "provenance": ("PROVENANCE",),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "add_provenance"
    OUTPUT_NODE = False
    CATEGORY = "MovieLabs > Util > Grant8&9"

    def add_provenance(self, images, provenance, unique_id, **kwargs):
        prov = copy.deepcopy(provenance)
        data = prov["data"]
        data["batch_id"] = str(uuid.uuid4())
        extra_pnginfo = kwargs.get("extra_pnginfo", {})
        extra_pnginfo["provenance"] = prov
        extra_pnginfo["workflowNodeId"] = unique_id or None
        return (images, extra_pnginfo)

NODE_CLASS_MAPPINGS = {
    "ProvenanceConnector": ProvenanceConnector
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ProvenanceConnector": "Provenance Connector"
}
