import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AccountInlineContactsTests(unittest.TestCase):
    def test_contact_inputs_are_embedded_in_profile_rows(self):
        template = (ROOT / "app" / "templates" / "account.html").read_text(encoding="utf-8")

        self.assertIn("account-profile-edit-list", template)
        profile_form = template.split('<form class="account-contact-form', 1)[1].split("</form>", 1)[0]
        self.assertIn('<dl class="account-profile-list account-profile-edit-list">', profile_form)
        self.assertIn('id="accountFullName"', profile_form)
        self.assertIn('id="accountEmail"', profile_form)
        self.assertIn('id="accountPhone"', profile_form)
        self.assertNotIn('class="mb-3"', profile_form)


if __name__ == "__main__":
    unittest.main()
