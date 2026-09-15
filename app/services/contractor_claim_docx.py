from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape
import re
import zipfile

from flask import current_app

from app.models import Apartment, Contractor, Project, Task, User, WorkPoint
from app.services.filename import safe_filename_part


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
STAMP_REL_ID = "rIdStamp"
STAMP_IMAGE_PATH = Path(__file__).resolve().parents[1] / "static" / "img" / "claim_stamp.png"
RUSSIAN_MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def contractor_claim_filename(project: Project, contractor: Contractor | None) -> str:
    parts = [project.name, "Претензия"]
    if contractor:
        parts.append(contractor.name)
    stem = "_".join(safe_filename_part(part) for part in parts if str(part or "").strip())
    return f"{stem or 'pretension'}_{datetime.now().strftime('%Y-%m-%d')}.docx"


def build_contractor_claim_docx(
    tasks: list[Task],
    *,
    project: Project,
    contractor: Contractor | None,
    author: User,
) -> Path:
    path = Path(current_app.config["EXPORT_FOLDER"]) / contractor_claim_filename(project, contractor)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_claim_docx(path, tasks, project=project, contractor=contractor, author=author)
    return path


def _write_claim_docx(path: Path, tasks: list[Task], *, project: Project, contractor: Contractor | None, author: User) -> None:
    current_date = date.today()
    body_parts: list[str] = []
    body_parts.extend(_letter_paragraphs(project, contractor, author, current_date))
    body_parts.append(_page_break())
    body_parts.extend(_defect_statement_tables(project, [task for task in tasks if not task.is_done]))
    body_parts.append(_page_break())
    body_parts.extend(_defect_statement_tables(project, [task for task in tasks if task.is_done], completed=True))

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WORD_NS}" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>'
        + "".join(body_parts)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        + '<w:pgMar w:top="567" w:right="1133" w:bottom="709" w:left="1134" w:header="709" w:footer="709" w:gutter="0"/>'
        + '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/>'
        + "</w:sectPr></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _rels_xml())
        archive.writestr("word/_rels/document.xml.rels", _document_rels_xml())
        archive.writestr("word/document.xml", document_xml)
        archive.write(STAMP_IMAGE_PATH, "word/media/image1.png")


def _letter_paragraphs(project: Project, contractor: Contractor | None, author: User, current_date: date) -> list[str]:
    developer_name = _developer_name(project)
    technical_customer = project.technical_customer or "Техзаказчик"
    contractor_name = contractor.name if contractor else "Подрядчик"
    contractor_address = contractor.legal_address if contractor else ""
    contractor_email = contractor.email if contractor else ""
    contract_number = contractor.contract_number if contractor else ""
    author_email = author.email or ""
    representative = _join_non_empty([project.developer_representative, project.developer_representative_phone], " ")
    director = _join_non_empty([_director_title(project), project.developer_director], "                                                   ")
    parts = [
        _paragraph("ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ ", bold=True, align="center", size=44, spacing_after=0),
        _paragraph("Специализированный застройщик", bold=True, align="center", size=44, spacing_after=0),
        _paragraph(f"«{developer_name}»", bold=True, align="center", size=44, spacing_after=0),
        _paragraph(f"ИНН/КПП {project.inn_kpp or '—'}, ОГРН {project.ogrn or '—'}", align="center", size=20, spacing_after=0),
        _paragraph(f"Юридический адрес: {project.legal_address or '—'}", align="center", size=20, spacing_after=120),
        _paragraph("", spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph("Претензия", bold=True, size=24, spacing_after=0),
        _paragraph(f"Исх. №____  от {_numeric_date(current_date)} г. ", align="both", size=22, spacing_after=0, underline=True),
        _paragraph(contractor_name, align="right", size=22, spacing_after=0),
        _paragraph(contractor_address, align="right", size=22, spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph(_salutation(contractor), size=22, spacing_after=120),
        _paragraph("", spacing_after=0),
        _paragraph(_intro_text(project, technical_customer, contractor_name, contract_number), align="both", left=284, first_line=425, size=22, spacing_after=0),
        _deadline_paragraph(author_email),
        _paragraph(_consequence_text(developer_name), align="both", left=284, first_line=425, size=22, spacing_after=0),
        _email_notice_paragraph(contractor_email),
        _paragraph("", spacing_after=0),
        _paragraph("Приложение:", align="both", left=284, first_line=425, size=22, spacing_after=0),
        _paragraph(f"- Дефектные ведомости от {_numeric_date(current_date)} г.", align="both", left=284, first_line=425, size=22, spacing_after=0),
        _paragraph("- Все работы по устранению замечаний сдавать данным представителям Застройщика: ", align="both", left=284, first_line=425, size=22, spacing_after=0),
        _paragraph(representative or "—", align="both", left=284, first_line=425, size=22, spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph("", spacing_after=0),
        _stamp_paragraph(),
        _paragraph(director or _director_title(project), size=22, spacing_after=120),
        _paragraph("", spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph(_executor_line(author), size=20, spacing_after=0),
        _paragraph(author.email or "", size=20, spacing_after=120, color="0563C1", underline=True),
        _paragraph("", spacing_after=120),
    ]
    return parts


def _intro_text(project: Project, technical_customer: str, contractor_name: str, contract_number: str) -> str:
    contract_text = f"договора подряда № {contract_number}" if contract_number else "договора подряда"
    return (
        f"В рамках исполнения гарантийных обязательств п.1.7, {contract_text}, заключенным между "
        f"{technical_customer} (далее-Техзаказчик) и {contractor_name} (далее-Подрядчик), направляем в Ваш адрес "
        f"дефектные ведомости, с перечнем недостатков, выявленных участниками долевого строительства в процессе "
        f"передачи квартир, расположенных по адресу: {project.address or '—'} ({project.name})."
    )


def _deadline_paragraph(author_email: str) -> str:
    email = author_email or "—"
    return _paragraph_runs(
        [
            ("На основании изложенного, просим устранить проявившиеся недостатки в течение 3 рабочих дней с момента получения настоящей претензии и направить на электронный адрес: ", {}),
            (email, {"color": "0563C1", "underline": True}),
            ("  информацию о результате выполненных Вами работ.", {}),
        ],
        align="both",
        left=284,
        first_line=425,
        size=22,
        spacing_after=0,
    )


def _email_notice_paragraph(contractor_email: str) -> str:
    email = contractor_email or "—"
    return _paragraph_runs(
        [
            ("Направлено на адрес эл. почты: ", {}),
            (email, {"color": "0563C1", "underline": True}),
        ],
        align="both",
        left=284,
        first_line=425,
        size=22,
        spacing_after=0,
    )


def _consequence_text(developer_name: str) -> str:
    return (
        f"В случае неисполнения настоящего требования, ООО СЗ «{developer_name}» будет вынуждено привлечь "
        "специализированную организацию для устранения допущенных Вами недостатков работ с возложением затрат "
        "и ущербов на Вашу организацию, а также оставляет за собой право обратиться в суд."
    )


def _defect_statement_tables(project: Project, tasks: list[Task], *, completed: bool = False) -> list[str]:
    grouped = _group_tasks_by_point(tasks)
    if not grouped:
        title = "Выполненные замечания" if completed else "Замечания"
        return [_statement_table(project.name, title, [], completed=completed)]
    tables = []
    for point, point_tasks in grouped:
        rows = _statement_rows(point_tasks)
        tables.append(_statement_table(project.name, _point_title(point), rows, completed=completed))
        tables.append(_paragraph("", spacing_after=120))
    return tables


def _group_tasks_by_point(tasks: list[Task]) -> list[tuple[WorkPoint | None, list[Task]]]:
    grouped: dict[int | str, list[Task]] = defaultdict(list)
    points: dict[int | str, WorkPoint | None] = {}
    for task in tasks:
        point = task.work_point
        key = point.id if point and point.id is not None else f"none-{task.id or id(task)}"
        grouped[key].append(task)
        points[key] = point
    return sorted(
        ((points[key], value) for key, value in grouped.items()),
        key=lambda item: (str(item[0].point_number if item[0] else ""), str(item[0].display_name if item[0] else "")),
    )


def _statement_rows(tasks: list[Task]) -> list[list[str]]:
    grouped: dict[int | str, list[Task]] = defaultdict(list)
    apartments: dict[int | str, Apartment | None] = {}
    for task in tasks:
        apartment = task.apartment
        key = apartment.id if apartment and apartment.id is not None else f"none-{task.id or id(task)}"
        grouped[key].append(task)
        apartments[key] = apartment
    rows = []
    for key, apartment_tasks in sorted(grouped.items(), key=lambda item: _apartment_sort_key(apartments[item[0]])):
        apartment = apartments[key]
        descriptions = [_task_description(task) for task in _ordered_tasks(apartment_tasks)]
        rows.append([
            _apartment_number(apartment),
            _construction_number(apartment),
            "\n".join(description for description in descriptions if description) or "—",
        ])
    return rows


def _statement_table(project_name: str, work_title: str, rows: list[list[str]], *, completed: bool = False) -> str:
    widths = [846, 2126, 6367] if completed else [701, 1985, 6653]
    table_width = sum(widths)
    table_rows = [
        _merged_row(f"Дефектная ведомость {project_name}", columns=3, bold=True, align="center"),
        _merged_row(work_title, columns=3, bold=True, align="center"),
        _row(["№ кв", "№ строительный", "Замечания"], widths=widths, bold=True, align="center"),
    ]
    data_rows = rows or [["—", "—", "Нет замечаний"]]
    for row_values in data_rows:
        table_rows.append(_row(row_values, widths=widths, bold=False, align="center"))
    return (
        "<w:tbl><w:tblPr>"
        f'<w:tblW w:w="{table_width}" w:type="dxa"/>'
        '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="000000"/>'
        '<w:left w:val="single" w:sz="4" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="000000"/>'
        '<w:right w:val="single" w:sz="4" w:color="000000"/>'
        '<w:insideH w:val="single" w:sz="4" w:color="000000"/>'
        '<w:insideV w:val="single" w:sz="4" w:color="000000"/></w:tblBorders>'
        '<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
        '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
        "</w:tblPr>"
        + "<w:tblGrid>"
        + "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
        + "</w:tblGrid>"
        + "".join(table_rows)
        + "</w:tbl>"
    )


def _merged_row(text: str, *, columns: int, bold: bool, align: str) -> str:
    return (
        '<w:tr><w:trPr><w:trHeight w:val="315"/></w:trPr>'
        f'<w:tc><w:tcPr><w:gridSpan w:val="{columns}"/><w:vAlign w:val="center"/></w:tcPr>'
        f'{_paragraph(text, bold=bold, align=align, size=28, in_cell=True)}'
        "</w:tc></w:tr>"
    )


def _row(values: list[str], *, widths: list[int], bold: bool, align: str | None) -> str:
    cells = []
    for index, value in enumerate(values):
        width = widths[index] if index < len(widths) else widths[-1]
        paragraphs = "".join(
            _paragraph(line or " ", bold=bold, align=align, size=24, in_cell=True)
            for line in str(value or "").splitlines() or [""]
        )
        cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>{paragraphs}</w:tc>')
    return '<w:tr><w:trPr><w:trHeight w:val="315"/></w:trPr>' + "".join(cells) + "</w:tr>"


def _paragraph(
    text: str,
    *,
    bold: bool = False,
    align: str | None = None,
    size: int = 22,
    first_line: int | None = None,
    left: int | None = None,
    right: int | None = None,
    spacing_after: int = 120,
    in_cell: bool = False,
    underline: bool = False,
    color: str | None = None,
) -> str:
    return _paragraph_runs(
        [(text, {"bold": bold, "underline": underline, "color": color})],
        align=align,
        size=size,
        first_line=first_line,
        left=left,
        right=right,
        spacing_after=spacing_after,
        in_cell=in_cell,
    )


def _paragraph_runs(
    runs: list[tuple[str, dict[str, object]]],
    *,
    align: str | None = None,
    size: int = 22,
    first_line: int | None = None,
    left: int | None = None,
    right: int | None = None,
    spacing_after: int = 120,
    in_cell: bool = False,
) -> str:
    paragraph_props = []
    if align:
        paragraph_props.append(f'<w:jc w:val="{align}"/>')
    ind_props = []
    if left is not None:
        ind_props.append(f'w:left="{left}"')
    if right is not None:
        ind_props.append(f'w:right="{right}"')
    if first_line is not None:
        ind_props.append(f'w:firstLine="{first_line}"')
    if ind_props:
        paragraph_props.append(f'<w:ind {" ".join(ind_props)}/>')
    if in_cell:
        paragraph_props.append('<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>')
    else:
        paragraph_props.append(f'<w:spacing w:before="0" w:after="{spacing_after}" w:line="240" w:lineRule="auto"/>')
    run_xml = "".join(
        _run_xml(
            text,
            size=size,
            bold=bool(options.get("bold")),
            underline=bool(options.get("underline")),
            color=str(options.get("color")) if options.get("color") else None,
        )
        for text, options in runs
    )
    return f"<w:p><w:pPr>{''.join(paragraph_props)}</w:pPr>{run_xml}</w:p>"


def _run_xml(text: str, *, size: int, bold: bool = False, underline: bool = False, color: str | None = None) -> str:
    color_xml = f'<w:color w:val="{color}"/>' if color else ""
    run_props = (
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="Times New Roman" w:cs="Times New Roman"/>'
        f'{"<w:b/><w:bCs/>" if bold else ""}{"<w:u w:val=\"single\"/>" if underline else ""}'
        f'{color_xml}<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
    )
    safe_text = escape(text)
    xml_space = ' xml:space="preserve"' if text.startswith(" ") or text.endswith(" ") or "  " in text else ""
    return f"<w:r>{run_props}<w:t{xml_space}>{safe_text}</w:t></w:r>"


def _page_break() -> str:
    return (
        "<w:p><w:r><w:rPr><w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\" "
        "w:eastAsia=\"Times New Roman\" w:cs=\"Times New Roman\"/>"
        "<w:sz w:val=\"18\"/><w:szCs w:val=\"18\"/></w:rPr><w:br w:type=\"page\"/></w:r></w:p>"
    )


def _stamp_paragraph() -> str:
    return (
        '<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
        '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>'
        '<w:drawing><wp:anchor distT="0" distB="0" distL="114300" distR="114300" '
        'simplePos="0" relativeHeight="251658240" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">'
        '<wp:simplePos x="0" y="0"/>'
        '<wp:positionH relativeFrom="column"><wp:posOffset>3394710</wp:posOffset></wp:positionH>'
        '<wp:positionV relativeFrom="paragraph"><wp:posOffset>9525</wp:posOffset></wp:positionV>'
        '<wp:extent cx="1590725" cy="1176020"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:wrapNone/>'
        '<wp:docPr id="1" name="Picture 1"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="claim_stamp.png"/>'
        '<pic:cNvPicPr><a:picLocks noChangeAspect="1" noChangeArrowheads="1"/></pic:cNvPicPr>'
        '</pic:nvPicPr><pic:blipFill>'
        f'<a:blip r:embed="{STAMP_REL_ID}"><a:extLst><a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">'
        '<a14:useLocalDpi val="0"/></a:ext></a:extLst></a:blip>'
        '<a:srcRect/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr bwMode="auto"><a:xfrm><a:off x="0" y="0"/><a:ext cx="1590725" cy="1176020"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic>'
        '</wp:anchor></w:drawing></w:r></w:p>'
    )


def _developer_name(project: Project) -> str:
    name = str(project.developer_name or "").strip()
    return _strip_company_prefix(name) or name or "Аквилон Северодвинск"


def _director_title(project: Project) -> str:
    developer = project.developer_name or "ООО СЗ"
    return f"Директор {developer}"


def _salutation(contractor: Contractor | None) -> str:
    if not contractor or not contractor.name:
        return "Уважаемые коллеги!"
    return "Уважаемые коллеги!"


def _point_title(point: WorkPoint | None) -> str:
    if not point:
        return "Замечания"
    title = str(point.display_name or "").strip()
    if not title:
        return f"Пункт {point.point_number}"
    return title


def _task_description(task: Task) -> str:
    return str(task.description or task.source_cell_value or "").strip()


def _ordered_tasks(tasks: list[Task]) -> list[Task]:
    return sorted(tasks, key=lambda task: (task.source_row_index or 0, task.id or 0))


def _apartment_sort_key(apartment: Apartment | None) -> tuple[int, str]:
    value = _apartment_number(apartment)
    match = re.search(r"\d+", value)
    return (int(match.group(0)) if match else 10**9, value)


def _apartment_number(apartment: Apartment | None) -> str:
    if not apartment:
        return "—"
    fallback = apartment.label() if hasattr(apartment, "label") else ""
    return str(apartment.apartment_number or fallback or "—").strip() or "—"


def _construction_number(apartment: Apartment | None) -> str:
    if not apartment:
        return "—"
    return str(apartment.construction_number or "—").strip() or "—"


def _executor_line(author: User) -> str:
    name = author.full_name or author.username or ""
    phone = author.phone or ""
    return _join_non_empty([f"Исп.: {name}".strip(), f"т. {phone}" if phone else ""], " ")


def _numeric_date(value: date) -> str:
    return f"{value.day:02d}.{value.month:02d}.{value.year}"


def _join_non_empty(values: list[str | None], separator: str) -> str:
    return separator.join(str(value or "").strip() for value in values if str(value or "").strip())


def _strip_company_prefix(value: str) -> str:
    value = value.strip().strip("«»\"")
    value = re.sub(r"^(ооо|общество с ограниченной ответственностью)\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^сз\s+", "", value, flags=re.IGNORECASE)
    return value.strip().strip("«»\"")


def _content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""


def _rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def _document_rels_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="{STAMP_REL_ID}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>"""
