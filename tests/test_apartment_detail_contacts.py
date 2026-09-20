import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "app" / "templates" / "apartment_detail.html").read_text(encoding="utf-8")
APARTMENTS_TEMPLATE = (ROOT / "app" / "templates" / "apartments.html").read_text(encoding="utf-8")
MODELS = (ROOT / "app" / "models.py").read_text(encoding="utf-8")
ROUTES = (ROOT / "app" / "routes.py").read_text(encoding="utf-8")
APP_INIT = (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")
STYLE = (ROOT / "app" / "static" / "style.css").read_text(encoding="utf-8")


class ApartmentDetailContactsTests(unittest.TestCase):
    def test_detail_shows_owner_and_phone_for_desktop_and_mobile(self):
        self.assertIn("ФИО собственника", TEMPLATE)
        self.assertIn("Номер телефона", TEMPLATE)
        self.assertIn("row.owner_names|join(', ') if row.owner_names else '—'", TEMPLATE)
        self.assertIn("row.phones|join(', ') if row.phones else '—'", TEMPLATE)

    def test_detail_fields_autosave_without_manual_save_button(self):
        self.assertIn('data-apartment-details-autosave="1"', TEMPLATE)
        self.assertIn("'X-Requested-With': 'XMLHttpRequest'", TEMPLATE)
        self.assertIn("field.value === 'unsold'", TEMPLATE)
        self.assertNotIn("Сохранить данные", TEMPLATE)
        self.assertIn("data-apartment-detail-sidebar", TEMPLATE)
        self.assertIn("data-apartment-history-card", TEMPLATE)
        self.assertIn("refreshRenderedSections(refreshSidebar)", TEMPLATE)
        self.assertIn("currentHistory.replaceWith(nextHistory)", TEMPLATE)
        self.assertIn("currentSidebar.replaceWith(nextSidebar)", TEMPLATE)
        self.assertIn("initApartmentDetailsAutosave()", TEMPLATE)
        self.assertNotIn("AbortController", TEMPLATE)

    def test_office_role_cannot_edit_apartment_comments_or_see_internal_status(self):
        self.assertIn("current_user.role not in ['viewer', 'office']", TEMPLATE)
        self.assertIn("current_user.role not in ['viewer', 'office']", APARTMENTS_TEMPLATE)
        self.assertIn("current_user.role != 'office'", TEMPLATE)
        self.assertIn("current_user.role != 'office'", APARTMENTS_TEMPLATE)
        self.assertIn("update_apartment_comment", TEMPLATE)
        self.assertIn("update_apartment_inspection_note", TEMPLATE)
        self.assertIn("update_apartment_po_status", TEMPLATE)
        self.assertIn("update_apartment_po_status", APARTMENTS_TEMPLATE)

    def test_apartment_comments_have_separate_labels(self):
        self.assertIn("Комментарий(передача)", TEMPLATE)
        self.assertIn("Комментарий(устранение замечаний)", TEMPLATE)
        self.assertIn("Комментарий(передача)", APARTMENTS_TEMPLATE)
        self.assertIn("Комментарий(устранение замечаний)", APARTMENTS_TEMPLATE)
        self.assertNotIn("row.mode == 'АПП' and current_user.role", TEMPLATE)
        self.assertNotIn("row.mode == 'не принята' and current_user.role", TEMPLATE)

    def test_correction_comment_is_internal_crm_field(self):
        self.assertIn("correction_comment = db.Column(db.Text", MODELS)
        self.assertIn("ALTER TABLE apartments ADD COLUMN correction_comment TEXT", APP_INIT)
        self.assertIn("apartment.correction_comment", ROUTES)
        update_start = ROUTES.index("def update_apartment_inspection_note")
        update_end = ROUTES.index("@bp.route(\"/apartments/<int:apartment_id>/comment\"", update_start)
        update_route = ROUTES[update_start:update_end]
        self.assertIn("item.correction_comment = note or None", update_route)
        self.assertNotIn("item.inspection_note = note or None", update_route)

    def test_unsold_apartment_detail_hides_inspection_row(self):
        self.assertIn("row.mode != 'не продана'", TEMPLATE)
        self.assertNotIn("Для непроданной квартиры осмотр фиксируется автоматически", TEMPLATE)

    def test_inspection_reset_hover_matches_save_button_green(self):
        start = STYLE.index(".apartment-inspection-reset-btn:hover")
        end = STYLE.index(".apartment-detail-page .apartment-task-item:hover", start)
        rule = STYLE[start:end]

        self.assertIn(
            "background: linear-gradient(180deg, var(--peredacha-action-green) 0%, var(--peredacha-action-green-hover) 100%) !important;",
            rule,
        )
        self.assertIn("border-color: var(--peredacha-action-green-hover) !important;", rule)
        self.assertNotIn("var(--peredacha-action-green-dark)", rule)


if __name__ == "__main__":
    unittest.main()
