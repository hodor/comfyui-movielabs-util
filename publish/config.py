import os
from pathlib import Path
import json

config_path = os.path.join(Path(__file__).parent.parent, "config.json")
if not os.path.exists(config_path):
    raise Exception("config.json not found")
with open(config_path, "r") as f:
    config = json.load(f)

filesystem_config = config["filesystem"]
shotgrid_config = config["shotgrid"]
task_names = config["task_names"]
