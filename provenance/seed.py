import os
import json

current_directory = os.path.dirname(os.path.abspath(__file__))
shotgrid_seed = json.load(open(os.path.join(current_directory, "shotgrid_seed.json")))
omc_seed = json.load(open(os.path.join(current_directory, "omc_seed.json")))

artist_names = [artist["name"] for artist in shotgrid_seed["artists"]]
shot_names = [shot["name"] for shot in shotgrid_seed["shots"]]
task_names = [task["name"] for task in shotgrid_seed["tasks"]]


creative_work_names = [
    work["title"]["workingTitle"]
    for data in omc_seed.values()  # Iterate over all keys dynamically
    for pathway in data  # Each key contains a list of pathway-like structures
    for work in pathway.get("CreativeWork", [])
]

script_revisions = [
    asset["version"]["name"]
    for data in omc_seed.values()
    for pathway in data
    for asset in pathway.get("Asset", [])
    if asset.get("assetFC", {}).get("functionalType") == "script"
]

character_names = [
    character["characterName"]["fullName"]
    for data in omc_seed.values()
    for pathway in data
    for character in pathway.get("Character", [])
]

scene_numbers = [
    scene["sceneNumber"]
    for data in omc_seed.values()
    for pathway in data
    for scene in pathway.get("NarrativeScene", [])
]

def get_artist_id(artist_name):
    for artist in shotgrid_seed["artists"]:
        if artist["name"] == artist_name:
            return artist["id"]
    return None

def get_shot_id(shot_name):
    for shot in shotgrid_seed["shots"]:
        if shot["name"] == shot_name:
            return shot["id"]
    return None

def get_task_id(task_name):
    for task in shotgrid_seed["tasks"]:
        if task["name"] == task_name:
            return task["id"]
    return None

def get_creative_work_id(creative_work_name):
    for data in omc_seed.values():
        for work in data:
            for creative_work in work.get("CreativeWork", []):
                if creative_work["title"]["workingTitle"] == creative_work_name:
                    return creative_work["identifier"][0]["identifierScope"], creative_work["identifier"][0]["identifierValue"]
    return None, None

def get_script_id(script_name):
    for data in omc_seed.values():
        for work in data:
            for script in work.get("Asset", []):
                if script["version"]["name"] == script_name:
                    return script["identifier"][0]["identifierScope"], script["identifier"][0]["identifierValue"]
    return None, None

def get_character_id(character_name):
    for data in omc_seed.values():
        for work in data:
            for character in work.get("Character", []):
                if character["characterName"]["fullName"] == character_name:
                    return character["identifier"][0]["identifierScope"], character["identifier"][0]["identifierValue"]
    return None, None

def get_scene_id(scene_number):
    for data in omc_seed.values():
        for work in data:
            for scene in work.get("NarrativeScene", []):
                if scene["sceneNumber"] == scene_number:
                    return scene["identifier"][0]["identifierScope"], scene["identifier"][0]["identifierValue"]
    return None, None
