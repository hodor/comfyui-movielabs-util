python name=publish/publish_asset.py
from .shotgrid import shots, artist_logins, ShotGrid
from .config import shotgrid_config, task_names
from .fs import create_task_version

# Add this helper at the top of the file
def sanitize_path(path):
    if path is None:
        return path
    path = path.strip()
    if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
        return path[1:-1]
    return path

import os

class PublishAsset:
    RETURN_TYPES = ()
    FUNCTION = "publish_asset"
    OUTPUT_NODE = True
    CATEGORY = "MovieLabs > Util > Grant8&9"

    @classmethod
    def INPUT_TYPES(cls):
        artist_logins_with_blank = [""] + artist_logins
        return {
            "required": {
                "artist_login": (artist_logins_with_blank,),
                "shot_code": (list(shots.keys()),),
                "task_name": (task_names,),
                "original_asset_file_path": ("STRING", {"default": "", "label": "Original Asset File Path", "tooltip": "Path to the original asset file"}),
            },
            "optional": {
                "proxy_asset_file_path": ("STRING", {"default": "", "label": "Proxy Asset File Path", "tooltip": "Path to the proxy asset file"}),
                "notes": ("STRING", {"default": "", "label": "Notes", "tooltip": "Notes to add to the version in ShotGrid"}),
            },
        }

    def publish_asset(self, **kwargs):
        artist_login = kwargs["artist_login"]
        if artist_login == "":
            raise Exception("Select your artist login")
        sg = ShotGrid(shotgrid_config, artist_login)

        shot_code = kwargs["shot_code"]
        task_name = kwargs["task_name"]

        if shot_code not in shots:
            raise Exception(f"Shot {shot_code} not found")
        
        sg_tasks = sg.get_tasks(shot_code, task_name)

        if len(sg_tasks) == 0:
            raise Exception(f"Task {task_name} not found for shot {shot_code}")

        # Sanitize paths only when the input is received, not at the module level!
        original_asset_file_path = sanitize_path(kwargs["original_asset_file_path"])
        proxy_asset_file_path = sanitize_path(kwargs.get("proxy_asset_file_path"))
        notes = kwargs.get("notes", "")

        # For EXR sequence handling, update logic to allow folder input:
        if os.path.isdir(original_asset_file_path):
            exr_sequence_dir = original_asset_file_path
        else:
            exr_sequence_dir = os.path.dirname(original_asset_file_path)

        # Pass exr_sequence_dir to ensure_exr_sequence if you need it:
        # exr_files = ensure_exr_sequence(exr_sequence_dir)

        shot_id = shots[shot_code]["id"]
        task_id = sg_tasks[0]["id"]

        shotgrid_data = create_task_version(shot_code, task_name, original_asset_file_path, proxy_asset_file_path)
        version_code = sg.get_version_code(shot_code, task_name, shotgrid_data["version_number"])
        shotgrid_fields = {
            "sg_notes": notes,
            "sg_path_to_movie": shotgrid_data["sg_path_to_movie"],
            "sg_path_to_frames": shotgrid_data["sg_path_to_frames"],
        }
        # Add additional publish logic as needed

# Node mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PublishAsset": PublishAsset,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PublishAsset": "Publish Asset (MovieLabs)",
}
