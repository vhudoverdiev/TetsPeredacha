import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "app" / "templates" / "apartment_detail.html").read_text(encoding="utf-8")
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
