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

# When processing inputs (for example, inside whatever method is handling the node execution)
original_asset_file_path = sanitize_path(original_asset_file_path)
proxy_asset_file_path = sanitize_path(proxy_asset_file_path)

# For EXR sequence handling, update logic to allow folder input:
import os

def get_first_exr_from_folder(folder_path):
    exr_files = [f for f in sorted(os.listdir(folder_path)) if f.lower().endswith('.exr')]
    if not exr_files:
        raise FileNotFoundError(f"No EXR files found in folder: {folder_path}")
    return os.path.join(folder_path, exr_files[0])

# Usage in node:
if os.path.isdir(original_asset_file_path):
    # User gave a folder
    first_exr_path = get_first_exr_from_folder(original_asset_file_path)
    # You can use first_exr_path for further EXR sequence logic
    exr_sequence_dir = original_asset_file_path
else:
    # User gave a file
    first_exr_path = original_asset_file_path
    exr_sequence_dir = os.path.dirname(original_asset_file_path)


# Instead of always using os.path.dirname(original_asset_file_path)
if os.path.isdir(original_asset_file_path):
    exr_sequence_dir = original_asset_file_path
else:
    exr_sequence_dir = os.path.dirname(original_asset_file_path)

# Pass exr_sequence_dir to ensure_exr_sequence
exr_files = ensure_exr_sequence(exr_sequence_dir)


class PublishAsset:
    def __init__(self):
        pass
    
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

    RETURN_TYPES = ()
    FUNCTION = "publish_asset"
    OUTPUT_NODE = True
    CATEGORY = "MovieLabs > Util > Grant8&9"

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

        shot_id = shots[shot_code]["id"]
        task_id = sg_tasks[0]["id"]
        original_asset_file_path = kwargs["original_asset_file_path"]
        proxy_asset_file_path = kwargs["proxy_asset_file_path"] if "proxy_asset_file_path" in kwargs else None
        notes = kwargs["notes"] if "notes" in kwargs else ""

        shotgrid_data = create_task_version(shot_code, task_name, original_asset_file_path, proxy_asset_file_path)
        version_code = sg.get_version_code(shot_code, task_name, shotgrid_data["version_number"])
        shotgrid_fields = {
            "sg_notes": notes,
            "sg_path_to_movie": shotgrid_data["sg_path_to_movie"],
            "sg_path_to_frames": shotgrid_data["sg_path_to_frames"],
        }
        sg_version =sg.add_version(version_code, shot_id, task_id, shotgrid_fields)
        file_upload_data = sg.request_file_upload(sg_version["id"], "sg_uploaded_movie", shotgrid_fields["sg_path_to_movie"])
        sg.upload_file(file_upload_data["links"]["upload"], shotgrid_fields["sg_path_to_movie"], shotgrid_data["mime_type"])
        sg.complete_file_upload(file_upload_data)
        return ()

NODE_CLASS_MAPPINGS = {
    "PublishAsset": PublishAsset
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PublishAsset": "Publish Asset"
}
