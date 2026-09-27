import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "app" / "templates" / "apartment_detail.html").read_text(encoding="utf-8")
APARTMENTS_TEMPLATE = (ROOT / "app" / "templates" / "apartments.html").read_text(encoding="utf-8")
MODELS = (ROOT / "app" / "models.py").read_text(encoding="utf-8")
ROUTES = (ROOT / "app" / "routes.py").read_text(encoding="utf-8")
APP_INIT = (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")
STYLE = (ROOT / "app" / "static" / "style.css").read_text(encoding="utf-8")
SCRIPT = (ROOT / "app" / "static" / "script.js").read_text(encoding="utf-8")


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

    def test_apartment_comment_display_controls_are_not_part_of_editor_header(self):
        comment_display = TEMPLATE.split('data-apartment-comment-display', 1)[1].split("</div>", 1)[0]
        note_display = TEMPLATE.split('data-apartment-inspection-note-display', 1)[1].split("</div>", 1)[0]
        comment_form_head = TEMPLATE.split('for="apartment-comment-', 1)[1].split("</div>", 1)[0]
        note_form_head = TEMPLATE.split('for="inspection-note-', 1)[1].split("</div>", 1)[0]

        self.assertIn('data-clear-note-form="apartment-comment-form-{{ apartment.id }}"', comment_display)
        self.assertIn("{% if not has_manual_comment %} hidden{% endif %}", comment_display)
        self.assertIn('data-clear-note-form="inspection-note-form-{{ apartment.id }}"', note_display)
        self.assertIn("{% if not has_inspection_comment %} hidden{% endif %}", note_display)
        self.assertNotIn("data-clear-note-button", comment_form_head)
        self.assertNotIn("data-clear-note-button", note_form_head)
        self.assertIn('id="apartment-comment-form-{{ apartment.id }}"', TEMPLATE)
        self.assertIn('id="inspection-note-form-{{ apartment.id }}"', TEMPLATE)
        self.assertIn("manual_comment_text not in ['-', '—']", TEMPLATE)
        self.assertIn("inspection_comment_text not in ['-', '—']", TEMPLATE)

    def test_apartment_comment_display_is_plain_and_has_no_autosave_caption(self):
        note_rule = STYLE.split("html body.app-body .apartment-detail-page .apartment-data-note > p {", 1)[1].split("}", 1)[0]

        self.assertIn("font-weight: 400 !important;", note_rule)
        self.assertNotIn("Сохраняется автоматически", STYLE)
        self.assertIn("syncApartmentNoteClearButton", SCRIPT)
        self.assertIn("button.getAttribute('data-clear-note-form')", SCRIPT)
        self.assertIn("normalizedValue === '-' || normalizedValue === '—'", SCRIPT)

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

    def test_inspection_date_picker_stacks_above_reset_action(self):
        controls_selector = (
            "html body.app-body .apartment-detail-page "
            ".apartment-compact-control-row:has([data-apartment-inspection-display]) "
            ".apartment-inline-controls {"
        )
        controls_start = STYLE.index(controls_selector)
        controls_rule = STYLE[controls_start:STYLE.index("}", controls_start)]
        input_selector = (
            "html body.app-body .apartment-detail-page "
            ".apartment-compact-control-row:has([data-apartment-inspection-display]) "
            ".apartment-inspection-date-form .form-control {"
        )
        input_start = STYLE.index(input_selector)
        input_rule = STYLE[input_start:STYLE.index("}", input_start)]

        self.assertIn("flex-direction: column !important;", controls_rule)
        self.assertIn("justify-self: end !important;", controls_rule)
        self.assertIn("width: 8.45rem !important;", controls_rule)
        self.assertIn("font-size: .72rem !important;", input_rule)
        self.assertIn("min-height: 2rem !important;", input_rule)

    def test_app_dates_refresh_display_after_async_save(self):
        self.assertIn("data-apartment-app-signed-display", TEMPLATE)
        self.assertIn("data-apartment-app-deadline-display", TEMPLATE)
        self.assertIn("document.querySelectorAll('[data-apartment-app-signed-display]')", SCRIPT)
        self.assertIn("document.querySelectorAll('[data-apartment-app-deadline-display]')", SCRIPT)
        self.assertIn("appDeadlineInput.value = data.app_deadline_date || '';", SCRIPT)

    def test_avr_date_autosave_keeps_current_status_and_refreshes_display(self):
        self.assertIn("form.classList.contains('apartment-avr-form')", SCRIPT)
        self.assertIn('button[name="avr_status"].btn-primary', SCRIPT)
        self.assertIn("formData.set('avr_status', activeAvrButton.value || '')", SCRIPT)
        self.assertIn("document.querySelectorAll('[data-apartment-avr-display]')", SCRIPT)
        self.assertIn("signedDateInput.value = data.avr_signed_date || '';", SCRIPT)

    def test_addendum_status_buttons_keep_text_on_one_line(self):
        selector = (
            'html body.app-body .apartment-detail-page '
            '.apartment-addendum-form button[name="addendum_status"]'
        )
        start = STYLE.index(selector)
        rule = STYLE[start:STYLE.index("}", start)]

        self.assertIn("font-size: .74rem !important;", rule)
        self.assertIn("white-space: nowrap !important;", rule)

    def test_addendum_row_matches_avr_date_control_pattern(self):
        self.assertIn('name="addendum_signed_date"', TEMPLATE)
        self.assertIn('class="apartment-addendum-status-actions"', TEMPLATE)
        self.assertNotIn("apartment-addendum-date-badge", TEMPLATE)
        self.assertIn("activeAddendumButton", SCRIPT)
        self.assertIn("formData.set('addendum_status', activeAddendumButton.value || '')", SCRIPT)
        self.assertIn("document.querySelectorAll('[data-apartment-addendum-display]')", SCRIPT)
        self.assertIn("signedDateInput.value = data.addendum_signed_date || '';", SCRIPT)


if __name__ == "__main__":
    unittest.main()
