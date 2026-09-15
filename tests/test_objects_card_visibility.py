import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
