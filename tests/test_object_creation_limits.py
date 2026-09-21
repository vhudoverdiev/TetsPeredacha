import unittest

from config import Config
from app import create_app, db
from app.models import Project, ROLE_ADMIN, ROLE_MANAGER, User


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "object-creation-limit-test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ObjectCreationLimitTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def _create_user(self, username: str, role: str) -> User:
        user = User(username=username, role=role, all_projects_access=True, captcha_disabled=True)
        user.set_password("Strong-test-password-2026!")
        db.session.add(user)
        db.session.commit()
        return user

    def _login(self, username: str):
        return self.client.post(
            "/login",
            data={"username": username, "password": "Strong-test-password-2026!"},
            follow_redirects=False,
        )

    def _post_object(self, name: str):
        return self.client.post(
            "/objects/new",
            data={
                "name": name,
                "address": "",
                "technical_customer": "",
                "developer_name": "",
                "inn_kpp": "",
                "ogrn": "",
                "legal_address": "",
                "developer_director": "",
                "developer_representative": "",
                "developer_representative_phone": "",
                "has_apartments": "y",
                "has_commercial": "y",
            },
            follow_redirects=False,
        )

    def test_office_manager_can_create_only_one_object_per_day(self):
        manager = self._create_user("manager", ROLE_MANAGER)
        self._login(manager.username)

        first_response = self._post_object("Первый объект")
        self.assertEqual(first_response.status_code, 302)
        first_project = Project.query.filter_by(name="Первый объект").one()
        self.assertEqual(first_project.created_by_id, manager.id)

        second_response = self._post_object("Второй объект")
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(Project.query.filter_by(name="Второй объект").count(), 0)

        with self.client.session_transaction() as session:
            flashes = session.get("_flashes") or []
        self.assertIn(("warning", "Можно добавить только 1 объект в сутки."), flashes)

    def test_developer_is_not_limited_by_daily_object_count(self):
        admin = self._create_user("admin", ROLE_ADMIN)
        self._login(admin.username)

        self.assertEqual(self._post_object("Первый объект").status_code, 302)
        self.assertEqual(self._post_object("Второй объект").status_code, 302)
        self.assertEqual(Project.query.count(), 2)
