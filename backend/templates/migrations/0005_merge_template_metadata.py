# Generated manually to merge template branches and provide display metadata.

from django.db import migrations


DOCX_FILENAME = "modele_simple.docx"

TEMPLATES = [
    {
        "slug": "modele-simple",
        "name": "Essentiel",
        "description": "CV clair, rapide à lire, idéal pour une première version professionnelle.",
        "long_description": "Structure simple, titres nets et hiérarchie lisible. Convient aux candidatures classiques et aux profils qui veulent aller droit au but.",
        "category": "classic",
        "is_premium": False,
        "order": 1,
    },
    {
        "slug": "modele-classique",
        "name": "Classique",
        "description": "Présentation professionnelle avec une structure rassurante pour recruteurs.",
        "long_description": "Pensé pour les métiers administratifs, commerciaux, finance, RH et candidatures institutionnelles. Le contenu reste très lisible.",
        "category": "classic",
        "is_premium": False,
        "order": 2,
    },
    {
        "slug": "modele-moderne",
        "name": "Moderne",
        "description": "Mise en page contemporaine avec colonne latérale et accent discret.",
        "long_description": "Adapté aux profils tech, marketing, produit, design et jeunes diplômés. Les informations de contact et compétences ressortent vite.",
        "category": "modern",
        "is_premium": False,
        "order": 3,
    },
    {
        "slug": "modele-compact",
        "name": "Compact",
        "description": "Format dense et efficace pour tenir l’essentiel sur une page.",
        "long_description": "Recommandé quand le CV doit rester court: stages, alternance, profils junior, candidatures rapides ou versions ciblées.",
        "category": "minimal",
        "is_premium": False,
        "order": 4,
    },
    {
        "slug": "modele-executif",
        "name": "Executif",
        "description": "Rendu premium, sobre et haut de gamme pour profils expérimentés.",
        "long_description": "Pensé pour les managers, consultants, entrepreneurs et profils seniors. Les sections respirent davantage et les titres ont plus d’impact.",
        "category": "minimal",
        "is_premium": True,
        "order": 5,
    },
    {
        "slug": "modele-creatif",
        "name": "Creatif",
        "description": "Design distinctif pour profils communication, design et création.",
        "long_description": "Une présentation plus expressive sans tomber dans le décoratif. Adaptée aux candidatures qui doivent montrer une personnalité visuelle.",
        "category": "creative",
        "is_premium": True,
        "order": 6,
    },
]


def seed_template_metadata(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")

    CVTemplate.objects.exclude(slug__in=[template["slug"] for template in TEMPLATES]).filter(
        docx_filename__isnull=True
    ).update(is_active=False)

    for template in TEMPLATES:
        CVTemplate.objects.update_or_create(
            slug=template["slug"],
            defaults={
                "name": template["name"],
                "description": template["description"],
                "long_description": template["long_description"],
                "category": template["category"],
                "preview_image_url": "",
                "docx_filename": DOCX_FILENAME,
                "is_premium": template["is_premium"],
                "is_active": True,
                "order": template["order"],
            },
        )


def unseed_template_metadata(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")
    CVTemplate.objects.filter(slug__in=["modele-executif", "modele-creatif"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("templates", "0003_enhance_cvtemplate"),
        ("templates", "0004_seed_configured_cv_templates"),
    ]

    operations = [
        migrations.RunPython(seed_template_metadata, unseed_template_metadata),
    ]
