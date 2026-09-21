import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const src = "C:/Users/Владимир/Desktop/Сайты/Передача/Инструкция для пользователя/CRM Передача - инструкция.pptx";
const p = await PresentationFile.importPptx(await FileBlob.load(src));
const snapshot = await p.inspect({ kind: "slide,textbox,shape,image,notes,layout", maxChars: 20000 });
await fs.writeFile("C:/Users/Владимир/Desktop/Сайты/Peredacha(test)/.codex-ppt-build/restyle_user_instruction/inspect.ndjson", snapshot.ndjson, "utf8");
console.log(snapshot.ndjson.slice(0, 4000));
