import os
import re
import shutil

from .config import filesystem_config

# If you call ensure_image_sequence from this file, the logic already expects a directory.
# No changes needed here, but make sure your publish_asset.py uses the updated image_sequence_dir logic as above.

# Optionally, you can add the sanitize_path function here if paths are used directly.
def sanitize_path(path):
    if path is None:
        return path
    path = path.strip()
    if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
        return path[1:-1]
    return path

def get_output_dir(shot_code):
    output_dir = filesystem_config["output_dir"]
    seq_code = shot_code[:-4]
    output_dir = [dir.format(SEQ_CODE=seq_code, SHOT_CODE=shot_code) for dir in output_dir]
    output_dir_path = os.path.join(*output_dir)
    os.makedirs(output_dir_path, exist_ok=True)
    return output_dir_path

def get_task_dir(output_dir, task_name):
    task_dir = filesystem_config["version_convention"][task_name]["parent_dir"]
    task_dir_path = os.path.join(output_dir, *task_dir)
    os.makedirs(task_dir_path, exist_ok=True)
    return task_dir_path

def format_string_to_version_regex(format_string):
    # Escape regex special characters except for the {VERSION_NUMBER} placeholder
    regex = re.escape(format_string)
    # Replace the escaped placeholder with a regex group to capture the version number
    regex = regex.replace(r'\{VERSION_NUMBER\}', r'(\d{3})')
    # Anchor the regex to match the full string
    regex = f'^{regex}$'
    return re.compile(regex)


def get_next_version(task_name, task_dir):
    version_numbers = []
    version_dir = filesystem_config["version_convention"][task_name]["version_dir"]
    if version_dir:
        version_regex = format_string_to_version_regex(version_dir)
        for f in os.listdir(task_dir):
            if os.path.isdir(os.path.join(task_dir, f)):
                match = version_regex.match(f)
                if match:
                    version_numbers.append(int(match.group(1)))
    else:
        version_pattern = re.compile(r"_v(\d{3})$")
        for f in os.listdir(task_dir):
            if os.path.isfile(os.path.join(task_dir, f)):
                base, _ = os.path.splitext(f)
                match = version_pattern.search(base)
                if match:
                    version_numbers.append(int(match.group(1)))
    if len(version_numbers) == 0:
        return "001"
    else:
        return str(max(version_numbers) + 1).zfill(3)

def get_version_dir(task_name, task_dir, version_number):
    version_dir = filesystem_config["version_convention"][task_name]["version_dir"]
    if version_dir is None:
        return task_dir
    else:
        version_dir = version_dir.format(VERSION_NUMBER=version_number)
        version_dir_path = os.path.join(task_dir, version_dir)
        os.makedirs(version_dir_path, exist_ok=True)
        return version_dir_path
    
def get_file_name(kind, shot_code, task_name, version_number, frame_number=None):
    file_name = filesystem_config["version_convention"][task_name][kind]
    return file_name.format(SHOT_CODE=shot_code, VERSION_NUMBER=version_number, FRAME_NUMBER=frame_number)

def match_extension(task_name, is_original, file_path):
    kind = "original" if is_original else "proxy"
    type = filesystem_config["version_convention"][task_name][kind]
    print({
        "task_name": task_name,
        "kind": kind,
        "type": type,
        "file_path": file_path,
    })
    if type == "image":
        supported_extensions = filesystem_config["version_convention"][task_name]["image_ext"]
    elif type == "file":
        supported_extensions = filesystem_config["version_convention"][task_name]["file_ext"]
    else:
        supported_extensions = filesystem_config["version_convention"][task_name]["movie_ext"]
    _, ext = os.path.splitext(file_path)
    ext = ext[1:].lower()
    if ext not in supported_extensions:
        raise ValueError(f"Unsupported {kind} file extension: {ext} for {task_name} task. Must be {', '.join(supported_extensions)}")
    return True

def list_image_sequence_files(dir_path):
    """List all EXR and PNG files in a directory"""
    return [f for f in sorted(os.listdir(dir_path)) 
            if f.lower().endswith((".exr", ".png"))]

def get_frame_number_from_image_file(file_path):
    """Get the frame number from an image file (EXR or PNG)"""
    # get the last bit of the filename before the extension
    base, _ = os.path.splitext(file_path)
    base = base.rstrip("_")
    frame_number = base.split("_")[-1]
    return frame_number

def get_file_extension_from_sequence(dir_path):
    """Determine the file extension used in the sequence (EXR or PNG)"""
    files = list_image_sequence_files(dir_path)
    if not files:
        return None
    
    # Get the extension of the first file
    _, ext = os.path.splitext(files[0])
    ext = ext.lower()
    
    # Verify all files have the same extension
    for f in files:
        _, f_ext = os.path.splitext(f)
        if f_ext.lower() != ext:
            raise ValueError(f"Mixed file extensions found in {dir_path}. All files must be either EXR or PNG.")
    
    return ext

def ensure_image_sequence(dir_path):
    """Ensure a valid image sequence exists (EXR or PNG files)"""
    image_files = list_image_sequence_files(dir_path)
    if len(image_files) == 0:
        raise ValueError(f"No EXR or PNG files found in {dir_path}")

    # Verify consistent extension
    file_ext = get_file_extension_from_sequence(dir_path)
    
    # Filter files to only include those with the detected extension
    image_files = [f for f in image_files if f.lower().endswith(file_ext)]

    frame_numbers = [get_frame_number_from_image_file(f) for f in image_files]
    
    # Ensure all frame numbers are the same length
    if len(set(len(f) for f in frame_numbers)) > 1:
        raise ValueError(f"Frame numbers of image files are not of the same length in {dir_path}")

    # Ensure all frame numbers are consecutive
    frame_numbers_int = [int(f) for f in frame_numbers]
    start = frame_numbers_int[0]
    for idx, num in enumerate(frame_numbers_int):
        if num != start + idx:
            raise ValueError(f"Frame numbers of image files are not consecutive in {dir_path}")
            
    # --- NEW: Logic to enforce start frame of 1001 ---
    frame_offset = 0 # Default to no offset
    original_start_frame = frame_numbers_int[0]

    # Check if the start frame is outside the exception range (101-999)
    if not (100 < original_start_frame < 1000):
        # If it is, calculate the offset needed to move the start to 1001
        frame_offset = 1001 - original_start_frame
        
    # --- Apply the offset to generate the final frame dictionary ---
    output_frames = {}
    for i, original_frame in enumerate(frame_numbers_int):
        # Calculate the new frame number
        new_frame = original_frame + frame_offset
        # Create the new dictionary entry with the corrected frame number
        output_frames[str(new_frame).zfill(5)] = os.path.join(dir_path, image_files[i])
        
    return output_frames, file_ext

def mime_type_from_file_path(file_path):
    _, ext = os.path.splitext(file_path)
    ext = ext[1:].lower()
    if ext == "mp4":
        return "video/mp4"
    elif ext == "mov":
        return "video/quicktime"
    elif ext == "png":
        return "image/png"
    elif ext == "jpg":
        return "image/jpeg"
    elif ext == "jpeg":
        return "image/jpeg"
    elif ext == "tiff":
        return "image/tiff"
    else:
        return "application/octet-stream"
    
def create_task_version(shot_code, task_name, original_file_path, proxy_file_path=None):
    if original_file_path is None or not os.path.exists(original_file_path):
        raise FileNotFoundError(f"Original {original_file_path} not found")
    match_extension(task_name, True, original_file_path)
    
    # Check if this task expects image sequences (EXR or PNG)
    image_sequence_task = False
    if "image_ext" in filesystem_config["version_convention"][task_name]:
        supported_exts = filesystem_config["version_convention"][task_name]["image_ext"]
        # Check if either exr or png is in the supported extensions
        image_sequence_task = any(ext in supported_exts for ext in ["exr", "png"])
    
    image_files = None
    detected_ext = None
    if image_sequence_task:
        image_files, detected_ext = ensure_image_sequence(os.path.dirname(original_file_path))
        
    proxy_necessary = filesystem_config["version_convention"][task_name]["proxy"] is not None
    if proxy_necessary and (proxy_file_path is None or not os.path.exists(proxy_file_path)):
        raise FileNotFoundError(f"Proxy {proxy_file_path} not found")
    if proxy_necessary:
        match_extension(task_name, False, proxy_file_path)

    output_dir = get_output_dir(shot_code)
    task_dir = get_task_dir(output_dir, task_name)
    new_version_number = get_next_version(task_name, task_dir)
    version_dir = get_version_dir(task_name, task_dir, new_version_number)

    output_file = None
    image_dir = None

    if image_sequence_task:
        image_dir = version_dir
        for frame_number, file_path in image_files.items():
            # Use the detected extension for the output file
            file_name = get_file_name("image", shot_code, task_name, new_version_number, frame_number) + detected_ext
            shutil.copy(file_path, os.path.join(version_dir, file_name))
    else:
        type = filesystem_config["version_convention"][task_name]["original"]
        file_name = get_file_name(type, shot_code, task_name, new_version_number) + os.path.splitext(original_file_path)[1].lower()
        output_file = os.path.join(version_dir, file_name)
        shutil.copy(original_file_path, output_file)
    
    if proxy_necessary:
        type = filesystem_config["version_convention"][task_name]["proxy"]
        file_name = get_file_name(type, shot_code, task_name, new_version_number) + os.path.splitext(proxy_file_path)[1].lower()
        output_file = os.path.join(version_dir, file_name)
        shutil.copy(proxy_file_path, output_file)
    
    shotgrid_data = {
        "version_number": new_version_number,
        "shot_code": shot_code,
        "task_name": task_name,
        "sg_path_to_movie": output_file,
        "sg_path_to_frames": image_dir,
        "mime_type": mime_type_from_file_path(output_file) if output_file else None,
    }

    return shotgrid_data

def create_blender_version(shot_code, original_file_path):
    if original_file_path is None or not os.path.exists(original_file_path):
        raise FileNotFoundError(f"Original file {original_file_path} is not found")
    _, ext = os.path.splitext(original_file_path)
    ext = ext[1:].lower()
    if ext not in filesystem_config["version_convention"]["Blender Files"]["file_ext"]:
        raise ValueError(f"Original {original_file_path} not a Blender file. File extension must be {', '.join(filesystem_config['version_convention']['Blender Files']['file_ext'])}")
    
    output_dir = get_output_dir(shot_code)
    task_dir = os.path.join(output_dir, os.path.join(*filesystem_config["version_convention"]["Blender Files"]["parent_dir"]))
    new_version_number = get_next_version("Blender Files", task_dir)
    version_dir = get_version_dir("Blender Files", task_dir, new_version_number)
    os.makedirs(version_dir, exist_ok=True)

    file_name = get_file_name("file", shot_code, "Blender Files", new_version_number) + os.path.splitext(original_file_path)[1].lower()
    output_file = os.path.join(version_dir, file_name)
    shutil.copy(original_file_path, output_file)
