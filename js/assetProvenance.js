// import { app } from "../../scripts/app.js";

// app.registerExtension({
//     name: "AssetProvenanceExtension",
//     beforeRegisterNodeDef(nodeType, nodeData, app) {
//         if (nodeData.name === "AssetProvenance") {
//             const onNodeCreated = nodeType.prototype.onNodeCreated;
//             nodeType.prototype.onNodeCreated = function () {
//                 const node = this;
//                 console.log("node", node);
//                 let dropdown = node.widgets.find(w => w.name === "character_name");
//                 console.log("dropdown", dropdown);
//                 if (dropdown) {
//                     dropdown.value = ""; // Clear selection
//                     dropdown.callback(""); // Update UI
//                 }
//                 onNodeCreated?.apply(this, arguments);
//             };
//         }
//     },
// });
