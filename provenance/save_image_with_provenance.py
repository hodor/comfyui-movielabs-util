import sys
import os
import json
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

import folder_paths
from comfy.cli_args import args
from .shotgrid import sg

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

class SaveImageWithProvenance:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "filename_prefix": ("STRING", {"default": "ComfyUI", "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes."}),
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO", "unique_id": "UNIQUE_ID"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"

    OUTPUT_NODE = True

    CATEGORY = "MovieLabs > Util > Grant8&9"
    DESCRIPTION = "Saves the input images to your ComfyUI output directory."

    def save_images(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None, unique_id=None):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        results = list()
        for (batch_number, image) in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if unique_id is not None:
                    metadata.add_text("SaveImageNodeId", unique_id)
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.png"
            img.save(os.path.join(full_output_folder, file), pnginfo=metadata, compress_level=self.compress_level)
            if extra_pnginfo is not None and "provenance" in extra_pnginfo and "data" in extra_pnginfo["provenance"] and "forReview" in extra_pnginfo["provenance"]["data"]:
                for_review = extra_pnginfo["provenance"]["data"]["forReview"]
                if for_review:
                    try:
                        shot_code = extra_pnginfo["provenance"]["data"]["shot"]["attributes"]["code"]
                        shot_id = extra_pnginfo["provenance"]["data"]["shotId"]["identifierValue"]
                        task_id = extra_pnginfo["provenance"]["data"]["taskId"]["identifierValue"]
                        extra_metadata = {
                            "saveImageNodeId": unique_id,
                            "provenanceNodeId": extra_pnginfo["provenanceConnectorNodeId"],
                            "batchId": extra_pnginfo["batchId"],
                        }
                        fields = {
                            "sg_tool": "ComfyUI",
                            "sg_comfyui_prompt": json.dumps(prompt),
                            "sg_comfyui_workflow": json.dumps(extra_pnginfo["workflow"]),
                            "sg_extra_metadata": json.dumps(extra_metadata),
                            "sg_notes": extra_pnginfo["provenance"]["data"]["notes"],
                        }
                        version_code = sg.get_version_code(shot_code)
                        sg.add_version(version_code, int(shot_id), int(task_id), fields)
                    except Exception as e:
                        raise e
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1

        return { "ui": { "images": results } }
        
NODE_CLASS_MAPPINGS = {
    "SaveImageWithProvenance": SaveImageWithProvenance
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithProvenance": "Save Image With Provenance"
}