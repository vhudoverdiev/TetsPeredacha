import unittest
from pathlib import Path

from config import Config
from app import create_app, db, login_manager
from app.models import ROLE_ADMIN, ROLE_GLAZIER, ROLE_MANAGER, ROLE_OFFICE, ROLE_PAINTER, Project, User


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "user-role-update-contracts-test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class UserRoleUpdateContractsTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.previous_session_protection = login_manager.session_protection
        login_manager.session_protection = None
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.project = Project(name="Role update project")
        db.session.add(self.project)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        login_manager.session_protection = self.previous_session_protection

    def _user(self, username, role=ROLE_MANAGER):
        user = User(
            username=username,
            role=role,
            is_active=True,
            captcha_disabled=True,
            project_id=self.project.id,
        )
        user.set_password("correct-password")
        db.session.add(user)
        db.session.commit()
        return user

    def _login(self, user):
        response = self.client.post(
            "/login",
            data={"username": user.username, "password": "correct-password"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

    def test_admin_can_update_another_users_role(self):
        admin = self._user("admin", ROLE_ADMIN)
        user = self._user("worker", ROLE_MANAGER)
        self._login(admin)

        response = self.client.post(
            f"/users/{user.id}/role",
            data={"role": ROLE_PAINTER},
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["role"], ROLE_PAINTER)
        self.assertEqual(db.session.get(User, user.id).role, ROLE_PAINTER)

    def test_users_page_role_select_has_resilient_autosave_handlers(self):
        script = Path("app/static/script.js").read_text(encoding="utf-8")

        self.assertIn("const saveRole = async () =>", script)
        self.assertIn("select.addEventListener('change', saveRole)", script)
        self.assertIn("select.addEventListener('input', saveRole)", script)
        self.assertIn("form.addEventListener('submit'", script)

    def test_admin_can_update_user_to_office_role(self):
        admin = self._user("admin-office", ROLE_ADMIN)
        user = self._user("worker-office", ROLE_MANAGER)
        self._login(admin)

        response = self.client.post(
            f"/users/{user.id}/role",
            data={"role": ROLE_OFFICE},
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["role"], ROLE_OFFICE)
        self.assertEqual(db.session.get(User, user.id).role, ROLE_OFFICE)

    def test_role_update_rejects_invalid_role(self):
        admin = self._user("admin-invalid", ROLE_ADMIN)
        user = self._user("worker-invalid", ROLE_MANAGER)
        self._login(admin)

        response = self.client.post(
            f"/users/{user.id}/role",
            data={"role": "owner"},
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["ok"])
        self.assertEqual(db.session.get(User, user.id).role, ROLE_MANAGER)

    def test_admin_cannot_update_own_role_from_users_table(self):
        admin = self._user("admin-self", ROLE_ADMIN)
        self._login(admin)

        response = self.client.post(
            f"/users/{admin.id}/role",
            data={"role": ROLE_GLAZIER},
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["ok"])
        self.assertEqual(db.session.get(User, admin.id).role, ROLE_ADMIN)

    def test_admin_cannot_update_another_admin_role_from_users_table(self):
        admin = self._user("admin-actor", ROLE_ADMIN)
        other_admin = self._user("admin-target", ROLE_ADMIN)
        self._login(admin)

        response = self.client.post(
            f"/users/{other_admin.id}/role",
            data={"role": ROLE_GLAZIER},
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["ok"])
        self.assertEqual(db.session.get(User, other_admin.id).role, ROLE_ADMIN)


if __name__ == "__main__":
    unittest.main()
