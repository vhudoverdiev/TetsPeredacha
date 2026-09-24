import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESKTOP_CSS = (ROOT / "app" / "static" / "desktop-only.css").read_text(encoding="utf-8")


class ObjectsCardVisibilityTests(unittest.TestCase):
    def test_sensitive_project_requisites_are_not_rendered_on_object_cards(self):
        template = (ROOT / "app" / "templates" / "objects.html").read_text(encoding="utf-8")

        description_block = template.split('<div class="object-description">', 1)[1].split("</div>", 1)[0]
        self.assertNotIn("ИНН/КПП", description_block)
        self.assertNotIn("ОГРН", description_block)
        self.assertNotIn("Юр. адрес", description_block)
        self.assertNotIn("Директор СЗ", description_block)
        self.assertNotIn("project.inn_kpp", description_block)
        self.assertNotIn("project.ogrn", description_block)
        self.assertNotIn("project.legal_address", description_block)
        self.assertNotIn("project.developer_director", description_block)

    def test_desktop_object_cards_render_three_per_row(self):
        self.assertIn(
            "html.desktop-like-pointer body.app-body:has(.objects-page) .objects-grid {\n"
            "  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;",
            DESKTOP_CSS,
        )
        self.assertIn(
            "@media (max-width: 1480px) {\n"
            "  html.desktop-like-pointer body.app-body:has(.objects-page) .objects-grid {\n"
            "    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;",
            DESKTOP_CSS,
        )


if __name__ == "__main__":
    unittest.main()
