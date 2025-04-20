import copy
import uuid

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

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "filename_prefix")
    FUNCTION = "add_provenance"
    OUTPUT_NODE = False
    CATEGORY = "MovieLabs > Util > Grant8&9"

    def generate_filename_prefix(self, data):
        # Get the mandatory fields
        creative_work_name = data.get("creativeWorkName", "")
        asset_type = data.get("assetFunctionalType", "")
        
        # Try scene-setup-take format if all three exist
        scene = data.get("sceneNumber", "")
        setup = data.get("setup", "")
        take = data.get("take", "")
        
        if scene and setup and take:
            # special case: if setup contains 'master', use scene-take format
            if 'master' in setup.lower():
                return f"{scene}-{take}"
            # otherwise use scene-setup-take format
            return f"{scene}{setup}-{take}"
        
        # Use creative_work-asset_type as base
        prefix = f"{creative_work_name}-{asset_type}"
        # Add scene if it exists
        if scene:
            prefix = f"{prefix}-{scene}"
        prefix = prefix.replace(" ", "_")
        
        return prefix

    def add_provenance(self, images, provenance, unique_id, **kwargs):
        prov = copy.deepcopy(provenance)
        data = prov["data"]
        data["batch_id"] = str(uuid.uuid4())
        extra_pnginfo = kwargs.get("extra_pnginfo", {})
        extra_pnginfo["provenance"] = prov
        extra_pnginfo["provenanceConnectorNodeId"] = unique_id or None
        
        # Generate filename prefix from provenance data
        filename_prefix = self.generate_filename_prefix(data)
        
        return (images, filename_prefix, extra_pnginfo)

NODE_CLASS_MAPPINGS = {
    "ProvenanceConnector": ProvenanceConnector
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ProvenanceConnector": "Provenance Connector"
}
