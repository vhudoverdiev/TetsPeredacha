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
    body_parts.extend(_defect_statement_tables(project, [task for task in tasks if not task.is_done]))
    body_parts.append(_paragraph("", spacing_after=120))
    body_parts.append(_paragraph("", spacing_after=120))
    body_parts.extend(_defect_statement_tables(project, [task for task in tasks if task.is_done], completed=True))

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WORD_NS}"><w:body>'
        + "".join(body_parts)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        + '<w:pgMar w:top="1134" w:right="850" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>'
        + "</w:sectPr></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _rels_xml())
        archive.writestr("word/document.xml", document_xml)


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
        _paragraph("ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ ", bold=True, align="center", size=28, spacing_after=0),
        _paragraph("Специализированный застройщик", bold=True, align="center", size=28, spacing_after=0),
        _paragraph(f"«{developer_name}»", bold=True, align="center", size=28, spacing_after=0),
        _paragraph(f"ИНН/КПП {project.inn_kpp or '—'}, ОГРН {project.ogrn or '—'}", align="center", size=20, spacing_after=0),
        _paragraph(f"Юридический адрес: {project.legal_address or '—'}", align="center", size=20, spacing_after=120),
        _paragraph("", spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph("Претензия", bold=True, size=24, spacing_after=0),
        _paragraph(f"Исх. №____  от {_numeric_date(current_date)} г. ", size=22, spacing_after=0),
        _paragraph(contractor_name, align="right", size=22, spacing_after=0),
        _paragraph(contractor_address, align="right", size=22, spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph(_salutation(contractor), size=22, spacing_after=120),
        _paragraph("", spacing_after=0),
        _paragraph(_intro_text(project, technical_customer, contractor_name, contract_number), first_line=708, size=22),
        _paragraph(_deadline_text(author_email), first_line=708, size=22),
        _paragraph(_consequence_text(developer_name), first_line=708, size=22),
        _paragraph(f"Направлено на адрес эл. почты: {contractor_email or '—'}", size=22),
        _paragraph("", spacing_after=0),
        _paragraph("Приложение:", size=22, spacing_after=0),
        _paragraph(f"- Дефектные ведомости от {_numeric_date(current_date)} г.", size=22, spacing_after=0),
        _paragraph("- Все работы по устранению замечаний сдавать данным представителям Застройщика: ", size=22, spacing_after=0),
        _paragraph(representative or "—", size=22, spacing_after=160),
        _paragraph("", spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph(director or _director_title(project), size=22, spacing_after=120),
        _paragraph("", spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph("", spacing_after=0),
        _paragraph(_executor_line(author), size=20, spacing_after=0),
        _paragraph(author.email or "", size=20, spacing_after=120),
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


def _deadline_text(author_email: str) -> str:
    email = author_email or "—"
    return (
        "На основании изложенного, просим устранить проявившиеся недостатки в течение 3 рабочих дней с момента "
        f"получения настоящей претензии и направить на электронный адрес: {email}  информацию о результате "
        "выполненных Вами работ."
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
        return [_statement_table(project.name, title, [])]
    tables = []
    for point, point_tasks in grouped:
        rows = _statement_rows(point_tasks)
        tables.append(_statement_table(project.name, _point_title(point), rows))
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


def _statement_table(project_name: str, work_title: str, rows: list[list[str]]) -> str:
    table_rows = [
        _merged_row(f"Дефектная ведомость {project_name}", columns=3, bold=True, align="center"),
        _merged_row(work_title, columns=3, bold=True, align="center"),
        _row(["№ кв", "№ строительный", "Замечания"], widths=[900, 1900, 8200], bold=True, align="center"),
    ]
    data_rows = rows or [["—", "—", "Нет замечаний"]]
    for row_values in data_rows:
        table_rows.append(_row(row_values, widths=[900, 1900, 8200], bold=False, align=None))
    return (
        "<w:tbl><w:tblPr>"
        '<w:tblW w:w="0" w:type="auto"/>'
        '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="000000"/>'
        '<w:left w:val="single" w:sz="4" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="000000"/>'
        '<w:right w:val="single" w:sz="4" w:color="000000"/>'
        '<w:insideH w:val="single" w:sz="4" w:color="000000"/>'
        '<w:insideV w:val="single" w:sz="4" w:color="000000"/></w:tblBorders>'
        "</w:tblPr>"
        '<w:tblGrid><w:gridCol w:w="900"/><w:gridCol w:w="1900"/><w:gridCol w:w="8200"/></w:tblGrid>'
        + "".join(table_rows)
        + "</w:tbl>"
    )


def _merged_row(text: str, *, columns: int, bold: bool, align: str) -> str:
    return (
        "<w:tr>"
        f'<w:tc><w:tcPr><w:gridSpan w:val="{columns}"/><w:vAlign w:val="center"/></w:tcPr>'
        f'{_paragraph(text, bold=bold, align=align, size=20, in_cell=True)}'
        "</w:tc></w:tr>"
    )


def _row(values: list[str], *, widths: list[int], bold: bool, align: str | None) -> str:
    cells = []
    for index, value in enumerate(values):
        width = widths[index] if index < len(widths) else widths[-1]
        paragraphs = "".join(
            _paragraph(line or " ", bold=bold, align=align, size=18, in_cell=True)
            for line in str(value or "").splitlines() or [""]
        )
        cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>{paragraphs}</w:tc>')
    return "<w:tr>" + "".join(cells) + "</w:tr>"


def _paragraph(
    text: str,
    *,
    bold: bool = False,
    align: str | None = None,
    size: int = 22,
    first_line: int | None = None,
    spacing_after: int = 120,
    in_cell: bool = False,
) -> str:
    paragraph_props = []
    if align:
        paragraph_props.append(f'<w:jc w:val="{align}"/>')
    if first_line:
        paragraph_props.append(f'<w:ind w:firstLine="{first_line}"/>')
    if in_cell:
        paragraph_props.append('<w:spacing w:before="0" w:after="0"/>')
    else:
        paragraph_props.append(f'<w:spacing w:before="0" w:after="{spacing_after}"/>')
    run_props = (
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="Times New Roman" w:cs="Times New Roman"/>'
        f'{"<w:b/>" if bold else ""}<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
    )
    safe_text = escape(text)
    xml_space = ' xml:space="preserve"' if text.startswith(" ") or text.endswith(" ") or "  " in text else ""
    return f"<w:p><w:pPr>{''.join(paragraph_props)}</w:pPr><w:r>{run_props}<w:t{xml_space}>{safe_text}</w:t></w:r></w:p>"


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
    if title.lower().startswith("работ"):
        return title
    return f"{point.point_number}. {title}" if point.point_number else title


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
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""


def _rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
