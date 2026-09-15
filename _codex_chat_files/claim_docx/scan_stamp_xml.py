from pathlib import Path
from zipfile import ZipFile


path = Path(r"C:\Users\Владимир\Desktop\Пример притензии.docx")
xml = ZipFile(path).read("word/document.xml").decode("utf-8")
for token in ("rId8", "wp:inline", "wp:anchor", "pic:pic", "graphicData"):
    index = xml.find(token)
    print(token, index)
    if index != -1:
        print(xml[max(0, index - 2200) : min(len(xml), index + 3200)])
