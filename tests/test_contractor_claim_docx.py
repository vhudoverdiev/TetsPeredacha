import re
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from config import Config
from app import create_app, db
from app.models import Apartment, Contractor, Project, STATUS_DONE, STATUS_NOT_STARTED, Task, User, WorkPoint
from app.services.contractor_claim_docx import build_contractor_claim_docx


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
        self.point = WorkPoint(point_number="12", short_name="Возведение коробки здания")
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
        self.assertIn("12. Возведение коробки здания", text)
        self.assertIn("Не выполнена заделка штробы.", text)
        self.assertIn("Сбить наплывы строительных смесей.", text)
        self.assertIn("Выполнена зачистка поверхности.", text)
        self.assertIn("Худовердиев В.С. 8 900 000-00-00", text)
        self.assertIn("Исп.: Костылева Н.А.", text)
        self.assertIn("8(8184) 52-00-00 (доб.354)", text)
        self.assertIn("kostyleva@group-akvilon.ru", text)


if __name__ == "__main__":
    unittest.main()
