# ComfyUI Guidance for Artists

## Instructions

* Make sure comfyui-movielabs-util custom nodes are installed in your ComfyUI environment. You will need three nodes: Asset Provenance, Provenance Connector, and Save Image With Provenance.
* You can continue to use your workflow. And instead of regular Save Image node you normally use, you will have to use the above three nodes.
* The Asset Provenance node will provide you a drop down to select a Shot. Make sure to select the right shot.
* The for_review setting in Asset Provenance node must be set to true when you want to push the output that you like to ShotGrid. If you keep it true, all the outputs will be pushed to ShotGrid. So set it to false again after a push, so you don’t accidentally push the next iteration to ShotGrid.
* If there are no error messages, when you set the for_review to true, that means the output is correctly pushed to ShotGrid. You may want to check that if your output made it to Versions in ShotGrid UI.


## Troubleshooting

* If the custom nodes are not available, contact ??? for guidance.
* If you do not see a drop down of Shots in Asset Provenance node, make sure you have Internet connection. The shot codes are pulled from ShotGrid live.
* If you see an error message when adding the custom nodes and you are sure you have Internet connection, try a restart of the ComfyUI.
* If you see an error message when you are pushing the output to ShotGrid (i.e., when for_review is set to true), then you can do one of two things:
    * Remove the Asset Provenance node and try adding again. Make sure to select the right shot code and type in any notes that you had before you removed the node. Now, queue the workflow again.
    * If the issue persists, you may have to restart ComfyUI again (sorry!). Make sure you save the workflow before the restart, so you don’t lose your work.
* If you continue to face issues, you have to manually upload the output to ShotGrid. Contact ??? for guidance at that point. Make sure you update the following fields at the minimum:
    * Tool (should be ComfyUI)
    * ComfyUI Prompt (this should be contents of the json file you get when you Export API from ComfyUI menu)
    * ComfyUI Workflow (this should be contents of the json file you get when you Export from ComfyUI menu). Note that ComfyUI provides two exports (Export and Export API).
    * Notes (should be whatever notes you want to add)
    * Output (should be the PNG file that you upload). 
        * Keep the three custom nodes and set for_review to false to save the PNG and use this PNG to upload manually. The PNG saved using the custom nodes (even when the PNG is not directly pushed to ShotGrid) has special metadata embedded in it and this is useful.
        * If you face an issue using the custom nodes, then remove them and use regular Save Image node and upload this PNG.



## Administrators

* Make sure shotgrid_config.json in the root directory of comfyui-movielabs-util is properly configured:
    * The client_secret should be updated. Ben Abergel has the secret.
    * The user_login_map is a map of workstation logins and ShotGrid logins for artists.
    * The entire file should be in proper JSON format. Otherwise, the nodes will not load.
* You can add more ComfyUI tasks to the comfyui_task_names property. Currently only Generate Image is added to the list.
* Version convention can be updated using the version_convention property. Right now, it is CUI_{SHOT_CODE}_style_v{VERSION_NUMBER}, The things in curly braces are automatically filled in by the custom node. The things outside the curly braces can be changed by you, if you prefer a different naming convention.

