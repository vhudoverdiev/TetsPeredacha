import unittest

from flask import g

from config import Config
from app import create_app, db, login_manager
from app.models import (
    AppSetting,
    ChatMessage,
    Project,
    ROLE_ADMIN,
    ROLE_EXECUTOR,
    ROLE_MANAGER,
    ROLE_OFFICE,
    ROLE_SUPERVISOR,
    SiteErrorReport,
    User,
)


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "messenger-contracts-test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class MessengerContractsTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.previous_session_protection = login_manager.session_protection
        login_manager.session_protection = None
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        self.project = Project(name="Messenger project")
        self.admin = User(
            username="developer",
            full_name="Владимир Худовердиев",
            password_hash="unused",
            role=ROLE_ADMIN,
        )
        self.manager = User(username="manager-chat", full_name="Инженер", password_hash="unused", role=ROLE_MANAGER)
        self.supervisor = User(username="supervisor-chat", full_name="Начальник", password_hash="unused", role=ROLE_SUPERVISOR)
        self.office = User(username="office-chat", full_name="Офис", password_hash="unused", role=ROLE_OFFICE)
        self.worker = User(username="worker-chat", full_name="Рабочий", password_hash="unused", role=ROLE_EXECUTOR)
        db.session.add_all([self.project, self.admin, self.manager, self.supervisor, self.office, self.worker])
        db.session.commit()

        self.client = self.app.test_client()
        self.admin_client = self.app.test_client()
        self.office_client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        login_manager.session_protection = self.previous_session_protection

    def _login(self, user, client=None):
        client = client or self.client
        if hasattr(g, "_login_user"):
            delattr(g, "_login_user")
        with client.session_transaction() as session:
            session.clear()
            session["_user_id"] = str(user.id)
            session["_fresh"] = True
            session["session_version"] = int(user.session_version or 0)
            session["current_project_id"] = self.project.id

    def test_messenger_available_for_authenticated_roles(self):
        for user in (self.admin, self.manager, self.supervisor, self.office, self.worker):
            with self.subTest(role=user.role):
                client = self.app.test_client()
                self._login(user, client)
                response = client.get("/messenger/thread")
                self.assertEqual(response.status_code, 200)

    def test_messenger_can_be_disabled_from_site_settings(self):
        db.session.add(AppSetting(key="enable_messenger", value="0"))
        db.session.commit()

        self._login(self.office, self.office_client)

        response = self.office_client.get("/messenger/thread")

        self.assertEqual(response.status_code, 403)

    def test_user_can_chat_with_developer_and_developer_sees_unread(self):
        self._login(self.office, self.office_client)
        response = self.office_client.post("/messenger/send", data={"body": "Нужна помощь"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(ChatMessage.query.count(), 1)

        self._login(self.admin, self.admin_client)
        thread = self.admin_client.get(f"/messenger/thread?user_id={self.office.id}").get_json()

        self.assertEqual(thread["messages"][0]["body"], "Нужна помощь")
        self.assertEqual(thread["messages"][0]["sender"], "Офис")
        office_row = next(user for user in thread["users"] if user["id"] == self.office.id)
        self.assertEqual(office_row["unread"], 1)

    def test_developer_reply_to_error_report_appears_in_user_appeals(self):
        report = SiteErrorReport(
            project=self.project,
            user=self.office,
            kind="user",
            message="Не открывается страница",
            page_url="/apartments",
            status="new",
        )
        db.session.add(report)
        db.session.commit()

        self._login(self.admin, self.admin_client)
        response = self.admin_client.post(
            f"/site-errors/{report.id}/reply",
            data={"reply": "Проверил, теперь работает."},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        db.session.refresh(report)
        self.assertEqual(report.status, "closed")
        self.assertEqual(report.developer_reply, "Проверил, теперь работает.")
        self.assertIsNone(report.user_reply_read_at)

        self._login(self.office, self.office_client)
        thread = self.office_client.get("/messenger/thread").get_json()

        self.assertEqual(thread["error_replies"][0]["reply"], "Проверил, теперь работает.")
        self.assertFalse(thread["error_replies"][0]["read"])
        self.assertGreaterEqual(thread["unread_count"], 1)

        read_response = self.office_client.post("/messenger/error-replies/read")
        self.assertEqual(read_response.status_code, 200)
        db.session.refresh(report)
        self.assertIsNotNone(report.user_reply_read_at)
