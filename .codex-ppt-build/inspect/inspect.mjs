import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const sourcePath = "C:/Users/Владимир/Desktop/Инструкция CRM Передача/CRM Передача - инструкция.pptx";
const pres = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
const snapshot = await pres.inspect({kind:"slide,textbox,shape,image,notes,layout", maxChars:12000});
await fs.writeFile(".codex-ppt-build/inspect/inspect.ndjson", snapshot.ndjson, "utf8");
console.log(snapshot.ndjson.slice(0, 4000));
