import io
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageOps

from cvs.renderers.html import (
    HTML_TEMPLATE_SPECS,
    HTMLRendererUnavailable,
    render_html_template_preview_png_bytes,
    supports_html_renderer,
)
from templates.models import CVTemplate
from templates.services.public_catalog import sync_public_template_catalog


THUMB_SIZE = (320, 448)

TEMPLATE_META = {
    "galerie-cv-001": ("Classique lateral", "classic", "CV classique avec colonne laterale sombre et contenu RH tres lisible."),
    "galerie-cv-002": ("Moderne bandeau", "modern", "CV moderne avec grand bandeau de tete et panneau de competences."),
    "galerie-cv-003": ("Minimaliste clair", "minimal", "CV minimaliste, clair et sobre, avec lecture rapide des rubriques."),
    "galerie-cv-004": ("Standard rail RH", "creative", "CV standard avec rail lateral clair pour contact, competences et valeur RH."),
    "galerie-cv-005": ("Executif sobre", "classic", "CV executif centre, sobre et symetrique pour profils confirmes."),
}


def _photo_path(index):
    photos = sorted((settings.BASE_DIR.parent / "frontend" / "src" / "assets" / "cv-photos" / "normalized").glob("*.png"))
    if not photos:
        return ""
    return str(photos[index % len(photos)])


def _sample_data(index):
    people = [
        ("Awa", "Kone", "Cheffe de projet digital"),
        ("Kevin", "Amani", "Ingenieur DevOps"),
        ("Sarah", "Bamba", "Chargee de recrutement"),
        ("Yann", "Brou", "Responsable commercial"),
        ("Isaac", "Kouadio", "Data analyst"),
    ]
    first, last, role = people[index % len(people)]
    return {
        "first_name": first,
        "last_name": last,
        "job_title": role,
        "phone": "+225 07 00 00 00 00",
        "email": f"{first.lower()}.{last.lower()}@exemple.com",
        "address": "Abidjan, Cote d'Ivoire",
        "linkedin": "linkedin.com/in/profil",
        "photo_url": _photo_path(index),
        "profile": (
            "Profil professionnel oriente resultats, capable de structurer les priorites, "
            "coordonner les parties prenantes et livrer des solutions adaptees aux objectifs metier."
        ),
        "experiences": [
            {
                "job_title": role,
                "company": "Atlas Digital",
                "location": "Abidjan",
                "period": "2022 - Aujourd'hui",
                "missions": [
                    "Pilotage des activites cles avec suivi des indicateurs de performance.",
                    "Coordination des equipes internes et amelioration des processus operationnels.",
                    "Production de livrables professionnels adaptes aux exigences clients.",
                ],
            },
            {
                "job_title": "Assistant projet",
                "company": "Groupe Horizon",
                "location": "Abidjan",
                "period": "2020 - 2022",
                "missions": [
                    "Preparation des reportings, comptes rendus et supports de decision.",
                    "Contribution a la mise en place d'outils de suivi et de controle qualite.",
                ],
            },
            {
                "job_title": "Stagiaire operationnel",
                "company": "Impact Services",
                "location": "Abidjan",
                "period": "2019 - 2020",
                "missions": [
                    "Collecte et fiabilisation des donnees necessaires au suivi d'activite.",
                    "Appui aux equipes dans la preparation des reunions et supports clients.",
                ],
            },
        ],
        "education": [
            {"degree": "Cycle ingenieur", "institution": "Institut Superieur de Technologie", "location": "Abidjan", "period": "2017 - 2020"},
            {"degree": "Classes preparatoires", "institution": "Ecole Superieure", "location": "Abidjan", "period": "2015 - 2017"},
        ],
        "skills": ["Gestion de projet", "Analyse", "Communication", "Reporting", "Excel", "Power BI", "Organisation", "Leadership"],
        "languages": [{"language": "Francais", "level": "Courant"}, {"language": "Anglais", "level": "Professionnel"}],
        "hobbies": ["Veille metier", "Innovation", "Formation continue", "Mentorat"],
        "extra_sections": [
            {"title": "Realisations", "items": ["Reduction des delais de traitement de 25% sur un processus critique.", "Mise en place d'un tableau de bord de suivi hebdomadaire."]},
            {"title": "Certifications", "items": ["Certification gestion de projet", "Formation analyse de donnees", "Atelier communication professionnelle"]},
            {"title": "References", "items": ["References disponibles sur demande."]},
        ],
    }


def _save_images(template, png_bytes):
    preview_rel = Path("templates") / "previews" / "html" / f"{template.slug}.png"
    thumb_rel = Path("templates") / "thumbnails" / "html" / f"{template.slug}.png"
    preview_path = Path(settings.MEDIA_ROOT) / preview_rel
    thumb_path = Path(settings.MEDIA_ROOT) / thumb_rel
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_bytes(png_bytes)

    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    thumb = ImageOps.contain(image, THUMB_SIZE, Image.Resampling.LANCZOS)
    thumb.save(thumb_path, "PNG", optimize=True)

    template.preview_full.name = preview_rel.as_posix()
    template.thumbnail.name = thumb_rel.as_posix()
    template.save(update_fields=["preview_full", "thumbnail", "updated_at"])


class Command(BaseCommand):
    help = "Genere les apercus PNG depuis le meme renderer HTML/CSS que le PDF final."

    def add_arguments(self, parser):
        parser.add_argument("--ignore-errors", action="store_true", help="Continue si le moteur HTML/PDF est indisponible.")
        parser.add_argument("--slug", help="Ne genere qu'un seul modele.")
        parser.add_argument("--limit", type=int, help="Limite le nombre de modeles generes.")

    def handle(self, *args, **options):
        failures = []
        for index, slug in enumerate(HTML_TEMPLATE_SPECS):
            if slug not in TEMPLATE_META:
                continue
            name, category, description = TEMPLATE_META[slug]
            template, _ = CVTemplate.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": category,
                    "description": description,
                    "long_description": f"{description} Rendu par un modele HTML/CSS dedie.",
                    "order": index + 1,
                    "docx_filename": "",
                    "is_active": True,
                    "is_premium": False,
                },
            )
        sync_public_template_catalog()

        queryset = CVTemplate.objects.filter(is_active=True).order_by("order", "id")
        if options.get("slug"):
            queryset = queryset.filter(slug=options["slug"])
        templates = [template for template in queryset if supports_html_renderer(template)]
        if options.get("limit"):
            templates = templates[: options["limit"]]

        if not templates:
            self.stdout.write(self.style.WARNING("Aucun modele HTML/CSS actif a generer."))
            return

        for index, template in enumerate(templates):
            try:
                png_bytes = render_html_template_preview_png_bytes(template, _sample_data(index), base_name=template.slug)
                _save_images(template, png_bytes)
                self.stdout.write(self.style.SUCCESS(f"{template.slug}: apercu HTML genere"))
            except HTMLRendererUnavailable as exc:
                failures.append(f"{template.slug}: {exc}")
                self.stdout.write(self.style.WARNING(f"{template.slug}: {exc}"))

        if failures and not options["ignore_errors"]:
            raise CommandError("Apercus HTML incomplets. " + " | ".join(failures))
