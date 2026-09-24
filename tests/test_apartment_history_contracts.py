import unittest

from app import create_app, db, login_manager
from app.models import Apartment, ChangeLog, Project, ROLE_ADMIN, User
from app.routes import _build_change_history_entry
from config import Config


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "apartment-history-contracts-test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ApartmentHistoryContractsTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.previous_session_protection = login_manager.session_protection
        login_manager.session_protection = None
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        self.project = Project(name="Apartment history QA")
        self.user = User(
            username="apartment-history-admin",
            password_hash="unused",
            role=ROLE_ADMIN,
            all_projects_access=True,
        )
        self.apartment = Apartment(
            project=self.project,
            apartment_number="1",
            owner_name="Старый собственник",
            phone="+7 900 000-00-00",
            finishing_type="Черновая",
        )
        db.session.add_all([self.project, self.user, self.apartment])
        db.session.commit()

        self.client = self.app.test_client()
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

    def _change_field_names(self):
        return {
            change.field_name
            for change in ChangeLog.query.filter_by(action="apartment_field_update").all()
        }

    def test_detail_fields_are_logged_and_rendered_with_specific_history_labels(self):
        response = self.client.post(
            f"/apartments/{self.apartment.id}/details",
            data={
                "owner_name": "Новый собственник",
                "phone": "+7 900 111-22-33",
                "finishing_type": "Белая",
                "mode": "app",
            },
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {"owner_name", "phone", "finishing_type", "apartment_mode"},
            self._change_field_names(),
        )

        page = self.client.get(f"/apartments/{self.apartment.id}").get_data(as_text=True)
        self.assertIn("ФИО собственника изменено", page)
        self.assertIn("Номер телефона изменён", page)
        self.assertIn("Отделка изменена", page)
        self.assertIn("Режим помещения изменён", page)
        self.assertNotIn("Комментарий помещения изменён: было «Старый собственник»", page)

    def test_inspection_status_and_date_are_logged_and_return_history_entries(self):
        status_response = self.client.post(
            f"/apartments/{self.apartment.id}/inspection-status",
            data={"inspection_status": "was"},
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
        )

        self.assertEqual(status_response.status_code, 200)
        status_summary = status_response.get_json()["history_entry"]["summary"]
        self.assertIn("Статус осмотра помещения изменён", status_summary)
        self.assertIn("был «Не был»", status_summary)
        old_date_label = status_response.get_json()["inspection_date_label"]

        date_response = self.client.post(
            f"/apartments/{self.apartment.id}/inspection-date",
            data={"inspection_date": "2026-09-15"},
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
        )

        self.assertEqual(date_response.status_code, 200)
        self.assertEqual(
            "Дата осмотра помещения изменена: была «%s», стала «15.09.2026»."
            % old_date_label,
            date_response.get_json()["history_entry"]["summary"].replace("15 сентября 2026", "15.09.2026"),
        )
        self.assertIn("apartment_inspection_status", self._change_field_names())
        self.assertIn("apartment_inspection_date", self._change_field_names())

    def test_new_apartment_history_fields_are_rendered_in_russian(self):
        cases = [
            (
                "addendum_status",
                "needed",
                "signed",
                "Статус доп. соглашения изменён: был «Не подписано», стал «Подписано».",
            ),
            (
                "app_deadline_status",
                "normal",
                "no_remarks",
                "Статус АПП изменён: был «Есть замечания», стал «Без замечаний».",
            ),
            (
                "deadline_date",
                "2026-09-16",
                "2026-09-25",
                "Дата подписания АПП изменена: была «16 сентября 2026», стала «25 сентября 2026».",
            ),
            (
                "app_deadline_date",
                "2026-11-15",
                "2026-12-01",
                "Срок устранения замечаний изменён: был «15 ноября 2026», стал «1 декабря 2026».",
            ),
            (
                "addendum_signed_date",
                "",
                "2026-09-24",
                "Дата подписания доп. соглашения изменена: была «не задана», стала «24 сентября 2026».",
            ),
        ]

        for field_name, old_value, new_value, expected_summary in cases:
            with self.subTest(field_name=field_name):
                change = ChangeLog(
                    action="apartment_field_update",
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value,
                    user=self.user,
                )
                entry = _build_change_history_entry(change)
                self.assertEqual(entry["summary"], expected_summary)
                self.assertNotIn(field_name, entry["summary"])
                if old_value:
                    self.assertNotIn(old_value, entry["summary"])
                self.assertNotIn(new_value, entry["summary"])


if __name__ == "__main__":
    unittest.main()
