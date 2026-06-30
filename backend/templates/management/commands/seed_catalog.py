"""
Refonte du catalogue : rase les anciens modèles et crée 20 modèles « Chic »
bien remplis (4 personas riches × photos cohérentes × palettes), avec aperçus
pré-rendus.

Usage : python manage.py seed_catalog
"""
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.conf import settings

from cvs.renderers.html import render_html_template_preview_png_bytes
from templates.models import CVTemplate

PHOTO_DIR = settings.BASE_DIR.parent / "frontend" / "src" / "assets" / "cv-photos" / "normalized"


def photo(index):
    path = PHOTO_DIR / f"cv-photo-{index:02d}.png"
    return str(path) if path.exists() else ""


# --- 4 personas riches et complets (chaque section remplie) ---
COMPTABLE = {
    "first_name": "Alassane",
    "last_name": "Soro",
    "job_title": "Comptable",
    "tagline": "8 ans d'expérience",
    "age": "30 ans",
    "nationality": "Ivoirien",
    "marital_status": "Marié, 2 enfants",
    "phone": "+225 07 00 11 51 12",
    "email": "alassane.soro@email.com",
    "address": "Abidjan, Côte d'Ivoire",
    "linkedin": "linkedin.com/in/alassanesoro",
    "driving_license": "Permis B",
    "profile": (
        "Professionnel des finances et de la comptabilité, je maîtrise parfaitement les "
        "techniques comptables et les normes SYSCOHADA. Rigoureux et organisé, je mets mon "
        "dynamisme au service de la performance financière de votre institution."
    ),
    "experiences": [
        {"job_title": "Comptable fournisseurs", "company": "Mael Shop — Abidjan", "period": "Avr. 2016 – Mai 2021",
         "missions": ["Gestion des comptes fournisseurs et suivi des factures.", "Contrôle des paiements et des échéances.",
                       "Réconciliation des comptes et lettrage.", "Préparation des rapports financiers mensuels."]},
        {"job_title": "Comptable général", "company": "Agence de Voyage HBK — Abidjan", "period": "Déc. 2013 – Août 2016",
         "missions": ["Tenue de la comptabilité générale et analytique.", "Suivi de la trésorerie et des recettes.",
                       "Préparation des déclarations fiscales et sociales (TVA, CNPS)."]},
        {"job_title": "Stagiaire comptable", "company": "Cabinet IBE Consulting — Abidjan", "period": "Juin 2014 – Sept. 2014",
         "missions": ["Saisie et classement des pièces comptables.", "Assistance à la révision des comptes."]},
    ],
    "education": [
        {"degree": "Master 2 Audit et Contrôle de Gestion", "institution": "EDHEC Plateau", "period": "2017 – 2018"},
        {"degree": "Licence Pro. Finance Comptabilité", "institution": "EDHEC Plateau", "period": "2014 – 2015"},
        {"degree": "BTS Finance Comptabilité et Gestion", "institution": "EDHEC Plateau", "period": "2012 – 2013"},
        {"degree": "Baccalauréat Série G2", "institution": "Lycée Moderne d'Abidjan", "period": "2010 – 2011"},
    ],
    "skills": ["Comptabilité générale et analytique", "Maîtrise du référentiel SYSCOHADA",
               "Audit et contrôle de gestion", "Déclarations fiscales et sociales", "Reporting et tableaux de bord"],
    "languages": [{"language": "Français", "level": "Courant"}, {"language": "Anglais", "level": "Intermédiaire"}],
    "hobbies": ["Voyage", "Lecture", "Football"],
    "extra_sections": [
        {"title": "Informatiques", "items": ["Sage Saari Compta", "Excel avancé", "Word, PowerPoint"]},
        {"title": "Aptitudes", "items": ["Rigueur", "Polyvalence", "Esprit d'initiative", "Discrétion"]},
        {"title": "Projets", "items": ["Mise en place du plan analytique d'un groupe de 3 sociétés.",
                                        "Automatisation du reporting mensuel sous Excel (gain de 40 % de temps)."]},
        {"title": "Certifications", "items": ["Certification SYSCOHADA révisé — 2020", "Fiscalité des entreprises — CGA, 2019"]},
    ],
}

DEVELOPPEUR = {
    "first_name": "Kévin",
    "last_name": "Brou",
    "job_title": "Développeur Full-Stack",
    "tagline": "React · Django · 4 ans d'expérience",
    "age": "27 ans",
    "nationality": "Ivoirien",
    "marital_status": "Célibataire",
    "phone": "+225 07 88 33 98 82",
    "email": "kevin.brou@email.com",
    "address": "Abidjan, Yopougon",
    "github": "github.com/kevinbrou",
    "portfolio": "kevinbrou.dev",
    "profile": (
        "Développeur full-stack passionné, spécialisé dans la conception d'applications web "
        "modernes et performantes. J'accompagne les entreprises de l'idée au déploiement avec "
        "React, Next.js, Django et PostgreSQL."
    ),
    "experiences": [
        {"job_title": "Développeur Full-Stack", "company": "Winlogic Technologies — Abidjan", "period": "Janv. 2024 – Aujourd'hui",
         "missions": ["Conception d'une solution mobile de sécurité (alertes, supervision).",
                       "Développement d'API REST sécurisées (Django REST Framework).",
                       "Déploiement et maintenance sur serveurs de production."]},
        {"job_title": "Développeur Web", "company": "Studio Digital CI — Abidjan", "period": "2022 – 2023",
         "missions": ["Création de plateformes e-commerce (React, Django).",
                       "Intégration responsive et optimisation des performances.",
                       "Mise en place de l'intégration continue."]},
        {"job_title": "Développeur Junior", "company": "Freelance", "period": "2021 – 2022",
         "missions": ["Développement de sites vitrines et portfolios interactifs.", "Maintenance et corrections d'applications clientes."]},
    ],
    "education": [
        {"degree": "Master Pro. Systèmes et Applications", "institution": "Académie des Sciences Technologiques", "period": "2024 – 2026"},
        {"degree": "Licence Systèmes et Applications", "institution": "Académie des Sciences Technologiques", "period": "2023 – 2024"},
        {"degree": "BTS Informatique Développeur", "institution": "Académie des Sciences Technologiques", "period": "2021 – 2023"},
        {"degree": "Baccalauréat Série D", "institution": "Lycée Moderne de Bongouanou", "period": "2019 – 2020"},
    ],
    "skills": ["Développement Full-Stack React & Django", "Conception d'API REST sécurisées",
               "Bases de données PostgreSQL", "Intégration responsive & UX", "Méthodes agiles (Scrum)"],
    "languages": [{"language": "Français", "level": "Excellent"}, {"language": "Anglais", "level": "Courant"}],
    "hobbies": ["Veille tech", "Échecs", "Basket"],
    "extra_sections": [
        {"title": "Informatiques", "items": ["React, Next.js", "Django, DRF", "PostgreSQL, Redis", "Python, JavaScript"]},
        {"title": "Aptitudes", "items": ["Rigueur", "Autonomie", "Capacité d'adaptation", "Esprit d'équipe"]},
        {"title": "Projets", "items": ["Yatou.ci — plateforme e-commerce multi-vendeurs (React, Django).",
                                        "Movicash — gestion des recettes Orange Money.",
                                        "Application mobile de sécurité avec supervision en temps réel."]},
        {"title": "Certifications", "items": ["Formation UX Design — OpenClassrooms, 2023", "Arduino & IoT — Coursera, 2024"]},
    ],
}

COMMERCIAL = {
    "first_name": "Awa",
    "last_name": "Koné",
    "job_title": "Chargée de clientèle",
    "tagline": "Commerce & relation client",
    "age": "29 ans",
    "nationality": "Ivoirienne",
    "marital_status": "Mariée",
    "phone": "+225 05 04 22 18 60",
    "email": "awa.kone@email.com",
    "address": "Abidjan, Cocody",
    "linkedin": "linkedin.com/in/awakone",
    "driving_license": "Permis B",
    "profile": (
        "Commerciale orientée résultats, je développe et fidélise un portefeuille clients par "
        "une écoute active et un suivi rigoureux. Force de proposition, je dépasse régulièrement "
        "mes objectifs de vente."
    ),
    "experiences": [
        {"job_title": "Chargée de clientèle", "company": "Orange CI — Abidjan", "period": "2020 – Aujourd'hui",
         "missions": ["Développement et fidélisation d'un portefeuille de 200+ clients.",
                       "Atteinte de 115 % des objectifs commerciaux annuels.",
                       "Conseil et vente de solutions adaptées aux besoins clients."]},
        {"job_title": "Conseillère commerciale", "company": "Bank Of Africa — Abidjan", "period": "2017 – 2020",
         "missions": ["Accueil, conseil et vente de produits bancaires.", "Gestion des réclamations et satisfaction client."]},
        {"job_title": "Téléconseillère", "company": "PerfecTeam — Abidjan", "period": "2015 – 2017",
         "missions": ["Prospection téléphonique et prise de rendez-vous.", "Suivi des campagnes commerciales."]},
    ],
    "education": [
        {"degree": "Master Marketing et Vente", "institution": "INP-HB Yamoussoukro", "period": "2014 – 2015"},
        {"degree": "Licence Gestion Commerciale", "institution": "Université FHB Cocody", "period": "2012 – 2013"},
        {"degree": "BTS Action Commerciale", "institution": "Groupe Pigier Abidjan", "period": "2010 – 2012"},
        {"degree": "Baccalauréat Série B", "institution": "Lycée Sainte-Marie de Cocody", "period": "2009 – 2010"},
    ],
    "skills": ["Développement de portefeuille clients", "Techniques de vente et négociation",
               "Fidélisation et relation client", "Reporting commercial", "Gestion des réclamations"],
    "languages": [{"language": "Français", "level": "Courant"}, {"language": "Anglais", "level": "Bon"}],
    "hobbies": ["Danse", "Cuisine", "Voyages"],
    "extra_sections": [
        {"title": "Informatiques", "items": ["CRM Salesforce", "Pack Office", "Outils de reporting"]},
        {"title": "Aptitudes", "items": ["Sens du contact", "Persévérance", "Empathie", "Esprit d'équipe"]},
        {"title": "Projets", "items": ["Lancement d'une offre fidélité ayant augmenté la rétention de 18 %.",
                                        "Animation d'un réseau de 12 points de vente partenaires."]},
        {"title": "Certifications", "items": ["Négociation commerciale — 2021", "Relation client digitale — 2022"]},
    ],
}

RH = {
    "first_name": "Fatou",
    "last_name": "Diabaté",
    "job_title": "Assistante RH",
    "tagline": "Ressources humaines & paie",
    "age": "28 ans",
    "nationality": "Ivoirienne",
    "marital_status": "Célibataire",
    "phone": "+225 01 02 88 44 21",
    "email": "fatou.diabate@email.com",
    "address": "Abidjan, Marcory",
    "linkedin": "linkedin.com/in/fatoudiabate",
    "profile": (
        "Assistante RH polyvalente, j'accompagne la gestion administrative du personnel, le "
        "recrutement et la paie. Organisée et discrète, je veille au respect de la "
        "réglementation sociale et au bien-être des équipes."
    ),
    "experiences": [
        {"job_title": "Assistante RH", "company": "Nestlé CI — Abidjan", "period": "2019 – Aujourd'hui",
         "missions": ["Gestion administrative du personnel (contrats, congés, absences).",
                       "Préparation des éléments variables de paie.",
                       "Suivi du recrutement et de l'onboarding des nouveaux collaborateurs."]},
        {"job_title": "Chargée de recrutement", "company": "Cabinet RH Excellence — Abidjan", "period": "2016 – 2019",
         "missions": ["Sourcing et présélection des candidats.", "Conduite des entretiens et reporting RH."]},
        {"job_title": "Stagiaire RH", "company": "SIB — Abidjan", "period": "2015 – 2016",
         "missions": ["Mise à jour des dossiers du personnel.", "Organisation des formations internes."]},
    ],
    "education": [
        {"degree": "Master Gestion des Ressources Humaines", "institution": "CESAG Dakar", "period": "2014 – 2015"},
        {"degree": "Licence Sciences de Gestion", "institution": "Université FHB Cocody", "period": "2012 – 2013"},
        {"degree": "BTS Gestion des Entreprises", "institution": "Groupe Loko Abidjan", "period": "2010 – 2012"},
        {"degree": "Baccalauréat Série G2", "institution": "Lycée Municipal de Marcory", "period": "2009 – 2010"},
    ],
    "skills": ["Gestion administrative du personnel", "Préparation et contrôle de la paie",
               "Recrutement et intégration", "Droit social ivoirien", "Gestion des formations"],
    "languages": [{"language": "Français", "level": "Courant"}, {"language": "Anglais", "level": "Intermédiaire"}],
    "hobbies": ["Lecture", "Bénévolat", "Natation"],
    "extra_sections": [
        {"title": "Informatiques", "items": ["SIRH Sage Paie", "Excel RH", "Pack Office"]},
        {"title": "Aptitudes", "items": ["Organisation", "Discrétion", "Sens de l'écoute", "Rigueur"]},
        {"title": "Projets", "items": ["Digitalisation des dossiers du personnel (zéro papier).",
                                        "Mise en place d'un parcours d'intégration des nouveaux salariés."]},
        {"title": "Certifications", "items": ["Gestion de la paie — 2020", "Droit du travail OHADA — 2021"]},
    ],
}

PERSONAS = [
    (COMPTABLE, 2),   # homme
    (DEVELOPPEUR, 5),  # homme
    (COMMERCIAL, 1),   # femme
    (RH, 7),           # femme
]

# slug, name, category, premium  (l'ordre suit l'affichage de la galerie)
CATALOG = [
    ("chic-anthracite", "Chic Anthracite", "creative", False),
    ("chic-azur", "Chic Azur", "modern", False),
    ("chic-emeraude", "Chic Émeraude", "modern", True),
    ("chic-bordeaux", "Chic Bordeaux", "creative", True),
    ("chic-violet", "Chic Violet", "creative", True),
    ("chic-marine", "Chic Marine", "modern", False),
    ("chic-corail", "Chic Corail", "creative", True),
    ("chic-foret", "Chic Forêt", "modern", False),
    ("chic-prune", "Chic Prune", "creative", True),
    ("chic-acier", "Chic Acier", "modern", False),
    ("lateral-sarcelle", "Latéral Sarcelle", "modern", False),
    ("lateral-or", "Latéral Or", "colorful", True),
    ("executif-graphite", "Exécutif Graphite", "classic", False),
    ("executif-marine", "Exécutif Marine", "classic", False),
    ("bandeau-ocean", "Bandeau Océan", "modern", False),
    ("bandeau-emeraude", "Bandeau Émeraude", "modern", False),
    ("minimal-ardoise", "Minimal Ardoise", "minimal", False),
    ("minimal-charbon", "Minimal Charbon", "minimal", False),
    ("rail-ambre", "Rail Ambre", "colorful", True),
    ("rail-indigo", "Rail Indigo", "colorful", True),
]


class Command(BaseCommand):
    help = "Rase l'ancien catalogue et crée 20 modèles Chic bien remplis."

    def handle(self, *args, **options):
        razed = CVTemplate.objects.update(is_active=False)
        self.stdout.write(f"Anciens modèles désactivés : {razed}")

        for index, (slug, name, category, premium) in enumerate(CATALOG):
            persona, photo_index = PERSONAS[index % len(PERSONAS)]
            data = dict(persona)
            data["photo_url"] = photo(photo_index)
            template, _ = CVTemplate.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": category,
                    "description": f"Modèle {name} — sidebar élégante, profil mis en valeur.",
                    "long_description": "Mise en page professionnelle, lisible et compatible ATS.",
                    "is_premium": premium,
                    "is_active": True,
                    "order": index,
                    "docx_filename": "",
                },
            )
            try:
                png = render_html_template_preview_png_bytes(template, data, base_name=slug)
                template.preview_full.save(f"{slug}.png", ContentFile(png), save=True)
                self.stdout.write(self.style.SUCCESS(f"✓ {slug} — {persona['job_title']} ({len(png)} o)"))
            except Exception as exc:  # noqa: BLE001
                self.stdout.write(self.style.ERROR(f"✗ aperçu {slug} : {exc}"))

        # NB : l'image de la page d'accueil (frontend/src/assets/cv-assanvo-preview.png)
        # est le vrai CV de l'utilisateur et n'est PAS régénérée ici.

        self.stdout.write(self.style.SUCCESS(f"Catalogue actif : {CVTemplate.objects.filter(is_active=True).count()} modèles."))
