import unittest

from config import Config
from app import create_app, db, login_manager
from app.models import (
    Apartment,
    Project,
    ROLE_ADMIN,
    STATUS_DONE,
    STATUS_NOT_STARTED,
    Task,
    User,
    WorkPoint,
)


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "task-recognition-po-contracts-test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class TaskRecognitionPoContractsTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.previous_session_protection = login_manager.session_protection
        login_manager.session_protection = None
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.project = Project(name="Recognition PO project")
        db.session.add(self.project)
        db.session.flush()
        self.apartment = Apartment(project=self.project, apartment_number="59")
        self.point = WorkPoint(point_number="16", short_name="Разнорабочие", source_sheet_name="manual")
        self.old_task = Task(
            source_uid="recognition-po-old",
            project=self.project,
            apartment=self.apartment,
            work_point=self.point,
            description="Старое замечание",
            source_cell_value="Старое замечание",
            status=STATUS_NOT_STARTED,
            is_done=False,
        )
        self.admin = User(username="admin", role=ROLE_ADMIN, is_active=True, captcha_disabled=True)
        self.admin.set_password("correct-password")
        self.admin.set_project_access([self.project.id], all_projects=False)
        db.session.add_all([self.apartment, self.point, self.old_task, self.admin])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        login_manager.session_protection = self.previous_session_protection

    def _login(self):
        response = self.client.post(
            "/login",
            data={"username": self.admin.username, "password": "correct-password"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as sess:
            sess["current_project_id"] = self.project.id

    def test_po_mode_saves_all_rows_and_completes_previous_open_tasks(self):
        self._login()

        response = self.client.post(
            "/tasks/recognition",
            data={
                "action": "save",
                "confirm_import": "1",
                "po_mode": "1",
                "act_count": "1",
                "act_0_filename": "po.pdf",
                "act_0_template_ok": "1",
                "act_0_project_ok": "1",
                "act_0_apartment_id": str(self.apartment.id),
                "act_0_inspection_date": "2026-09-17",
                "act_0_row_count": "1",
                "act_0_row_0_point": "16",
                "act_0_row_0_description": "Новое замечание после ПО",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        db.session.refresh(self.old_task)
        self.assertEqual(self.old_task.status, STATUS_DONE)
        new_task = Task.query.filter(Task.description == "Новое замечание после ПО").one()
        self.assertEqual(new_task.status, STATUS_NOT_STARTED)
        self.assertEqual(new_task.work_point.point_number, "16")


if __name__ == "__main__":
    unittest.main()
