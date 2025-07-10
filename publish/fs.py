import os
import re
import shutil

from .config import filesystem_config

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

def list_exr_files(dir_path):
    return [f for f in sorted(os.listdir(dir_path)) if f.endswith(".exr") or f.endswith(".EXR")]

def get_frame_number_from_exr_file(file_path):
    # get the last bit of the filename before the extension
    base, _ = os.path.splitext(file_path)
    base = base.rstrip("_")
    frame_number = base.split("_")[-1]
    return frame_number


def ensure_exr_sequence(dir_path):
    exr_files = list_exr_files(dir_path)
    if len(exr_files) == 0:
        raise ValueError(f"No exr files found in {dir_path}")
    if len(exr_files) > 0:
        frame_numbers = [get_frame_number_from_exr_file(f) for f in exr_files]
        # ensure all frame numbers are the same length
        if len(set(len(f) for f in frame_numbers)) > 1:
            raise ValueError(f"Frame numbers of exr files are not of the same length in {dir_path}")
        # ensure all frame numbers are consecutive, regardless of starting number
        frame_numbers_int = [int(f) for f in frame_numbers]
        start = frame_numbers_int[0]
        for idx, num in enumerate(frame_numbers_int):
            if num != start + idx:
                raise ValueError(f"Frame numbers of exr files are not consecutive in {dir_path}")
        return {str(int(frame_number) + 1000).zfill(5): os.path.join(dir_path, f) for frame_number, f in zip(frame_numbers, exr_files)}

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
    exr_task = "exr" in filesystem_config["version_convention"][task_name]["image_ext"] if "image_ext" in filesystem_config["version_convention"][task_name] else False
    exr_files = ensure_exr_sequence(os.path.dirname(original_file_path)) if exr_task else None
        
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
    exr_dir = None

    if exr_task:
        exr_dir = version_dir
        for frame_number, file_path in exr_files.items():
            file_name = get_file_name("image", shot_code, task_name, new_version_number, frame_number) + ".exr"
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
        "sg_path_to_frames": exr_dir,
        "mime_type": mime_type_from_file_path(output_file),
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
    