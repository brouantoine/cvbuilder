# Generated manually to provide configured MVP templates.

from django.db import migrations


DOCX_FILENAME = "modele_simple.docx"

CONFIGURED_TEMPLATES = [
    {
        "slug": "modele-simple",
        "name": "Modèle simple",
        "description": "Un CV clair et direct pour candidatures rapides.",
        "is_premium": False,
    },
    {
        "slug": "modele-classique",
        "name": "Classique",
        "description": "Une structure professionnelle adaptée aux profils administratifs et commerciaux.",
        "is_premium": False,
    },
    {
        "slug": "modele-moderne",
        "name": "Moderne",
        "description": "Une présentation sobre pour les profils tech, créatifs et jeunes diplômés.",
        "is_premium": False,
    },
    {
        "slug": "modele-compact",
        "name": "Compact",
        "description": "Un format efficace pour tenir les informations essentielles sur une page.",
        "is_premium": False,
    },
]


def seed_configured_templates(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")
    CVTemplate.objects.filter(docx_filename__isnull=True).update(docx_filename=DOCX_FILENAME)
    CVTemplate.objects.filter(docx_filename="").update(docx_filename=DOCX_FILENAME)

    for template in CONFIGURED_TEMPLATES:
        CVTemplate.objects.update_or_create(
            slug=template["slug"],
            defaults={
                "name": template["name"],
                "description": template["description"],
                "preview_image_url": "",
                "is_premium": template["is_premium"],
                "docx_filename": DOCX_FILENAME,
            },
        )


def remove_seeded_templates(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")
    slugs = [template["slug"] for template in CONFIGURED_TEMPLATES if template["slug"] != "modele-simple"]
    CVTemplate.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("templates", "0003_seed_simple_template"),
    ]

    operations = [
        migrations.RunPython(seed_configured_templates, remove_seeded_templates),
    ]
