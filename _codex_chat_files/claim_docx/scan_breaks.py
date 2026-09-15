from pathlib import Path
from zipfile import ZipFile
import re


path = Path(r"C:\Users\Владимир\Desktop\Пример притензии.docx")
xml = ZipFile(path).read("word/document.xml").decode("utf-8")
patterns = ["w:type=\"page\"", "lastRenderedPageBreak", "w:br"]
for pattern in patterns:
    print(pattern, xml.count(pattern))
for match in re.finditer("|".join(re.escape(pattern) for pattern in patterns), xml):
    start = max(0, match.start() - 220)
    end = min(len(xml), match.end() + 220)
    print("----", match.group(0), match.start())
    print(xml[start:end])
