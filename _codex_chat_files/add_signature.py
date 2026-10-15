from pathlib import Path
def edit(path, old, new):
 p=Path(path);s=p.read_bytes();assert old.encode() in s,path;p.write_bytes(s.replace(old.encode(),new.encode(),1))
edit('app/models.py','    developer_director = db.Column(db.String(255), nullable=True)','    signature_image = db.Column(db.Text().with_variant(__import__("sqlalchemy.dialects.mysql", fromlist=["LONGTEXT"]).LONGTEXT(), "mysql"), nullable=True)\n    developer_director = db.Column(db.String(255), nullable=True)')
edit('app/__init__.py','                if "technical_customer" not in project_columns:', '                if "signature_image" not in project_columns:\n                    db.session.execute(text("ALTER TABLE projects ADD COLUMN signature_image LONGTEXT"))\n                if "technical_customer" not in project_columns:')
edit('app/forms.py','from wtforms.validators import DataRequired, Length, Optional','from wtforms.validators import DataRequired, Length, Optional, ValidationError')
edit('app/forms.py','class ProjectForm(FlaskForm):','''class ProjectForm(FlaskForm):
    signature = FileField("Подпись", validators=[FileAllowed(["png", "jpg", "jpeg"], "Загрузите PNG или JPEG.")])
    remove_signature = BooleanField("Удалить загруженную подпись")

    def validate_signature(self, field):
        if not field.data:
            return
        from app.services.project_signature import normalize_signature
        try:
            self.signature_image_data = normalize_signature(field.data)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
''')
edit('app/routes.py','            created_by_id=current_user.id,\n        )','            created_by_id=current_user.id,\n            signature_image=getattr(form, "signature_image_data", None),\n        )')
edit('app/routes.py','        project.name = form.name.data.strip()','        if getattr(form, "signature_image_data", None):\n            project.signature_image = form.signature_image_data\n        elif form.remove_signature.data:\n            project.signature_image = None\n        project.name = form.name.data.strip()')
# Pass project to edit page, including validation errors.
p=Path('app/routes.py');s=p.read_bytes();s=s.replace(b'form=form, form_title="', b'form=form, form_title="') # preserve existing lines
s=s.replace('form=form, form_title="Редактировать объект"'.encode(),'form=form, project=project, form_title="Редактировать объект"'.encode());p.write_bytes(s)
edit('app/templates/object_form.html','<form method="post">','<form method="post" enctype="multipart/form-data">')
edit('app/templates/object_form.html','      <div class="object-type-box mb-3">','''      <div class="mb-3">
        {{ form.signature.label(class="form-label") }}
        {{ form.signature(class="form-control", accept="image/png,image/jpeg", aria_describedby="signature-help") }}
        <div id="signature-help" class="form-text">PNG или JPEG до 5 МБ. Подпись гендиректора для претензий этого объекта. Новый файл заменит текущую подпись.</div>
        {% for error in form.signature.errors %}<div class="text-danger" role="alert">{{ error }}</div>{% endfor %}
        {% if project is defined and project.signature_image %}
        <img src="data:image/png;base64,{{ project.signature_image }}" alt="Текущая подпись объекта" class="img-fluid d-block my-2" style="max-width: 240px; max-height: 100px;">
        <label class="form-check">{{ form.remove_signature(class="form-check-input") }} {{ form.remove_signature.label.text }}</label>
        {% endif %}
      </div>
      <div class="object-type-box mb-3">''')
edit('app/services/contractor_claim_docx.py','import re\n','import re\nimport base64\nfrom io import BytesIO\nfrom PIL import Image\n')
edit('app/services/contractor_claim_docx.py','        archive.write(STAMP_IMAGE_PATH, "word/media/image1.png")','        if project.signature_image:\n            archive.writestr("word/media/image1.png", base64.b64decode(project.signature_image))\n        else:\n            archive.write(STAMP_IMAGE_PATH, "word/media/image1.png")')
edit('app/services/contractor_claim_docx.py','_signature_cell(_stamp_inline_paragraph(),','_signature_cell(_stamp_inline_paragraph(project.signature_image),')
edit('app/services/contractor_claim_docx.py','def _stamp_inline_paragraph() -> str:\n    return (','''def _stamp_inline_paragraph(signature_image: str | None = None) -> str:
    cx, cy = 950000, 701000
    if signature_image:
        with Image.open(BytesIO(base64.b64decode(signature_image))) as image:
            scale = min(cx / image.width, cy / image.height)
            cx, cy = round(image.width * scale), round(image.height * scale)
    return (''')
p=Path('app/services/contractor_claim_docx.py');s=p.read_bytes().replace(b"        '<wp:extent cx=\"950000\" cy=\"701000\"/>'",b"        f'<wp:extent cx=\"{cx}\" cy=\"{cy}\"/>'").replace(b"        '<pic:spPr bwMode=\"auto\"><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"950000\" cy=\"701000\"/></a:xfrm>'",b"        f'<pic:spPr bwMode=\"auto\"><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"{cx}\" cy=\"{cy}\"/></a:xfrm>'");p.write_bytes(s)
