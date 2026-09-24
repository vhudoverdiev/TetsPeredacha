import unittest
from datetime import date

from config import Config
from app import create_app, db, login_manager
from app.models import Apartment, Project, ROLE_ADMIN, STATUS_NOT_STARTED, Task, User, WorkPoint
from app.services.task_service import APP_DEADLINE_NORMAL, APP_DEADLINE_NO_REMARKS, AVR_STATUS_NEEDED, AVR_STATUS_SIGNED


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "apartment-app-status-test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ApartmentAppStatusTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.previous_session_protection = login_manager.session_protection
        login_manager.session_protection = None
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.project = Project(name="APP status project")
        self.user = User(username="app-status-admin", password_hash="unused", role=ROLE_ADMIN)
        self.apartment = Apartment(project=self.project, apartment_number="1", is_app_mode=True)
        db.session.add_all([self.project, self.user, self.apartment])
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

    def test_app_signed_date_sets_deadline_after_60_calendar_days(self):
        response = self.client.post(
            f"/apartments/{self.apartment.id}/app-status",
            data={
                "app_status": APP_DEADLINE_NORMAL,
                "app_signed_date": "2026-09-16",
                "app_deadline_manual": "0",
            },
        )

        self.assertEqual(response.status_code, 302)
        apartment = db.session.get(Apartment, self.apartment.id)
        self.assertEqual(apartment.deadline_date, date(2026, 9, 16))
        self.assertEqual(apartment.app_deadline_date, date(2026, 11, 15))
        self.assertEqual(apartment.remark_deadline_date, date(2026, 11, 15))
        self.assertEqual(apartment.app_deadline_status, APP_DEADLINE_NORMAL)
        self.assertEqual(apartment.avr_status, AVR_STATUS_NEEDED)

    def test_manual_deadline_overrides_calculated_deadline(self):
        response = self.client.post(
            f"/apartments/{self.apartment.id}/app-status",
            data={
                "app_status": APP_DEADLINE_NORMAL,
                "app_signed_date": "2026-09-16",
                "app_deadline_date": "2026-12-01",
                "app_deadline_manual": "1",
            },
        )

        self.assertEqual(response.status_code, 302)
        apartment = db.session.get(Apartment, self.apartment.id)
        self.assertEqual(apartment.deadline_date, date(2026, 9, 16))
        self.assertEqual(apartment.app_deadline_date, date(2026, 12, 1))
        self.assertEqual(apartment.remark_deadline_date, date(2026, 12, 1))

    def test_no_remarks_hides_avr_section(self):
        self.apartment.avr_status = AVR_STATUS_SIGNED
        self.apartment.avr_signed_date = date(2026, 10, 1)
        db.session.commit()

        response = self.client.post(
            f"/apartments/{self.apartment.id}/app-status",
            data={
                "app_status": APP_DEADLINE_NO_REMARKS,
                "app_signed_date": "2026-09-16",
                "app_deadline_manual": "0",
            },
        )

        self.assertEqual(response.status_code, 302)
        apartment = db.session.get(Apartment, self.apartment.id)
        self.assertEqual(apartment.app_deadline_status, APP_DEADLINE_NO_REMARKS)
        self.assertIsNone(apartment.app_deadline_date)
        self.assertIsNone(apartment.remark_deadline_date)
        self.assertEqual(apartment.avr_status, AVR_STATUS_NEEDED)
        self.assertIsNone(apartment.avr_signed_date)

        page = self.client.get(f"/apartments/{self.apartment.id}").get_data(as_text=True)
        self.assertIn("Без замечаний", page)
        self.assertNotIn("Изменить АВР", page)

    def test_dop_agreement_point_auto_marks_addendum_as_not_signed(self):
        point = WorkPoint(point_number="26", short_name="Отступное (ТМЦ)")
        task = Task(
            project=self.project,
            apartment=self.apartment,
            work_point=point,
            source_uid="dop-auto",
            description="Выдать ТМЦ",
            status=STATUS_NOT_STARTED,
        )
        db.session.add_all([point, task])
        db.session.commit()

        page = self.client.get(f"/apartments/{self.apartment.id}").get_data(as_text=True)

        self.assertIn("Доп.Соглашение", page)
        self.assertIn("Не подписано", page)

    def test_manual_addendum_none_overrides_dop_agreement_auto_status(self):
        point = WorkPoint(point_number="26", short_name="Отступное (ТМЦ)")
        task = Task(
            project=self.project,
            apartment=self.apartment,
            work_point=point,
            source_uid="dop-manual-none",
            description="Выдать ТМЦ",
            status=STATUS_NOT_STARTED,
        )
        db.session.add_all([point, task])
        db.session.commit()

        response = self.client.post(
            f"/apartments/{self.apartment.id}/addendum-status",
            data={"addendum_status": "none"},
        )

        self.assertEqual(response.status_code, 302)
        apartment = db.session.get(Apartment, self.apartment.id)
        self.assertEqual(apartment.addendum_status, "none")
        self.assertTrue(apartment.addendum_status_manual)
        page = self.client.get(f"/apartments/{self.apartment.id}").get_data(as_text=True)
        self.assertIn("Доп.Соглашение", page)
        self.assertIn(">Нет<", page)

    def test_manual_addendum_signed_is_saved(self):
        response = self.client.post(
            f"/apartments/{self.apartment.id}/addendum-status",
            data={"addendum_status": "signed"},
        )

        self.assertEqual(response.status_code, 302)
        apartment = db.session.get(Apartment, self.apartment.id)
        self.assertEqual(apartment.addendum_status, "signed")
        self.assertTrue(apartment.addendum_status_manual)

    def test_non_app_apartment_cannot_have_addendum(self):
        self.apartment.is_app_mode = False
        point = WorkPoint(point_number="26", short_name="Отступное (ТМЦ)")
        task = Task(
            project=self.project,
            apartment=self.apartment,
            work_point=point,
            source_uid="dop-non-app",
            description="Выдать ТМЦ",
            status=STATUS_NOT_STARTED,
        )
        db.session.add_all([point, task])
        db.session.commit()

        page = self.client.get(f"/apartments/{self.apartment.id}").get_data(as_text=True)
        self.assertNotIn("Изменить доп. соглашение", page)

        response = self.client.post(
            f"/apartments/{self.apartment.id}/addendum-status",
            data={"addendum_status": "signed"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
