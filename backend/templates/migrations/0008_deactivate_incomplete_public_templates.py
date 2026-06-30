from django.db import migrations


INCOMPLETE_TEMPLATE_SLUGS = [
    "modele-simple",
    "modele-classique",
    "modele-moderne",
    "modele-compact",
    "modele-executif",
    "modele-creatif",
    "custom-document-9",
]


def deactivate_incomplete_templates(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")
    CVTemplate.objects.filter(slug__in=INCOMPLETE_TEMPLATE_SLUGS).update(is_active=False)


def reactivate_incomplete_templates(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")
    CVTemplate.objects.filter(slug__in=INCOMPLETE_TEMPLATE_SLUGS).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ("templates", "0007_alter_cvtemplate_description_and_more"),
    ]

    operations = [
        migrations.RunPython(deactivate_incomplete_templates, reactivate_incomplete_templates),
    ]
