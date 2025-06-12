import os
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from .version import data_model_name, data_model_version
from .shotgrid import sg, shots, tasks

class IdentifierModel(BaseModel):
    scope: str = Field(alias="identifierScope")
    value: str = Field(alias="identifierValue")
    class Config:
        populate_by_name = True

class AssetProvenanceModel(BaseModel):
    # comes from production systems, such as ShotGrid
    shot_id: IdentifierModel = Field(default=None, alias="shotId")
    task_id: IdentifierModel = Field(default=None, alias="taskId")
    artist_id: Optional[IdentifierModel] = Field(default=None, alias="artistId")
    shot: Dict[str, Any] = Field(default=None, alias="shot")
    task: Dict[str, Any] = Field(default=None, alias="task")
    # comes from the user
    notes: str = Field(default=None, alias="notes", description="Notes to add to the version in ShotGrid")
    for_review: bool = Field(default=False, alias="forReview", description="Flag to indicate if this asset is a candidate for review")
    class Config:
        populate_by_name = True


class AssetProvenance:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "for_review": ("BOOLEAN", {"default": False, "label": "Mark as review candidate"}),
                "shot_code": (list(shots.keys()),),
                "task_name": (sg.config["comfyui_task_names"],),
                "notes": ("STRING", {"default": "", "label": "Notes", "tooltip": "Notes to add to the version in ShotGrid"}),
            },
            "optional": {
            },
        }

    RETURN_TYPES = ("PROVENANCE",)
    RETURN_NAMES = ("provenance",)
    FUNCTION = "capture_provenance"
    OUTPUT_NODE = False
    CATEGORY = "MovieLabs > Util > Grant8&9"

    def capture_provenance(self, **kwargs):
        # Parse the shot_name JSON string into an object
        shot_code = kwargs["shot_code"]
        task_name = kwargs["task_name"]

        if shot_code not in shots:
            raise Exception(f"Shot code {shot_code} not found")
        if task_name not in tasks[shot_code]:
            raise Exception(f"Task name {task_name} not found for shot code {shot_code}")

        shot_id = shots[shot_code]["id"]
        task_id = tasks[shot_code][task_name]["id"]

        prov = AssetProvenanceModel(
            artist_id=IdentifierModel(identifierScope="shotgrid", identifierValue=sg.user_login) if sg.user_login else None,
            shot_id=IdentifierModel(identifierScope="shotgrid", identifierValue=str(shot_id)),
            task_id=IdentifierModel(identifierScope="shotgrid", identifierValue=str(task_id)),
            shot=shots[shot_code],
            task=tasks[shot_code][task_name],
            notes=kwargs["notes"],
            for_review=kwargs["for_review"]
        )
        provenance = {
            "model": {
                "modelName": data_model_name,
                "modelVersion": data_model_version
            },
            "data": prov.model_dump(by_alias=True)
        }
        return (provenance,)

NODE_CLASS_MAPPINGS = {
    "AssetProvenance": AssetProvenance
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AssetProvenance": "Asset Provenance"
}