import re
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from config import Config
from app import create_app, db
from app.models import Apartment, Contractor, Project, STATUS_DONE, STATUS_NOT_STARTED, Task, User, WorkPoint
from app.services.contractor_claim_docx import build_contractor_claim_docx


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{WORD_NS}}}"


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "contractor-claim-docx-test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


def _docx_text(path: Path) -> str:
    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    text = re.sub(r"<[^>]+>", " ", xml)
    return re.sub(r"\s+", " ", text)


def _document_root(path: Path):
    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    return ET.fromstring(xml)


class ContractorClaimDocxTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        TestConfig.EXPORT_FOLDER = self.tempdir.name
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        self.project = Project(
            name='ЖК "Квартал 100" - 7 очередь',
            address="Архангельская обл., г. Северодвинск, ул. Ломоносова 79 к 3",
            developer_name='ООО СЗ "Аквилон-Северодвинск"',
            inn_kpp="2901297953/290101001",
            ogrn="1192901006924",
            legal_address="164515, г. Северодвинск, ул. Ломоносова, д. 85, корпус 1, офис 2",
            developer_representative="Худовердиев В.С.",
            developer_representative_phone="8 900 000-00-00",
        )
        self.contractor = Contractor(
            project=self.project,
            name='ООО "Коробка"',
            legal_address="164520, Архангельская обл.",
            contract_number="07-04/2025",
            email="contractor@example.test",
        )
        self.point = WorkPoint(point_number="12", short_name="12. Возведение коробки здания")
        self.contractor.work_points.append(self.point)
        self.apartment = Apartment(project=self.project, apartment_number="1", owner_name="Иванов И.И.")
        self.apartment.construction_number = "1-2-1"
        self.contractor.apartments.append(self.apartment)
        self.author = User(
            username="engineer",
            full_name="Костылева Н.А.",
            phone="8(8184) 52-00-00 (доб.354)",
            email="kostyleva@group-akvilon.ru",
            password_hash="unused",
        )
        self.open_task = Task(
            project=self.project,
            apartment=self.apartment,
            work_point=self.point,
            source_uid="claim-open",
            description="Не выполнена заделка штробы.",
            source_row_index=10,
            status=STATUS_NOT_STARTED,
        )
        self.second_open_task = Task(
            project=self.project,
            apartment=self.apartment,
            work_point=self.point,
            source_uid="claim-open-2",
            description="Сбить наплывы строительных смесей.",
            source_row_index=11,
            status=STATUS_NOT_STARTED,
        )
        self.done_task = Task(
            project=self.project,
            apartment=self.apartment,
            work_point=self.point,
            source_uid="claim-done",
            description="Выполнена зачистка поверхности.",
            source_row_index=12,
            status=STATUS_DONE,
            is_done=True,
            responsible=self.author,
        )
        db.session.add_all([self.project, self.contractor, self.point, self.apartment, self.author, self.open_task, self.second_open_task, self.done_task])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.tempdir.cleanup()

    def test_claim_docx_uses_project_contractor_and_author_data(self):
        path = build_contractor_claim_docx(
            [self.open_task, self.second_open_task, self.done_task],
            project=self.project,
            contractor=self.contractor,
            author=self.author,
        )

        self.assertTrue(path.exists())
        text = _docx_text(path)
        self.assertIn("ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ", text)
        self.assertIn("Претензия", text)
        self.assertIn('Дефектная ведомость ЖК "Квартал 100" - 7 очередь', text)
        self.assertIn("2901297953/290101001", text)
        self.assertIn("1192901006924", text)
        self.assertIn('ООО "Коробка"', text)
        self.assertIn("07-04/2025", text)
        self.assertIn("Направлено на адрес эл. почты: contractor@example.test", text)
        self.assertIn("№ кв", text)
        self.assertIn("№ строительный", text)
        self.assertIn("1-2-1", text)
        self.assertIn("Возведение коробки здания", text)
        self.assertNotIn("12. Возведение коробки здания", text)
        self.assertIn("Не выполнена заделка штробы.", text)
        self.assertIn("Сбить наплывы строительных смесей.", text)
        self.assertIn("Выполнена зачистка поверхности.", text)
        self.assertIn("Худовердиев В.С. 8 900 000-00-00", text)
        self.assertIn("Исп.: Костылева Н.А.", text)
        self.assertIn("8(8184) 52-00-00 (доб.354)", text)
        self.assertIn("kostyleva@group-akvilon.ru", text)

    def test_claim_docx_matches_reference_page_and_table_layout(self):
        path = build_contractor_claim_docx(
            [self.open_task, self.second_open_task, self.done_task],
            project=self.project,
            contractor=self.contractor,
            author=self.author,
        )
        root = _document_root(path)
        with ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
            document_rels = archive.read("word/_rels/document.xml.rels").decode("utf-8")
            stamp_bytes = archive.read("word/media/image1.png")
            content_types = archive.read("[Content_Types].xml").decode("utf-8")

        page_breaks = root.findall(f".//{W}br[@{W}type='page']")
        self.assertEqual(len(page_breaks), 2)
        self.assertIn("<wp:anchor", document_xml)
        self.assertIn('r:embed="rIdStamp"', document_xml)
        self.assertIn('cx="1590725"', document_xml)
        self.assertIn('cy="1176020"', document_xml)
        self.assertIn('Id="rIdStamp"', document_rels)
        self.assertIn('Target="media/image1.png"', document_rels)
        self.assertIn('ContentType="image/png"', content_types)
        self.assertGreater(len(stamp_bytes), 0)
        self.assertRegex(document_xml, r'<w:color w:val="0000FF"/>.*?<w:t>kostyleva@group-akvilon\.ru</w:t>')
        self.assertRegex(document_xml, r'<w:color w:val="0000FF"/>.*?<w:t>contractor@example\.test</w:t>')
        self.assertIn('<w:bottom w:val="single" w:sz="4" w:space="1" w:color="auto"/>', document_xml)
        self.assertIn('<w:jc w:val="center"/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>', document_xml)
        self.assertIn('<w:ind w:left="284" w:right="-709" w:firstLine="424"/>', document_xml)
        self.assertIn('<w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>', document_xml)

        page_margins = root.find(f".//{W}sectPr/{W}pgMar")
        self.assertEqual(page_margins.attrib[f"{W}top"], "567")
        self.assertEqual(page_margins.attrib[f"{W}right"], "1133")
        self.assertEqual(page_margins.attrib[f"{W}bottom"], "709")
        self.assertEqual(page_margins.attrib[f"{W}left"], "1134")

        tables = root.findall(f".//{W}tbl")
        self.assertEqual(len(tables), 2)
        first_grid = [column.attrib[f"{W}w"] for column in tables[0].findall(f"{W}tblGrid/{W}gridCol")]
        completed_grid = [column.attrib[f"{W}w"] for column in tables[1].findall(f"{W}tblGrid/{W}gridCol")]
        self.assertEqual(first_grid, ["701", "1985", "6653"])
        self.assertEqual(completed_grid, ["846", "2126", "6367"])

        first_title_size = tables[0].find(f".//{W}sz").attrib[f"{W}val"]
        self.assertEqual(first_title_size, "28")
        body_sizes = [node.attrib[f"{W}val"] for node in tables[0].findall(f".//{W}sz")]
        self.assertIn("24", body_sizes)


if __name__ == "__main__":
    unittest.main()
