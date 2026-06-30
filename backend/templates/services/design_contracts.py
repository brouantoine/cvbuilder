import re


VARIANT_CONTRACTS = {
    "coral-sidebar": {
        "layout": "Colonne saumon à gauche, contenu principal blanc à droite avec titres sombres.",
        "photo": "Photo ronde en haut de la colonne latérale.",
        "sections": "Profil, contact, compétences et logiciels en sidebar; formation, expériences et résultats dans le corps principal.",
        "density": "CV dense mais lisible, sans grands vides.",
    },
    "student-clean": {
        "layout": "Composition claire bleu pâle avec colonne contact à droite et sections en blocs.",
        "photo": "Photo ronde dans la colonne droite.",
        "sections": "Formation, expériences, bénévolat, compétences, langues et centres d'intérêt structurés pour profil débutant.",
        "density": "Remplir la page avec des rubriques courtes et utiles.",
    },
    "navy-header": {
        "layout": "Bandeau bleu foncé en haut, colonne latérale gauche et contenu principal détaillé.",
        "photo": "Photo ronde dans le bandeau supérieur.",
        "sections": "Contact, langues, compétences et logiciels à gauche; profil, expériences, formation à droite.",
        "density": "Adapté aux profils techniques ou reconversion avec missions détaillées.",
    },
    "beige-editorial": {
        "layout": "Design beige éditorial, colonne identité à gauche et contenu en deux colonnes.",
        "photo": "Photo ronde ou portrait dans la colonne identité.",
        "sections": "A propos, formation, expériences, compétences et centres d'intérêt dans une composition élégante.",
        "density": "Aéré mais complet, avec rubriques courtes.",
    },
    "neutral-photo": {
        "layout": "CV blanc neutre avec photo, lignes fines et colonne de synthèse.",
        "photo": "Photo rectangulaire ou ronde en haut.",
        "sections": "Contact, compétences, langues à gauche; expériences et formation à droite.",
        "density": "Style formel, une page lisible.",
    },
    "grey-commercial": {
        "layout": "Design commercial gris/noir, très sobre, orienté expérience.",
        "photo": "Photo sobre en colonne gauche.",
        "sections": "Profil, compétences, centres d'intérêt et parcours commercial structuré.",
        "density": "Corporate, compact et orienté résultats.",
    },
    "gold-culinary": {
        "layout": "Colonne dorée chaleureuse et bloc principal crème.",
        "photo": "Photo ronde en haut de la colonne dorée.",
        "sections": "Contact, qualités, langues, centres d'intérêt à gauche; expérience, études et compétences à droite.",
        "density": "Métier terrain, phrases courtes et compétences pratiques.",
    },
    "english-hr": {
        "layout": "CV international en anglais avec sidebar gauche et contenu RH à droite.",
        "photo": "Photo professionnelle en haut de la sidebar.",
        "sections": "Objective, work experience, recruitment consultant, education, skills, languages, references.",
        "density": "Anglais professionnel, direct et ATS-friendly.",
    },
    "diagonal-student": {
        "layout": "En-tête diagonal beige avec photo centrale et contenu en colonnes.",
        "photo": "Photo ronde centrée dans l'en-tête.",
        "sections": "Présentation, compétences, formation, expériences, langues et centres d'intérêt.",
        "density": "Profil débutant, valoriser potentiel, stages et bénévolat.",
    },
    "green-detail": {
        "layout": "Bloc vert en haut de la sidebar et timeline détaillée à droite.",
        "photo": "Photo ronde dans le bloc vert.",
        "sections": "Formation, expériences détaillées, intérêts, langues et compétences.",
        "density": "CV détaillé, accepte plus d'entrées que les autres modèles.",
    },
    "sidebar": {
        "layout": "Colonne latérale sombre à gauche, contenu principal blanc à droite.",
        "photo": "Photo ronde en haut de la colonne latérale.",
        "sections": "Contact, compétences, langues et centres d'intérêt en sidebar; profil, expériences, formation et sections ajoutées dans le corps principal.",
        "density": "Page A4 dense, les blocs doivent occuper la hauteur utile sans grands blancs.",
    },
    "header": {
        "layout": "Grand bandeau horizontal coloré en haut, photo ronde à droite, contenu principal en deux zones.",
        "photo": "Photo ronde dans le bandeau supérieur.",
        "sections": "Profil et expériences à gauche; compétences, langues, outils et certifications dans un panneau latéral clair.",
        "density": "Le panneau latéral doit descendre vers le bas de page.",
    },
    "topband": {
        "layout": "Grand bandeau horizontal coloré en haut, photo ronde à droite, contenu principal en deux zones.",
        "photo": "Photo ronde dans le bandeau supérieur.",
        "sections": "Profil et expériences à gauche; compétences, langues, outils et certifications dans un panneau latéral clair.",
        "density": "Le panneau latéral doit descendre vers le bas de page.",
    },
    "minimal": {
        "layout": "Mise en page blanche minimaliste avec bordure/ligne verticale et blocs doux en bas.",
        "photo": "Photo rectangulaire arrondie dans l'en-tête.",
        "sections": "Profil, expériences et formation structurés; réalisations et certifications dans les blocs bas.",
        "density": "Le bas de page doit être utilisé par des panneaux de synthèse.",
    },
    "rail": {
        "layout": "Grand contenu à gauche et rail latéral clair à droite.",
        "photo": "Photo ronde en haut du rail latéral.",
        "sections": "Profil, expériences, formation et réalisations à gauche; compétences, langues, outils, certifications et références à droite.",
        "density": "Le rail doit être rempli jusqu'en bas de la page.",
    },
    "executive": {
        "layout": "Design exécutif centré, photo en haut, nom au centre et blocs encadrés en bas.",
        "photo": "Photo ronde centrée au-dessus du nom.",
        "sections": "Profil, expériences, formation, compétences, réalisations et certifications dans une composition symétrique.",
        "density": "Style sobre mais page occupée, sans zone blanche excessive.",
    },
}


def gallery_variant_for_slug(slug):
    match = re.match(r"^galerie-cv-(\d+)$", slug or "")
    if not match:
        return ""
    index = (int(match.group(1)) - 1) % 10
    return {
        0: "sidebar",
        1: "header",
        2: "minimal",
        3: "rail",
        4: "executive",
        5: "sidebar",
        6: "header",
        7: "minimal",
        8: "rail",
        9: "executive",
    }[index]


def template_design_contract(template):
    variant = gallery_variant_for_slug(getattr(template, "slug", ""))
    contract = VARIANT_CONTRACTS.get(variant, {})
    try:
        from cvs.renderers.html import renderer_variant_for_template, supports_html_renderer

        if supports_html_renderer(template):
            renderer_kind = "html_css"
            variant = renderer_variant_for_template(template) or variant
            contract = VARIANT_CONTRACTS.get(variant, contract)
        else:
            renderer_kind = "gallery_canvas"
    except Exception:
        renderer_kind = "gallery_canvas"
    return {
        "template_id": getattr(template, "id", None),
        "template_name": getattr(template, "name", ""),
        "template_slug": getattr(template, "slug", ""),
        "category": getattr(template, "category", ""),
        "renderer_variant": variant,
        "renderer_kind": renderer_kind,
        **contract,
        "strict_rule": (
            "L'IA ne doit produire que des données structurées. "
            "Le renderer appliquera ce contrat de design; ne jamais recopier le style de l'ancien CV."
        ),
    }
