# Generated manually to keep the public gallery focused on configured designs.

from django.db import migrations


PUBLIC_TEMPLATE_SLUGS = [
    "modele-simple",
    "modele-classique",
    "modele-moderne",
    "modele-compact",
    "modele-executif",
    "modele-creatif",
]


def hide_legacy_templates(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")
    CVTemplate.objects.exclude(slug__in=PUBLIC_TEMPLATE_SLUGS).update(is_active=False)


def show_legacy_templates(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")
    CVTemplate.objects.exclude(slug__in=PUBLIC_TEMPLATE_SLUGS).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ("templates", "0005_merge_template_metadata"),
    ]

    operations = [
        migrations.RunPython(hide_legacy_templates, show_legacy_templates),
    ]
