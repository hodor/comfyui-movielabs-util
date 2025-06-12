import copy
import json
import uuid
from .shotgrid import sg

class ProvenanceConnector:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
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
        extra_pnginfo = kwargs.get("extra_pnginfo", {})
        extra_pnginfo["provenance"] = prov
        extra_pnginfo["provenanceConnectorNodeId"] = unique_id or None
        extra_pnginfo["batchId"] = str(uuid.uuid4())
        
        return (images, extra_pnginfo)

NODE_CLASS_MAPPINGS = {
    "ProvenanceConnector": ProvenanceConnector
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ProvenanceConnector": "Provenance Connector"
}
