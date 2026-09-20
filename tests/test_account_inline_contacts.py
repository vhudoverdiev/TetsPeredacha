import unittest
from pathlib import Path

from config import Config
from app import create_app, db
from app.models import ROLE_ADMIN, ROLE_MANAGER, User


ROOT = Path(__file__).resolve().parents[1]


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "account-inline-contacts-test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class AccountInlineContactsTests(unittest.TestCase):
    def test_contact_inputs_are_embedded_in_profile_rows(self):
        template = (ROOT / "app" / "templates" / "account.html").read_text(encoding="utf-8")

        self.assertIn("account-profile-edit-list", template)
        profile_form = template.split('<form class="account-contact-form', 1)[1].split("</form>", 1)[0]
        self.assertIn('data-account-autosave="1"', template)
        self.assertIn('<dl class="account-profile-list account-profile-edit-list">', profile_form)
        self.assertIn('id="accountFullName"', profile_form)
        self.assertIn('id="accountEmail"', profile_form)
        self.assertIn('id="accountPhone"', profile_form)
        self.assertNotIn("Сохранить контакты", profile_form)
        self.assertIn("X-Requested-With", template)
        self.assertNotIn('class="mb-3"', profile_form)
        self.assertIn("let saving = false", template)
        self.assertIn("saveAgain = true", template)
        self.assertIn("const saveUrl = form.getAttribute('action') || window.location.href", template)
        self.assertIn("fetch(saveUrl", template)
        self.assertNotIn("fetch(form.action", template)
        self.assertIn("if (!response.ok || data.ok === false)", template)
        self.assertIn("navigator.sendBeacon", template)
        self.assertNotIn("AbortController", template)
        self.assertIn("current_user.role == ROLE_ADMIN", template)
        self.assertIn('name="current_password"', template)
        self.assertIn('name="new_password"', template)
        self.assertIn('name="confirm_password"', template)


class AccountAutosaveContactsTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(username="autosave-user", role=ROLE_MANAGER, captcha_disabled=True)
        self.user.set_password("Strong-test-password-2026!")
        db.session.add(self.user)
        db.session.commit()
        self.client = self.app.test_client()
        self.client.post("/login", data={"username": self.user.username, "password": "Strong-test-password-2026!"})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_account_contacts_autosave_returns_json_without_redirect(self):
        response = self.client.post(
            "/account",
            data={
                "action": "update_contacts",
                "full_name": "Иванов Иван Иванович",
                "email": "ivanov@example.test",
                "phone": "8 900 000-00-00",
            },
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": True, "message": "Контакты сохранены."})
        updated = db.session.get(User, self.user.id)
        self.assertEqual(updated.full_name, "Иванов Иван Иванович")
        self.assertEqual(updated.email, "ivanov@example.test")
        self.assertEqual(updated.phone, "8 900 000-00-00")

    def test_account_hides_role_for_non_developer(self):
        response = self.client.get("/account")

        html = response.get_data(as_text=True)
        self.assertNotIn("<dt>Роль</dt>", html)
        self.assertNotIn("Инженер", html)

    def test_account_shows_role_for_developer(self):
        self.user.role = ROLE_ADMIN
        db.session.commit()

        response = self.client.get("/account")

        html = response.get_data(as_text=True)
        self.assertIn("<dt>Роль</dt>", html)
        self.assertIn("Разработчик", html)

    def test_account_password_change_updates_current_user_password(self):
        response = self.client.post(
            "/account",
            data={
                "action": "change_password",
                "current_password": "Strong-test-password-2026!",
                "new_password": "Another-strong-password-2026!",
                "confirm_password": "Another-strong-password-2026!",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        updated = db.session.get(User, self.user.id)
        self.assertFalse(updated.check_password("Strong-test-password-2026!"))
        self.assertTrue(updated.check_password("Another-strong-password-2026!"))


if __name__ == "__main__":
    unittest.main()
