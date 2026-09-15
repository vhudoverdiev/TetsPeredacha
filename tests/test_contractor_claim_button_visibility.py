import tempfile
import unittest

from config import Config
from app import create_app, db, login_manager
from app.models import Apartment, Contractor, Project, ROLE_ADMIN, STATUS_NOT_STARTED, Task, User, WorkPoint


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "contractor-claim-button-test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ContractorClaimButtonVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        TestConfig.EXPORT_FOLDER = self.tempdir.name
        self.app = create_app(TestConfig)
        self.previous_session_protection = login_manager.session_protection
        login_manager.session_protection = None
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

        self.project = Project(name='ЖК "Квартал 100" - 5 очередь')
        self.user = User(username="claim-button-admin", password_hash="unused", role=ROLE_ADMIN)
        self.contractor = Contractor(project=self.project, name='ООО "Коробка"')
        self.apartment = Apartment(project=self.project, apartment_number="1", owner_name="Иванов И.И.")
        self.point = WorkPoint(point_number="12", short_name="Возведение коробки здания")
        self.contractor.work_points.append(self.point)
        self.contractor.apartments.append(self.apartment)
        self.task = Task(
            project=self.project,
            apartment=self.apartment,
            work_point=self.point,
            source_uid="claim-button-task",
            description="Сбить наплывы строительных смесей.",
            status=STATUS_NOT_STARTED,
        )
        db.session.add_all([self.project, self.user, self.contractor, self.apartment, self.point, self.task])
        db.session.commit()

        with self.client.session_transaction() as session:
            session["_user_id"] = str(self.user.id)
            session["_fresh"] = True
            session["session_version"] = int(self.user.session_version or 0)
            session["current_project_id"] = self.project.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        login_manager.session_protection = self.previous_session_protection
        self.tempdir.cleanup()

    def test_claim_word_button_requires_selected_contractor(self):
        response = self.client.get("/contractors")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Претензия Word", response.get_data(as_text=True))

        response = self.client.get(f"/contractors?contractor_id={self.contractor.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Претензия Word", response.get_data(as_text=True))

    def test_claim_word_button_is_hidden_on_excel_selection_without_contractor(self):
        response = self.client.get("/contractors/excel-selection")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Претензия Word", response.get_data(as_text=True))

        response = self.client.get(f"/contractors/excel-selection?contractor_id={self.contractor.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Претензия Word", response.get_data(as_text=True))

    def test_docx_export_without_contractor_redirects_to_list(self):
        response = self.client.get("/contractors/export?format=docx", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/contractors", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
