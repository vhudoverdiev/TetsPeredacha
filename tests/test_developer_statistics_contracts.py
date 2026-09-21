from datetime import datetime
import unittest

from config import Config
from app import create_app, db
from app.models import ROLE_ADMIN, SiteVisit, User
from app.routes import _build_developer_statistics_context


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "developer-statistics-contracts-test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class DeveloperStatisticsContractsTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_statistics_totals_include_guest_request_ips_and_unique_visits_are_unique_ips(self):
        user = User(username="stats-admin", role=ROLE_ADMIN, password_hash="unused")
        db.session.add(user)
        db.session.flush()
        visits = [
            SiteVisit(
                user=user,
                ip_address="203.0.113.10",
                endpoint="main.dashboard",
                path="/",
                method="GET",
                status_code=200,
                is_authenticated=True,
                visit_kind="request",
                created_at=datetime(2026, 8, 4, 10, 0),
            ),
            SiteVisit(
                user=user,
                ip_address="203.0.113.10",
                endpoint="main.apartments",
                path="/apartments",
                method="GET",
                status_code=200,
                is_authenticated=True,
                visit_kind="request",
                created_at=datetime(2026, 8, 4, 10, 5),
            ),
            SiteVisit(
                ip_address="198.51.100.25",
                endpoint="auth.login",
                path="/login",
                method="GET",
                status_code=200,
                is_authenticated=False,
                visit_kind="request",
                created_at=datetime(2026, 8, 4, 10, 10),
            ),
            SiteVisit(
                ip_address="198.51.100.25",
                endpoint="auth.login",
                path="/login",
                method="GET",
                status_code=200,
                is_authenticated=False,
                visit_kind="request",
                created_at=datetime(2026, 8, 4, 10, 15),
            ),
            SiteVisit(
                ip_address="192.0.2.77",
                endpoint="analytics_tab_open",
                path="/",
                method="TAB",
                status_code=204,
                is_authenticated=False,
                visit_kind="tab_open",
                tab_id="tab-not-counted-as-request",
                created_at=datetime(2026, 8, 4, 10, 20),
            ),
        ]
        db.session.add_all(visits)
        db.session.commit()

        with self.app.test_request_context("/developer/statistics?start_date=2026-08-04&end_date=2026-08-04"):
            context = _build_developer_statistics_context()

        self.assertEqual(context["total_visits"], 4)
        self.assertEqual(context["unique_visitors"], 2)
        self.assertEqual(context["unique_ips"], 2)
        self.assertEqual(
            {item["ip_address"]: item["hits"] for item in context["top_ips"]},
            {"203.0.113.10": 2, "198.51.100.25": 2},
        )

    def test_user_guest_groups_are_built_from_whole_period_not_only_recent_visits(self):
        active_user = User(username="active", full_name="Активный Пользователь", role=ROLE_ADMIN, password_hash="unused")
        older_user = User(username="older", full_name="Старый Пользователь", role=ROLE_ADMIN, password_hash="unused")
        db.session.add_all([active_user, older_user])
        db.session.flush()

        visits = [
            SiteVisit(
                user=older_user,
                ip_address="203.0.113.50",
                endpoint="main.dashboard",
                path="/",
                method="GET",
                status_code=200,
                is_authenticated=True,
                visit_kind="request",
                created_at=datetime(2026, 8, 4, 8, 0),
            )
        ]
        visits.extend(
            SiteVisit(
                user=active_user,
                ip_address="203.0.113.10",
                endpoint="main.dashboard",
                path="/",
                method="GET",
                status_code=200,
                is_authenticated=True,
                visit_kind="request",
                created_at=datetime(2026, 8, 4, 10, minute % 60),
            )
            for minute in range(260)
        )
        db.session.add_all(visits)
        db.session.commit()

        with self.app.test_request_context("/developer/statistics/visits?start_date=2026-08-04&end_date=2026-08-04"):
            context = _build_developer_statistics_context()

        labels = [group["label"] for group in context["visitor_groups"]]
        self.assertIn("Активный Пользователь", labels)
        self.assertIn("Старый Пользователь", labels)

    def test_request_visit_is_persisted_before_response_returns(self):
        client = self.app.test_client()

        response = client.get(
            "/login",
            environ_base={"REMOTE_ADDR": "198.51.100.44"},
            headers={"User-Agent": "StatsPersistenceTest/1.0"},
        )

        self.assertEqual(response.status_code, 200)
        visit = SiteVisit.query.filter_by(ip_address="198.51.100.44", visit_kind="request").one()
        self.assertEqual(visit.path, "/login")
        self.assertFalse(visit.is_authenticated)


if __name__ == "__main__":
    unittest.main()
