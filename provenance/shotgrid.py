import getpass
import os
from pathlib import Path
import re
import threading
import requests
import json

def get_next_version_number(version_code):
    possible_version_number = version_code.split("_")[-1]
    if possible_version_number.startswith("v"):
        possible_version_number = possible_version_number[1:]
    if len(possible_version_number) == 3 and possible_version_number.isdigit():
        print("possible_version_number", possible_version_number)
        # Convert to integer, add 1, and format back to 3 digits
        next_version = int(possible_version_number) + 1
        print("next_version", next_version)
        if next_version > 999:
            return "999"
        return f"{next_version:03d}"
    else:
        return "001"

def get_user_login():
    # Method 1: get artist id from system username - works on macOS, Linux, and Windows
    user_login = None
    try:
        user_login = getpass.getuser()
    except Exception:
        pass
    
    # Method 2: Check environment variables
    if not user_login:
        for env_var in ['USER', 'LOGNAME', 'USERNAME']:
            user_login = os.environ.get(env_var)
            if user_login:
                break
    return user_login

def authenticate_with_client_credentials(client, config, user_login):
    response = client.post(
        f"{config['server_url']}/api/v1.1/auth/access_token",
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "grant_type": "client_credentials",
            "scope": f"sudo_as_login:{user_login}" if user_login else None
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
    )
    return response.json()

def refresh_tokens(client, config, tokens):
    response = client.post(
        f"{config['server_url']}/api/v1.1/auth/access_token",
        data={"refresh_token": tokens["refresh_token"], "grant_type": "refresh_token"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    )
    return response.json()

def format_to_regex(pattern):
    # Replace {PLACEHOLDER} with .* to match any characters
    regex_pattern = re.sub(r'\{[^}]+\}', '.*', pattern)
    # Escape any special regex characters that might be in the pattern
    regex_pattern = re.escape(regex_pattern)
    # Replace the escaped .* with actual .* for wildcard matching
    regex_pattern = regex_pattern.replace('\\.\\*', '.*')
    return re.compile(regex_pattern)

class ShotGrid:
    def __init__(self, config):
        self.config = config
        self.version_convention_regex = format_to_regex(self.config["version_convention"])
        self.client = requests.Session()
        self._refresh_timer = None
        self.user_login = get_user_login()
        self._initial_auth()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def _initial_auth(self):
        resp_json = authenticate_with_client_credentials(self.client, self.config, self.user_login)
        if "access_token" not in resp_json:
            print("Could not authenticate using current user with ShotGrid. Trying with admin credentials.")
            resp_json = authenticate_with_client_credentials(self.client, self.config, None)
        
        if "access_token" in resp_json:
            self.tokens = resp_json
            print(self.tokens)
            # Set up refresh timer
            if self._refresh_timer:
                self._refresh_timer.cancel()
            
            self._refresh_timer = threading.Timer(
                self.tokens["expires_in"] - 30,
                self._refresh_tokens
            )
            self._refresh_timer.daemon = True
            self._refresh_timer.start()
        else:
            raise Exception("Could not authenticate with ShotGrid")

    def _refresh_tokens(self):
        # Refresh using refresh_token
        resp_json = refresh_tokens(self.client, self.config, self.tokens)
        self.tokens = resp_json
        
        # Set up next refresh
        if self._refresh_timer:
            self._refresh_timer.cancel()
        
        self._refresh_timer = threading.Timer(
            self.tokens["expires_in"] - 30,
            self._refresh_tokens
        )
        self._refresh_timer.daemon = True
        self._refresh_timer.start()

    def cleanup(self):
        if self._refresh_timer:
            self._refresh_timer.cancel()
            self._refresh_timer = None

    def get_shots(self):
        headers = {"Authorization": f"Bearer {self.tokens['access_token']}", "Accept": "application/json"}
        params = {"filter[project.Project.id]": self.config["project_id"], "fields": "id,code,project,content"}
        response = self.client.get(f"{self.config['server_url']}/api/v1.1/entity/Shot", headers=headers, params=params)
        sg_shots = response.json()
        if "errors" in sg_shots:
            raise Exception("Error getting shots from ShotGrid")
        if "data" in sg_shots and len(sg_shots["data"]) > 0:
            return [shot for shot in sg_shots["data"] if "attributes" in shot and "code" in shot["attributes"]]
        else:
            return []
    
    def get_shot(self, shot_code):
        headers = {"Authorization": f"Bearer {self.tokens['access_token']}", "Accept": "application/json"}
        params = {"filter[project.Project.id]": self.config["project_id"], "filter[code]": shot_code, "fields": "id,code,project,content"}
        response = self.client.get(f"{self.config['server_url']}/api/v1.1/entity/Shot", headers=headers, params=params)
        sg_shot = response.json()
        if "errors" in sg_shot:
            raise Exception("Error getting shot from ShotGrid")
        if "data" in sg_shot and len(sg_shot["data"]) > 0:
            return [shot for shot in sg_shot["data"] if "attributes" in shot and "code" in shot["attributes"]]
        else:
            return []
    
    def get_tasks(self, shot_code, task_name):
        headers = {"Authorization": f"Bearer {self.tokens['access_token']}", "Accept": "application/json"}
        params = {"filter[project.Project.id]": self.config["project_id"], "filter[entity.Shot.code]": shot_code, "fields": "id,name,content,step"}
        if task_name:
            params["filter[content]"] = task_name
        response = self.client.get(f"{self.config['server_url']}/api/v1.1/entity/Task", headers=headers, params=params)
        sg_tasks = response.json()
        if "errors" in sg_tasks:
            raise Exception("Error getting tasks from ShotGrid")
        if "data" in sg_tasks and len(sg_tasks["data"]) > 0:
            return sg_tasks["data"]
        else:
            return []
    
    def get_versions(self, shot_code):
        headers = {"Authorization": f"Bearer {self.tokens['access_token']}", "Accept": "application/json"}
        params = {"filter[project.Project.id]": self.config["project_id"], "filter[entity.Shot.code]": shot_code, "fields": "id,code,entity.Shot.id"}
        params["sort"] = "-code"
        response = self.client.get(f"{self.config['server_url']}/api/v1.1/entity/Version", headers=headers, params=params)
        sg_versions = response.json()
        if "errors" in sg_versions:
            raise Exception("Error getting versions from ShotGrid")
        if "data" in sg_versions and len(sg_versions["data"]) > 0:
            sg_versions = sg_versions["data"]
            versions = [version for version in sg_versions if self.version_convention_regex.match(version["attributes"]["code"])]
            return versions
        else:
            return []
    
    def get_version_code(self, shot_code):
        versions = self.get_versions(shot_code)
        print("versions", versions)
        if len(versions) > 0:
            version_number = get_next_version_number(versions[0]["attributes"]["code"])
        else:
            version_number = "001"
        return self.format_version_code(version_number, shot_code)
    
    # def add_version_from_shot_code(self, shot_code, task_name, fields):
    #     shot = self.get_shot(shot_code)["data"][0]
    #     task = self.get_tasks(shot_code, task_name)["data"][0]
    #     versions = self.get_versions(shot_code)["data"]
    #     if len(versions) > 0:
    #         version_number = get_next_version_number(versions[0]["attributes"]["code"])
    #     else:
    #         version_number = "001"
    #     version_code = self.format_version_code(version_number, shot_code)
    #     self.add_version(version_code, shot["id"], task["id"], fields)
    
    def add_version(self, version_code, shot_id, task_id, fields):
        params = {
            "project":  { "type": "Project", "id": self.config["project_id"] },
            "entity":   { "type": "Shot",    "id": shot_id },
            "sg_task":  { "type": "Task",    "id": task_id },
        }
        fields["code"] = version_code
        params.update(fields)
        headers = {"Authorization": f"Bearer {self.tokens['access_token']}", "Accept": "application/json"}
        response = self.client.post(f"{self.config['server_url']}/api/v1/entity/versions", headers=headers, json=params)
        if "errors" in response.json():
            print("response", response.json())
            raise Exception("Error adding version to ShotGrid")
        return response.json()
    
    def format_version_code(self, version_number, shot_code):
        if self.config.get("version_convention"):
            return self.config["version_convention"].format(SHOT_CODE=shot_code, VERSION_NUMBER=version_number)
        else:
            return f"{shot_code}_v{version_number}"

config_path = os.path.join(Path(__file__).parent.parent, "shotgrid_config.json")
print("config_path", config_path)
if not os.path.exists(config_path):
    raise Exception("shotgrid_config.json not found")
with open(config_path, "r") as f:
    shotgrid_config = json.load(f)

sg = ShotGrid(shotgrid_config)
sg_shots = sg.get_shots()
shots = {shot["attributes"]["code"]: shot for shot in sg_shots if "attributes" in shot and "code" in shot["attributes"]}
tasks = {}
for shot_code in shots.keys():
    tasks[shot_code] = {}
    for task_name in shotgrid_config["comfyui_task_names"]:
        sg_tasks = sg.get_tasks(shot_code, task_name)
        if len(sg_tasks) > 0:
            tasks[shot_code][task_name] = sg_tasks[0]