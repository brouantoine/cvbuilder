# Generated manually for the MVP seed template.

from django.db import migrations


def seed_simple_template(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")
    CVTemplate.objects.update_or_create(
        slug="modele-simple",
        defaults={
            "name": "Modèle simple",
            "description": "Un modèle gratuit compatible avec la génération DOCX.",
            "preview_image_url": "",
            "is_premium": False,
            "docx_filename": "modele_simple.docx",
        },
    )


def remove_simple_template(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")
    CVTemplate.objects.filter(slug="modele-simple").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("templates", "0002_add_docx_filename"),
    ]

    operations = [
        migrations.RunPython(seed_simple_template, remove_simple_template),
    ]
