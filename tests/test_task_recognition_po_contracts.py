import hashlib
import unittest

from config import Config
from app import create_app, db, login_manager
from app.models import (
    Apartment,
    Project,
    ROLE_ADMIN,
    STATUS_DONE,
    STATUS_CONCESSION,
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
        self.point_1 = WorkPoint(point_number="1", short_name="Пункт 1", source_sheet_name="manual")
        self.point_10 = WorkPoint(point_number="10", short_name="Вентиляция", source_sheet_name="manual")
        self.point = WorkPoint(point_number="16", short_name="Разнорабочие", source_sheet_name="manual")
        self.point_25 = WorkPoint(point_number="25", short_name="Прочее", source_sheet_name="manual")
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
        username_suffix = hashlib.sha1(self._testMethodName.encode("utf-8")).hexdigest()[:10]
        self.admin = User(username=f"admin-{username_suffix}", role=ROLE_ADMIN, is_active=True, captcha_disabled=True)
        self.admin.set_password("correct-password")
        self.admin.set_project_access([self.project.id], all_projects=False)
        db.session.add_all([self.apartment, self.point_1, self.point_10, self.point, self.point_25, self.old_task, self.admin])
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

    def test_manual_single_form_requires_and_uses_selected_point(self):
        self._login()

        response = self.client.post(
            "/tasks/new",
            data={
                "add_mode": "manual",
                "manual_kind": "single",
                "apartment_id": str(self.apartment.id),
                "description": "Новое одиночное замечание",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Task.query.filter_by(description="Новое одиночное замечание").first())

        response = self.client.post(
            "/tasks/new",
            data={
                "add_mode": "manual",
                "manual_kind": "single",
                "apartment_id": str(self.apartment.id),
                "point_number": "10",
                "description": "Новое одиночное замечание",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, f"/apartments/{self.apartment.id}")
        task = Task.query.filter_by(description="Новое одиночное замечание").one()
        self.assertEqual(task.work_point.point_number, "10")

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
                "act_0_row_0_active": "1",
                "act_0_row_0_point": "16",
                "act_0_row_0_description": "Новое замечание после ПО",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, f"/apartments/{self.apartment.id}")
        db.session.refresh(self.old_task)
        self.assertEqual(self.old_task.status, STATUS_DONE)
        new_task = Task.query.filter(Task.description == "Новое замечание после ПО").one()
        self.assertEqual(new_task.status, STATUS_NOT_STARTED)
        self.assertEqual(new_task.work_point.point_number, "16")

    def test_manual_single_concession_marks_selected_existing_tasks_as_concession(self):
        self._login()

        response = self.client.post(
            "/tasks/new",
            data={
                "add_mode": "manual",
                "manual_kind": "single",
                "apartment_id": str(self.apartment.id),
                "point_number": "26",
                "description": "Выданы отступные ТМЦ",
                "concession_task_ids": [str(self.old_task.id)],
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        db.session.refresh(self.old_task)
        self.assertEqual(self.old_task.status, STATUS_CONCESSION)
        concession_task = Task.query.filter(Task.description == "Выданы отступные ТМЦ").one()
        self.assertEqual(concession_task.work_point.point_number, "26")

    def test_manual_act_concession_marks_selected_point_tasks_as_concession(self):
        self._login()

        response = self.client.post(
            "/tasks/new",
            data={
                "add_mode": "manual",
                "manual_kind": "act",
                "apartment_id": str(self.apartment.id),
                "description_26": "Выданы отступные по акту",
                "concession_point_numbers": ["16"],
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        db.session.refresh(self.old_task)
        self.assertEqual(self.old_task.status, STATUS_CONCESSION)
        concession_task = Task.query.filter(Task.description == "Выданы отступные по акту").one()
        self.assertEqual(concession_task.work_point.point_number, "26")

    def test_po_mode_keeps_identical_existing_remark_open(self):
        self._login()

        response = self.client.post(
            "/tasks/recognition",
            data={
                "action": "save",
                "confirm_import": "1",
                "po_mode": "1",
                "act_count": "1",
                "act_0_filename": "po-identical.pdf",
                "act_0_template_ok": "1",
                "act_0_project_ok": "1",
                "act_0_apartment_id": str(self.apartment.id),
                "act_0_row_count": "1",
                "act_0_row_0_active": "1",
                "act_0_row_0_point": "16",
                "act_0_row_0_description": "Старое замечание",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 200)
        db.session.refresh(self.old_task)
        self.assertEqual(self.old_task.status, STATUS_NOT_STARTED)
        self.assertEqual(Task.query.filter(Task.description == "Старое замечание").count(), 1)

    def test_po_mode_with_only_duplicate_rows_still_completes_other_previous_tasks(self):
        self._login()
        old_other = Task(
            source_uid="recognition-po-duplicate-old-other",
            project=self.project,
            apartment=self.apartment,
            work_point=self.point_25,
            description="Старое замечание другого пункта",
            status=STATUS_NOT_STARTED,
            is_done=False,
        )
        db.session.add(old_other)
        db.session.commit()

        response = self.client.post(
            "/tasks/recognition",
            data={
                "action": "save",
                "confirm_import": "1",
                "po_mode": "1",
                "act_count": "1",
                "act_0_filename": "po-only-duplicates.pdf",
                "act_0_template_ok": "1",
                "act_0_project_ok": "1",
                "act_0_apartment_id": str(self.apartment.id),
                "act_0_row_count": "1",
                "act_0_row_0_active": "1",
                "act_0_row_0_point": "16",
                "act_0_row_0_description": "Старое замечание",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        db.session.refresh(self.old_task)
        db.session.refresh(old_other)
        self.assertEqual(self.old_task.status, STATUS_NOT_STARTED)
        self.assertEqual(old_other.status, STATUS_DONE)
        self.assertEqual(Task.query.filter(Task.description == "Старое замечание").count(), 1)

    def test_save_ignores_recognition_rows_before_point_ten(self):
        self._login()

        response = self.client.post(
            "/tasks/recognition",
            data={
                "action": "save",
                "confirm_import": "1",
                "act_count": "1",
                "act_0_filename": "points.pdf",
                "act_0_template_ok": "1",
                "act_0_project_ok": "1",
                "act_0_apartment_id": str(self.apartment.id),
                "act_0_row_count": "2",
                "act_0_row_0_active": "1",
                "act_0_row_0_point": "1",
                "act_0_row_0_description": "Старый пункт не должен сохраниться",
                "act_0_row_1_active": "1",
                "act_0_row_1_point": "10",
                "act_0_row_1_description": "Пункт десять сохраняется",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, f"/apartments/{self.apartment.id}")
        self.assertIsNone(Task.query.filter(Task.description == "Старый пункт не должен сохраниться").one_or_none())
        saved_task = Task.query.filter(Task.description == "Пункт десять сохраняется").one()
        self.assertEqual(saved_task.work_point.point_number, "10")

    def test_auto_recognition_concession_marks_selected_point_tasks_as_concession(self):
        self._login()

        response = self.client.post(
            "/tasks/recognition",
            data={
                "action": "save",
                "confirm_import": "1",
                "act_count": "1",
                "act_0_filename": "concession.pdf",
                "act_0_template_ok": "1",
                "act_0_project_ok": "1",
                "act_0_apartment_id": str(self.apartment.id),
                "act_0_row_count": "1",
                "act_0_row_0_active": "1",
                "act_0_row_0_point": "26",
                "act_0_row_0_description": "Отступное из PDF",
                "act_0_concession_point_numbers": ["16"],
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        db.session.refresh(self.old_task)
        self.assertEqual(self.old_task.status, STATUS_CONCESSION)
        concession_task = Task.query.filter(Task.description == "Отступное из PDF").one()
        self.assertEqual(concession_task.work_point.point_number, "26")

    def test_save_allows_mismatched_project_when_manually_verified(self):
        self._login()

        blocked_response = self.client.post(
            "/tasks/recognition",
            data={
                "action": "save",
                "confirm_import": "1",
                "act_count": "1",
                "act_0_filename": "mismatch.pdf",
                "act_0_template_ok": "1",
                "act_0_project_ok": "0",
                "act_0_project_name": "Другой объект",
                "act_0_apartment_id": str(self.apartment.id),
                "act_0_row_count": "1",
                "act_0_row_0_active": "1",
                "act_0_row_0_point": "10",
                "act_0_row_0_description": "Ручная сверка без подтверждения",
            },
        )

        self.assertEqual(blocked_response.status_code, 200)
        self.assertIn("Сверьте ЖК".encode("utf-8"), blocked_response.data)
        self.assertIsNone(Task.query.filter_by(description="Ручная сверка без подтверждения").first())

        saved_response = self.client.post(
            "/tasks/recognition",
            data={
                "action": "save",
                "confirm_import": "1",
                "act_count": "1",
                "act_0_filename": "mismatch.pdf",
                "act_0_template_ok": "1",
                "act_0_project_ok": "0",
                "act_0_project_override": "1",
                "act_0_project_name": "Другой объект",
                "act_0_apartment_id": str(self.apartment.id),
                "act_0_row_count": "1",
                "act_0_row_0_active": "1",
                "act_0_row_0_point": "10",
                "act_0_row_0_description": "Ручная сверка подтверждена",
            },
            follow_redirects=False,
        )

        self.assertEqual(saved_response.status_code, 302)
        self.assertEqual(saved_response.location, f"/apartments/{self.apartment.id}")
        saved_task = Task.query.filter_by(description="Ручная сверка подтверждена").one()
        self.assertEqual(saved_task.apartment_id, self.apartment.id)
        self.assertEqual(saved_task.work_point.point_number, "10")

    def test_save_ignores_unchecked_recognition_rows_even_with_text_in_po_mode(self):
        self._login()

        response = self.client.post(
            "/tasks/recognition",
            data={
                "action": "save",
                "confirm_import": "1",
                "po_mode": "1",
                "act_count": "1",
                "act_0_filename": "unchecked.pdf",
                "act_0_template_ok": "1",
                "act_0_project_ok": "1",
                "act_0_apartment_id": str(self.apartment.id),
                "act_0_row_count": "2",
                "act_0_row_0_point": "16",
                "act_0_row_0_description": "Снятая строка не должна сохраниться",
                "act_0_row_1_active": "1",
                "act_0_row_1_point": "10",
                "act_0_row_1_description": "Отмеченная строка сохраняется",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, f"/apartments/{self.apartment.id}")
        self.assertIsNone(Task.query.filter(Task.description == "Снятая строка не должна сохраниться").one_or_none())
        saved_task = Task.query.filter(Task.description == "Отмеченная строка сохраняется").one()
        self.assertEqual(saved_task.work_point.point_number, "10")

    def test_auto_import_warns_to_enable_po_when_apartment_already_has_many_open_remarks(self):
        self._login()
        for index in range(5):
            db.session.add(Task(
                source_uid=f"recognition-po-many-{index}",
                project=self.project,
                apartment=self.apartment,
                work_point=self.point_10,
                description=f"Открытое замечание {index}",
                status=STATUS_NOT_STARTED,
                is_done=False,
            ))
        db.session.commit()

        response = self.client.post(
            "/tasks/recognition",
            data={
                "action": "save",
                "confirm_import": "1",
                "act_count": "1",
                "act_0_filename": "repeat.pdf",
                "act_0_template_ok": "1",
                "act_0_project_ok": "1",
                "act_0_apartment_id": str(self.apartment.id),
                "act_0_row_count": "1",
                "act_0_row_0_active": "1",
                "act_0_row_0_point": "10",
                "act_0_row_0_description": "Новое замечание без ПО",
            },
            follow_redirects=True,
        )

        html = response.get_data(as_text=True)
        self.assertIn("Поставьте кнопку ПО", html)
        self.assertIsNone(Task.query.filter(Task.description == "Новое замечание без ПО").one_or_none())

    def test_manual_act_po_completes_old_non_identical_and_keeps_identical_open(self):
        self._login()
        old_other = Task(
            source_uid="manual-po-old-other",
            project=self.project,
            apartment=self.apartment,
            work_point=self.point_10,
            description="Старое по вентиляции",
            status=STATUS_NOT_STARTED,
            is_done=False,
        )
        old_unmentioned_point = Task(
            source_uid="manual-po-old-unmentioned-point",
            project=self.project,
            apartment=self.apartment,
            work_point=self.point_25,
            description="Старое по пункту которого нет в новом акте",
            status=STATUS_NOT_STARTED,
            is_done=False,
        )
        db.session.add_all([old_other, old_unmentioned_point])
        db.session.commit()

        response = self.client.post(
            "/tasks/new",
            data={
                "add_mode": "manual",
                "manual_kind": "act",
                "apartment_id": str(self.apartment.id),
                "po_mode": "1",
                "description_10": "Новое по вентиляции",
                "description_16": "Старое замечание",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, f"/apartments/{self.apartment.id}")
        db.session.refresh(self.old_task)
        db.session.refresh(old_other)
        db.session.refresh(old_unmentioned_point)
        self.assertEqual(self.old_task.status, STATUS_NOT_STARTED)
        self.assertEqual(old_other.status, STATUS_DONE)
        self.assertEqual(old_unmentioned_point.status, STATUS_DONE)
        self.assertEqual(Task.query.filter(Task.description == "Старое замечание").count(), 1)
        new_task = Task.query.filter(Task.description == "Новое по вентиляции").one()
        self.assertEqual(new_task.status, STATUS_NOT_STARTED)

    def test_manual_act_warns_to_enable_po_for_three_points_when_existing_remarks_exist(self):
        self._login()
        self.old_task.status = STATUS_DONE
        self.old_task.is_done = True
        db.session.commit()

        response = self.client.post(
            "/tasks/new",
            data={
                "add_mode": "manual",
                "manual_kind": "act",
                "apartment_id": str(self.apartment.id),
                "description_10": "Первое новое",
                "description_16": "Второе новое",
                "description_25": "Третье новое",
            },
            follow_redirects=True,
        )

        html = response.get_data(as_text=True)
        self.assertIn("Поставьте кнопку ПО", html)
        self.assertIsNone(Task.query.filter(Task.description == "Первое новое").one_or_none())


if __name__ == "__main__":
    unittest.main()
