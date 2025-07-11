import os
from .shotgrid import shots, artist_logins, ShotGrid
from .config import shotgrid_config, task_names
from .fs import create_task_version

def sanitize_path(path):
    if path is None:
        return path
    path = path.strip()
    if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
        return path[1:-1]
    return path

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
                "original_asset_file_path": ("STRING", {"default": "", "label": "Original Asset File Path"}),
            },
            "optional": {
                "proxy_asset_file_path": ("STRING", {"default": "", "label": "Proxy Asset File Path"}),
                "notes": ("STRING", {"default": "", "multiline": True, "label": "Notes"}),
            },
        }

def publish_asset(self, artist_login, shot_code, task_name, original_asset_file_path, proxy_asset_file_path=None, notes=""):
    if not artist_login:
        raise Exception("Select your artist login")
    sg = ShotGrid(shotgrid_config, artist_login)

    if shot_code not in shots:
        raise Exception(f"Shot {shot_code} not found")

    sg_tasks = sg.get_tasks(shot_code, task_name)
    if not sg_tasks:
        raise Exception(f"Task {task_name} not found for shot {shot_code}")

    # Sanitize paths
    clean_original_path = sanitize_path(original_asset_file_path)
    clean_proxy_path = sanitize_path(proxy_asset_file_path)

    final_asset_path = None

    # --- NEW: Logic to find an EXR file in a folder ---
    if os.path.isdir(clean_original_path):
        # If a folder is passed, search inside it for the first .exr file
        print(f"Searching for .exr files in folder: {clean_original_path}")
        for filename in sorted(os.listdir(clean_original_path)):
            if filename.lower().endswith('.exr'):
                final_asset_path = os.path.join(clean_original_path, filename)
                print(f"Found EXR file: {final_asset_path}")
                break # Stop after finding the first one
        if not final_asset_path:
            raise FileNotFoundError(f"No .exr files found in the specified folder: {clean_original_path}")
    else:
        # If a file path is passed directly, use it
        final_asset_path = clean_original_path

    # --- CORE LOGIC ---
    shotgrid_data = create_task_version(shot_code, task_name, final_asset_path, clean_proxy_path)
    version_code = sg.get_version_code(shot_code, task_name, shotgrid_data["version_number"])

    shotgrid_fields = {
        "sg_notes": notes,
        "sg_path_to_movie": shotgrid_data["sg_path_to_movie"],
        "sg_path_to_frames": shotgrid_data["sg_path_to_frames"],
    }

    shot_id = shots[shot_code]["id"]
    task_id = sg_tasks[0]["id"]

    # 1. Add version to ShotGrid
    sg_version = sg.add_version(version_code, shot_id, task_id, shotgrid_fields)

    # 2. Request upload URL
    file_upload_data = sg.request_file_upload(sg_version["id"], "sg_uploaded_movie", shotgrid_fields["sg_path_to_movie"])

    # 3. Upload the file
    sg.upload_file(file_upload_data["links"]["upload"], shotgrid_fields["sg_path_to_movie"], shotgrid_data["mime_type"])

    # 4. Mark upload as complete
    sg.complete_file_upload(file_upload_data)

    return ()

# Node mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PublishAsset": PublishAsset,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PublishAsset": "Publish Asset (MovieLabs)",
}
