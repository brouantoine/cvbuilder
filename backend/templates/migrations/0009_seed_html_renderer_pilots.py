from django.db import migrations


PILOT_TEMPLATES = [
    {
        "slug": "galerie-cv-001",
        "name": "Classique lateral",
        "category": "classic",
        "description": "CV classique avec colonne laterale sombre et contenu RH tres lisible.",
        "long_description": "Modele HTML/CSS pilote avec contact, photo, competences et langues en sidebar.",
        "order": 1,
    },
    {
        "slug": "galerie-cv-002",
        "name": "Moderne bandeau",
        "category": "modern",
        "description": "CV moderne avec grand bandeau de tete et panneau de competences.",
        "long_description": "Modele HTML/CSS pilote adapte aux profils digitaux, projets et fonctions support.",
        "order": 2,
    },
    {
        "slug": "galerie-cv-003",
        "name": "Minimaliste clair",
        "category": "minimal",
        "description": "CV minimaliste, clair et sobre, avec lecture rapide des rubriques.",
        "long_description": "Modele HTML/CSS pilote oriente clarte, structure et sobriete professionnelle.",
        "order": 3,
    },
    {
        "slug": "galerie-cv-004",
        "name": "Standard rail RH",
        "category": "creative",
        "description": "CV standard avec rail lateral clair pour contact, competences et valeur RH.",
        "long_description": "Modele HTML/CSS pilote pense pour une lecture recruteur rapide et dense.",
        "order": 4,
    },
    {
        "slug": "galerie-cv-005",
        "name": "Executif sobre",
        "category": "classic",
        "description": "CV executif centre, sobre et symetrique pour profils confirmes.",
        "long_description": "Modele HTML/CSS pilote avec photo centrale, synthese, experiences et blocs bas.",
        "order": 5,
    },
]


def seed_html_renderer_pilots(apps, schema_editor):
    CVTemplate = apps.get_model("templates", "CVTemplate")
    for item in PILOT_TEMPLATES:
        CVTemplate.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "name": item["name"],
                "category": item["category"],
                "description": item["description"],
                "long_description": item["long_description"],
                "order": item["order"],
                "docx_filename": "",
                "is_active": True,
                "is_premium": False,
            },
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("templates", "0008_deactivate_incomplete_public_templates"),
    ]

    operations = [
        migrations.RunPython(seed_html_renderer_pilots, noop_reverse),
    ]

