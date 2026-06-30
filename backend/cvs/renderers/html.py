import io
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.template.loader import render_to_string


class UnsupportedHTMLTemplate(Exception):
    """Le modèle choisi n'a pas encore de renderer HTML/CSS."""


class HTMLRendererUnavailable(RuntimeError):
    """Aucun moteur HTML vers PDF n'a pu produire le document."""


HTML_VARIANT_SPECS = {
    "chic": {
        "template": "cvs/html_renderers/chic.html",
        "variant": "chic",
    },
    "sidebar": {
        "template": "cvs/html_renderers/sidebar.html",
        "variant": "sidebar",
    },
    "topband": {
        "template": "cvs/html_renderers/topband.html",
        "variant": "topband",
    },
    "minimal": {
        "template": "cvs/html_renderers/minimal.html",
        "variant": "minimal",
    },
    "rail": {
        "template": "cvs/html_renderers/rail.html",
        "variant": "rail",
    },
    "executive": {
        "template": "cvs/html_renderers/executive.html",
        "variant": "executive",
    },
}


GALLERY_VARIANTS = ("sidebar", "topband", "minimal", "rail", "executive", "sidebar", "topband", "minimal", "rail", "executive")

CATEGORY_VARIANTS = {
    "classic": ("sidebar", "executive", "topband"),
    "modern": ("topband", "rail", "minimal"),
    "creative": ("rail", "topband", "sidebar"),
    "minimal": ("minimal", "executive", "rail"),
    "colorful": ("topband", "rail", "sidebar"),
}

CATEGORY_PALETTES = {
    "classic": [
        {"accent": "#1d4ed8", "dark": "#111827", "soft": "#eff6ff", "muted": "#64748b"},
        {"accent": "#334155", "dark": "#0f172a", "soft": "#f1f5f9", "muted": "#64748b"},
    ],
    "modern": [
        {"accent": "#0f766e", "dark": "#0f172a", "soft": "#ecfdf5", "muted": "#64748b"},
        {"accent": "#2563eb", "dark": "#111827", "soft": "#dbeafe", "muted": "#64748b"},
    ],
    "creative": [
        {"accent": "#9f1239", "dark": "#18181b", "soft": "#fff1f2", "muted": "#71717a"},
        {"accent": "#7c3aed", "dark": "#1f2937", "soft": "#f5f3ff", "muted": "#6b7280"},
    ],
    "minimal": [
        {"accent": "#374151", "dark": "#111827", "soft": "#f3f4f6", "muted": "#6b7280"},
        {"accent": "#0f766e", "dark": "#172554", "soft": "#f8fafc", "muted": "#64748b"},
    ],
    "colorful": [
        {"accent": "#be123c", "dark": "#111827", "soft": "#ffe4e6", "muted": "#64748b"},
        {"accent": "#b45309", "dark": "#1f2937", "soft": "#fffbeb", "muted": "#78716c"},
    ],
}


HTML_TEMPLATE_SPECS = {
    "galerie-cv-001": {
        **HTML_VARIANT_SPECS["sidebar"],
        "label": "Classique lateral",
        "palette": CATEGORY_PALETTES["classic"][0],
    },
    "galerie-cv-002": {
        **HTML_VARIANT_SPECS["topband"],
        "label": "Moderne bandeau",
        "palette": CATEGORY_PALETTES["modern"][0],
    },
    "galerie-cv-003": {
        **HTML_VARIANT_SPECS["minimal"],
        "label": "Minimaliste clair",
        "palette": CATEGORY_PALETTES["minimal"][0],
    },
    "galerie-cv-004": {
        **HTML_VARIANT_SPECS["rail"],
        "label": "Standard rail RH",
        "palette": CATEGORY_PALETTES["creative"][0],
    },
    "galerie-cv-005": {
        **HTML_VARIANT_SPECS["executive"],
        "label": "Executif sobre",
        "palette": CATEGORY_PALETTES["classic"][1],
    },
}


# Palettes des 10 modèles du catalogue (refonte « Chic »).
CHIC_PALETTES = {
    "anthracite": {"accent": "#e8772e", "dark": "#3b3b3d", "soft": "#f5f3f0", "muted": "#6b7280"},
    "azur": {"accent": "#2563eb", "dark": "#1e293b", "soft": "#eef2fb", "muted": "#64748b"},
    "emeraude": {"accent": "#0f9d72", "dark": "#1f2d28", "soft": "#ecfdf5", "muted": "#64748b"},
    "bordeaux": {"accent": "#b03052", "dark": "#2c1f24", "soft": "#fdf2f4", "muted": "#6b5560"},
    "violet": {"accent": "#7c3aed", "dark": "#241f33", "soft": "#f4f1fd", "muted": "#6b6580"},
    "sarcelle": {"accent": "#0d9488", "dark": "#14302e", "soft": "#effdfa", "muted": "#5f7572"},
    "graphite": {"accent": "#334155", "dark": "#111827", "soft": "#f1f5f9", "muted": "#64748b"},
    "ocean": {"accent": "#0369a1", "dark": "#0f2740", "soft": "#eff6fc", "muted": "#5b7184"},
    "ardoise": {"accent": "#475569", "dark": "#1e293b", "soft": "#f4f6f9", "muted": "#6b7280"},
    "ambre": {"accent": "#d97706", "dark": "#2b2620", "soft": "#fffaf0", "muted": "#78716c"},
    "marine": {"accent": "#1d4ed8", "dark": "#0b1f3a", "soft": "#eef3fc", "muted": "#5b7184"},
    "corail": {"accent": "#e1564b", "dark": "#2c2522", "soft": "#fef2f1", "muted": "#7a6a66"},
    "foret": {"accent": "#15803d", "dark": "#14271c", "soft": "#effaf1", "muted": "#5d7565"},
    "prune": {"accent": "#9d2d6b", "dark": "#271a24", "soft": "#fdf1f8", "muted": "#6f5b67"},
    "acier": {"accent": "#0e7490", "dark": "#16252b", "soft": "#eefafe", "muted": "#5b7480"},
    "or": {"accent": "#b7791f", "dark": "#2a2418", "soft": "#fdf8ec", "muted": "#7a6f57"},
    "indigo": {"accent": "#4f46e5", "dark": "#1c1b33", "soft": "#f0f0fe", "muted": "#65647e"},
    "charbon": {"accent": "#1f2937", "dark": "#0b0f17", "soft": "#f3f4f6", "muted": "#6b7280"},
}

CATALOG_TEMPLATE_SPECS = {
    "chic-anthracite": {"variant": "chic", "palette": CHIC_PALETTES["anthracite"], "label": "Chic Anthracite"},
    "chic-azur": {"variant": "chic", "palette": CHIC_PALETTES["azur"], "label": "Chic Azur"},
    "chic-emeraude": {"variant": "chic", "palette": CHIC_PALETTES["emeraude"], "label": "Chic Émeraude"},
    "chic-bordeaux": {"variant": "chic", "palette": CHIC_PALETTES["bordeaux"], "label": "Chic Bordeaux"},
    "chic-violet": {"variant": "chic", "palette": CHIC_PALETTES["violet"], "label": "Chic Violet"},
    "lateral-sarcelle": {"variant": "sidebar", "palette": CHIC_PALETTES["sarcelle"], "label": "Latéral Sarcelle"},
    "executif-graphite": {"variant": "executive", "palette": CHIC_PALETTES["graphite"], "label": "Exécutif Graphite"},
    "bandeau-ocean": {"variant": "topband", "palette": CHIC_PALETTES["ocean"], "label": "Bandeau Océan"},
    "minimal-ardoise": {"variant": "minimal", "palette": CHIC_PALETTES["ardoise"], "label": "Minimal Ardoise"},
    "rail-ambre": {"variant": "rail", "palette": CHIC_PALETTES["ambre"], "label": "Rail Ambre"},
    "chic-marine": {"variant": "chic", "palette": CHIC_PALETTES["marine"], "label": "Chic Marine"},
    "chic-corail": {"variant": "chic", "palette": CHIC_PALETTES["corail"], "label": "Chic Corail"},
    "chic-foret": {"variant": "chic", "palette": CHIC_PALETTES["foret"], "label": "Chic Forêt"},
    "chic-prune": {"variant": "chic", "palette": CHIC_PALETTES["prune"], "label": "Chic Prune"},
    "chic-acier": {"variant": "chic", "palette": CHIC_PALETTES["acier"], "label": "Chic Acier"},
    "lateral-or": {"variant": "sidebar", "palette": CHIC_PALETTES["or"], "label": "Latéral Or"},
    "executif-marine": {"variant": "executive", "palette": CHIC_PALETTES["marine"], "label": "Exécutif Marine"},
    "bandeau-emeraude": {"variant": "topband", "palette": CHIC_PALETTES["foret"], "label": "Bandeau Émeraude"},
    "minimal-charbon": {"variant": "minimal", "palette": CHIC_PALETTES["charbon"], "label": "Minimal Charbon"},
    "rail-indigo": {"variant": "rail", "palette": CHIC_PALETTES["indigo"], "label": "Rail Indigo"},
}


def _gallery_index(slug):
    match = re.match(r"^galerie-cv-(\d+)$", slug or "")
    return int(match.group(1)) - 1 if match else None


def _stable_index(value):
    text = _safe_text(value)
    return sum((index + 1) * ord(char) for index, char in enumerate(text))


def _palette_for(template, index=0):
    palettes = CATEGORY_PALETTES.get(getattr(template, "category", "") or "", CATEGORY_PALETTES["classic"])
    return palettes[index % len(palettes)]


def _category_variant_for(template, index=0):
    variants = CATEGORY_VARIANTS.get(getattr(template, "category", "") or "", CATEGORY_VARIANTS["classic"])
    return variants[index % len(variants)]


def _html_spec_for_template(template):
    slug = getattr(template, "slug", "") or ""
    if slug in CATALOG_TEMPLATE_SPECS:
        spec = CATALOG_TEMPLATE_SPECS[slug]
        return {
            **HTML_VARIANT_SPECS[spec["variant"]],
            **spec,
            "label": getattr(template, "name", "") or spec["label"],
        }
    if slug in HTML_TEMPLATE_SPECS:
        return {**HTML_TEMPLATE_SPECS[slug], "label": getattr(template, "name", "") or HTML_TEMPLATE_SPECS[slug]["label"]}

    index = _gallery_index(slug)
    if index is not None:
        variant = GALLERY_VARIANTS[index % len(GALLERY_VARIANTS)]
        return {
            **HTML_VARIANT_SPECS[variant],
            "label": getattr(template, "name", "") or f"Modele CV {index + 1:03d}",
            "palette": _palette_for(template, index),
        }

    index = _stable_index(slug or getattr(template, "name", ""))
    variant = _category_variant_for(template, index)
    return {
        **HTML_VARIANT_SPECS[variant],
        "label": getattr(template, "name", "") or "Modele CV",
        "palette": _palette_for(template, index),
    }


def supports_html_renderer(template):
    return _html_spec_for_template(template) is not None


def renderer_variant_for_template(template):
    spec = _html_spec_for_template(template)
    return spec["variant"] if spec else ""


def _safe_text(value):
    return str(value or "").strip()


def _clean_items(items):
    cleaned = []
    for item in items or []:
        if isinstance(item, dict):
            scalar_values = [value for value in item.values() if not isinstance(value, list)]
            list_values = [value for value in item.values() if isinstance(value, list)]
            if any(_safe_text(value) for value in scalar_values) or any(_clean_items(value) for value in list_values):
                cleaned.append(item)
        elif _safe_text(item):
            cleaned.append(_safe_text(item))
    return cleaned


def _media_path_from_url(value):
    marker = settings.MEDIA_URL or "/media/"
    if marker and marker in value:
        relative = value.split(marker, 1)[1]
        return Path(settings.MEDIA_ROOT) / relative
    parsed = urlparse(value)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    return None


def _photo_path(data):
    value = _safe_text(data.get("photo_url") or data.get("photo"))
    if not value:
        return None
    from_url = _media_path_from_url(value)
    if from_url and from_url.exists():
        return from_url
    direct = Path(value)
    return direct if direct.exists() else None


def _photo_uri(data):
    path = _photo_path(data)
    if not path:
        return ""
    try:
        import base64
        import mimetypes

        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except (OSError, ValueError):
        return ""


def _initials(first_name, last_name):
    letters = [_safe_text(first_name)[:1], _safe_text(last_name)[:1]]
    return "".join(letter.upper() for letter in letters if letter) or "CV"


# Icônes SVG (line-icons, stroke=currentColor) pour les coordonnées.
_SVG_OPEN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
_CONTACT_ICONS = {
    "phone": _SVG_OPEN + '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.8.4 1.6.7 2.3a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.8-1.3a2 2 0 0 1 2.1-.4c.7.3 1.5.6 2.3.7a2 2 0 0 1 1.7 2z"/></svg>',
    "email": _SVG_OPEN + '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m2 7 10 6 10-6"/></svg>',
    "address": _SVG_OPEN + '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "linkedin": _SVG_OPEN + '<rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="1.5"/><path d="M10 21v-7a3 3 0 0 1 6 0v7M10 14v7"/></svg>',
    "github": _SVG_OPEN + '<path d="M9 19c-4 1.5-4-2-6-2.5m12 4.5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.3 4.3 0 0 0-.1-3.2s-1-.3-3.4 1.3a11.6 11.6 0 0 0-6 0C6.9 3.5 5.9 3.8 5.9 3.8a4.3 4.3 0 0 0-.1 3.2A4.6 4.6 0 0 0 4.5 10c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21"/></svg>',
    "portfolio": _SVG_OPEN + '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z"/></svg>',
    "license": _SVG_OPEN + '<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="8" cy="12" r="2.2"/><path d="M14 10h4M14 14h4M4.5 17c.6-1.4 2-2 3.5-2s2.9.6 3.5 2"/></svg>',
}


def _contact_items(data):
    candidates = [
        ("Téléphone", "phone", data.get("phone")),
        ("Email", "email", data.get("email")),
        ("Ville", "address", data.get("address")),
        ("LinkedIn", "linkedin", data.get("linkedin")),
        ("GitHub", "github", data.get("github")),
        ("Portfolio", "portfolio", data.get("portfolio")),
        ("Permis", "license", data.get("driving_license")),
    ]
    return [
        {"label": label, "kind": kind, "value": _safe_text(value), "icon": _CONTACT_ICONS.get(kind, "")}
        for label, kind, value in candidates
        if _safe_text(value)
    ]


def _experience_items(data):
    # Aucune troncature : toutes les expériences et TOUTES les missions sont affichées.
    items = []
    for exp in _clean_items(data.get("experiences")):
        title = _safe_text(exp.get("job_title")) or "Experience professionnelle"
        company = _safe_text(exp.get("company"))
        period = _safe_text(exp.get("period"))
        location = _safe_text(exp.get("location"))
        meta = " | ".join(part for part in [company, location, period] if part)
        missions = [_safe_text(item) for item in exp.get("missions") or [] if _safe_text(item)]
        items.append({"title": title, "company": company, "period": period, "meta": meta, "missions": missions})
    return items


def _education_items(data):
    # Aucune troncature : TOUS les diplômes sont affichés.
    items = []
    for edu in _clean_items(data.get("education")):
        degree = _safe_text(edu.get("degree")) or "Formation"
        institution = _safe_text(edu.get("institution"))
        period = _safe_text(edu.get("period"))
        location = _safe_text(edu.get("location"))
        meta = " | ".join(part for part in [institution, location, period] if part)
        items.append({"degree": degree, "institution": institution, "period": period, "meta": meta})
    return items


def _language_items(data):
    languages = []
    for item in _clean_items(data.get("languages")):
        if isinstance(item, dict):
            label = " - ".join(part for part in [_safe_text(item.get("language")), _safe_text(item.get("level"))] if part)
        else:
            label = _safe_text(item)
        if label:
            languages.append(label)
    return languages


def _extra_sections(data):
    sections = []
    for section in _clean_items(data.get("extra_sections")):
        title = _safe_text(section.get("title"))
        items = [_safe_text(item) for item in section.get("items") or [] if _safe_text(item)]
        if title and items:
            sections.append({"title": title, "items": items})
    return sections


def _section_items(extra_sections, *tokens, fallback=None):
    normalized = [_fold(token) for token in tokens]
    for section in extra_sections:
        title = _fold(section["title"])
        if any(token in title for token in normalized):
            return section["items"]
    return fallback or []


def _section_matches(section, tokens):
    title = _fold(section.get("title") or section.get("title", ""))
    return any(token in title for token in [_fold(token) for token in tokens])


def _other_extra_sections(extra_sections):
    consumed = [
        "realisation", "réalisation", "projet", "project", "achievement",
        "certification", "certificat", "reference", "référence", "recommandation",
        "outil", "logiciel", "technique",
    ]
    return [section for section in extra_sections if not _section_matches(section, consumed)]


_LEVEL_PERCENTS = (
    (("natif", "maternel", "native", "mother"), 100),
    (("bilingue", "bilingual"), 96),
    (("excellent", "expert", "maitris"), 92),
    (("courant", "fluent", "c2", "c1"), 90),
    (("professionnel", "avance", "advanced", "tres bon"), 82),
    (("bon", "good", "b2"), 72),
    (("intermediaire", "intermediate", "b1", "moyen"), 62),
    (("scolaire", "school", "a2", "notions", "notion"), 45),
    (("debutant", "beginner", "a1", "base"), 32),
)


def _level_percent(level):
    folded = _fold(level)
    if not folded:
        return 70
    for tokens, percent in _LEVEL_PERCENTS:
        if any(token in folded for token in tokens):
            return percent
    return 70


def _language_ratings(data):
    ratings = []
    for item in _clean_items(data.get("languages")):
        if isinstance(item, dict):
            label = _safe_text(item.get("language"))
            level = _safe_text(item.get("level"))
        else:
            parts = [part.strip() for part in _safe_text(item).split(" - ", 1)]
            label = parts[0]
            level = parts[1] if len(parts) > 1 else ""
        if label:
            ratings.append({"label": label, "level": level, "percent": _level_percent(level)})
    return ratings


def _skill_ratings(items):
    percents = [95, 90, 84, 78, 72, 68]
    ratings = []
    for index, item in enumerate(items[:8]):
        label = _safe_text(item)
        if label:
            ratings.append({"label": label, "percent": percents[min(index, len(percents) - 1)]})
    return ratings


def _split_title(title):
    """Sépare l'intitulé de l'info complémentaire entre parenthèses.
    « Développeur Full-Stack (React, Django) » -> ("Développeur Full-Stack", "(React, Django)")."""
    title = _safe_text(title)
    match = re.match(r"^(.*?)\s*(\([^()]*\))\s*$", title)
    if match and match.group(1).strip():
        return match.group(1).strip(), match.group(2).strip()
    return title, ""


def _title_size_class(main_title):
    """Réduit l'intitulé pour rester sur 1-2 lignes propres, sans débordement."""
    length = len(_safe_text(main_title))
    if length > 30:
        return "title-xlong"
    if length > 20:
        return "title-long"
    return ""


def _identity_lines(data):
    lines = []
    for key in ("age", "nationality", "marital_status", "birth_date"):
        value = _safe_text(data.get(key))
        if value:
            lines.append(value)
    return lines


def _main_column_lines(data):
    """Estime le nombre de lignes occupées par la colonne principale (hors compétences)."""
    lines = 1  # intitulé / tagline
    profile_words = len(re.findall(r"\w+", _safe_text(data.get("profile"))))
    lines += max(1, profile_words // 11) if profile_words else 0
    for exp in _clean_items(data.get("experiences")):
        lines += 3  # date + poste + entreprise
        for mission in exp.get("missions") or []:
            if _safe_text(mission):
                lines += max(1, len(re.findall(r"\w+", _safe_text(mission))) // 11)
    lines += len(_clean_items(data.get("education"))) * 3
    extra = _extra_sections(data)
    projects = _section_items(extra, "projet", "project")
    certs = _section_items(extra, "certification", "certificat")
    if projects:
        lines += 2 + len(projects)
    if certs:
        lines += 2 + len(certs)
    return lines


def _side_column_lines(data):
    """Estime le nombre de lignes occupées par la colonne latérale (hors compétences)."""
    extra = _extra_sections(data)
    tools = _section_items(extra, "informatique", "outil", "logiciel", "technique")
    lines = 7  # photo + nom
    lines += len(_identity_lines(data)) + len(_contact_items(data)) + 2
    lines += len(_language_ratings(data)) * 2 + 1 if _language_ratings(data) else 0
    lines += len(_skill_ratings(tools)) * 2 + 1 if tools else 0
    lines += len(_section_items(extra, "aptitude", "qualite", "qualité")) + 1
    lines += 2 if _clean_items(data.get("hobbies")) else 0
    return lines


SIDE_CAPACITY = 42  # lignes tenant dans la colonne latérale d'une page

# Sections de la colonne principale que l'on peut déplacer vers la latérale.
_MOVABLE_SECTIONS = (
    ("skills", "Compétences"),
    ("certifications", "Certifications"),
    ("projects", "Projets réalisés"),
)


def _moved_section_data(cv, section):
    """Retourne (titre, items) de la section déplacée, depuis le contexte normalisé."""
    mapping = {
        "skills": ("Compétences", cv.get("skills") or []),
        "certifications": ("Certifications", cv.get("certifications") or []),
        "projects": ("Projets réalisés", cv.get("projects") or []),
    }
    return mapping.get(section, ("", []))


def _move_candidates(data):
    """Ordonne les sections déplaçables : on essaie d'abord celle qui remplit le
    mieux l'espace libre de la colonne latérale sans la faire déborder.
    Ainsi ce n'est pas toujours « Compétences » qui bouge — la plus adaptée est choisie."""
    cv = _normalize_data(data)
    free = SIDE_CAPACITY - _side_column_lines(data)
    present = []
    for section, _label in _MOVABLE_SECTIONS:
        items = cv.get(section) or []
        if items:
            present.append((section, len(items)))
    fits = sorted((c for c in present if c[1] <= free), key=lambda c: -c[1])
    rest = sorted((c for c in present if c[1] > free), key=lambda c: c[1])
    return [section for section, _size in fits + rest]


def _fit_class(data):
    text_score = sum(len(re.findall(r"\w+", _safe_text(data.get(key)))) for key in ["profile", "job_title"])
    item_score = 0
    for exp in _clean_items(data.get("experiences")):
        item_score += 12 + sum(min(len(re.findall(r"\w+", _safe_text(mission))), 18) for mission in exp.get("missions") or [])
    item_score += len(_clean_items(data.get("education"))) * 10
    item_score += len(_clean_items(data.get("skills"))) * 3
    item_score += len(_clean_items(data.get("languages"))) * 4
    item_score += len(_clean_items(data.get("hobbies"))) * 2
    for section in _clean_items(data.get("extra_sections")):
        item_score += 8 + len(_clean_items(section.get("items"))) * 5
    score = text_score + item_score
    if score >= 290:
        return "fit-3"
    if score >= 215:
        return "fit-2"
    if score >= 150:
        return "fit-1"
    return "fit-0"


def _fold(value):
    normalized = unicodedata.normalize("NFKD", _safe_text(value))
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _normalize_data(data):
    data = data or {}
    first_name = _safe_text(data.get("first_name"))
    last_name = _safe_text(data.get("last_name"))
    full_name = " ".join(part for part in [first_name, last_name] if part) or "Mon CV"
    skills = [_safe_text(item) for item in _clean_items(data.get("skills")) if _safe_text(item)]
    hobbies = [_safe_text(item) for item in _clean_items(data.get("hobbies")) if _safe_text(item)]
    experiences = _experience_items(data)
    education = _education_items(data)
    extra_sections = _extra_sections(data)
    projects = _section_items(extra_sections, "projet", "project")
    achievements = _section_items(extra_sections, "realisation", "réalisation", "achievement")
    certifications = _section_items(extra_sections, "certification", "certificat")
    references = _section_items(extra_sections, "reference", "référence", "recommandation")
    tools = _section_items(extra_sections, "informatique", "outil", "logiciel", "technique")
    aptitudes = _section_items(extra_sections, "aptitude", "qualite", "qualité", "savoir-etre", "savoir-être")
    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "initials": _initials(first_name, last_name),
        "job_title": _safe_text(data.get("job_title")),
        "job_title_main": _split_title(data.get("job_title"))[0],
        "job_title_extra": _split_title(data.get("job_title"))[1],
        "title_size_class": _title_size_class(_split_title(data.get("job_title"))[0]),
        "profile": _safe_text(data.get("profile")),
        "photo_uri": _photo_uri(data),
        "contact_items": _contact_items(data),
        "experiences": experiences,
        "education": education,
        "skills": skills,
        "languages": _language_items(data),
        "hobbies": hobbies,
        "extra_sections": extra_sections,
        "other_extra_sections": _other_extra_sections(extra_sections),
        "projects": projects,
        "achievements": achievements,
        "certifications": certifications,
        "references": references,
        "tools": tools,
        "tagline": _safe_text(data.get("tagline")),
        "identity_lines": _identity_lines(data),
        "language_ratings": _language_ratings(data),
        "skill_ratings": _skill_ratings(tools or skills),
        "aptitudes": (aptitudes or []),
        "fit_class": _fit_class(data),
        "moved_section": "",
        "moved_title": "",
        "moved_items": [],
    }


def render_cv_html(template, data, moved_section=None, fit_class=None):
    spec = _html_spec_for_template(template)
    if not spec:
        raise UnsupportedHTMLTemplate("Ce modèle n'a pas encore de rendu HTML/CSS.")
    cv = _normalize_data(data or {})
    if fit_class:
        cv["fit_class"] = fit_class
    if moved_section:
        title, items = _moved_section_data(cv, moved_section)
        if items:
            cv["moved_section"] = moved_section
            cv["moved_title"] = title
            cv["moved_items"] = items
    return render_to_string(
        spec["template"],
        {
            "spec": spec,
            "palette": spec["palette"],
            "cv": cv,
        },
    )


def _safe_base_name(value):
    base = re.sub(r"[^a-zA-Z0-9]+", "_", value or "cv").strip("_").lower()
    return base or "cv"


def _candidate_chromium_binaries():
    configured = _safe_text(getattr(settings, "CV_CHROMIUM_BINARY", ""))
    candidates = [configured] if configured else []
    candidates.extend(["chromium", "chromium-browser", "google-chrome", "google-chrome-stable"])
    found = []
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        resolved = str(path) if path.exists() else shutil.which(candidate)
        if resolved and resolved not in found:
            found.append(resolved)
    return found


def _subprocess_env(tmp):
    home = tmp / "home"
    runtime = tmp / "runtime"
    config = tmp / "config"
    for path in [home, runtime, config]:
        path.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update({
        "HOME": str(home),
        "XDG_RUNTIME_DIR": str(runtime),
        "XDG_CONFIG_HOME": str(config),
    })
    return env


def _pdf_with_weasyprint(html, tmp, base_name):
    try:
        from weasyprint import HTML
    except Exception as exc:
        raise HTMLRendererUnavailable(f"WeasyPrint indisponible: {exc}") from exc

    pdf_path = tmp / f"{base_name}.pdf"
    HTML(string=html, base_url=tmp.as_uri()).write_pdf(str(pdf_path))
    if not pdf_path.exists():
        raise HTMLRendererUnavailable("WeasyPrint n'a pas produit de PDF.")
    return pdf_path.read_bytes()


def _pdf_with_chromium(html_path, pdf_path, tmp):
    errors = []
    for binary in _candidate_chromium_binaries():
        command = [
            binary,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False, env=_subprocess_env(tmp))
        if completed.returncode == 0 and pdf_path.exists():
            return pdf_path.read_bytes()
        errors.append((completed.stderr or completed.stdout or f"{binary}: echec Chromium").strip())
    raise HTMLRendererUnavailable("Chromium indisponible: " + " | ".join(errors))


def _pdf_with_libreoffice(html_path, pdf_path, tmp):
    outdir = tmp / "out"
    profile = tmp / "lo-profile"
    outdir.mkdir()
    profile.mkdir()
    command = [
        getattr(settings, "LIBREOFFICE_BINARY", "soffice"),
        "--headless",
        f"-env:UserInstallation=file://{profile}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(outdir),
        str(html_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False, env=_subprocess_env(tmp))
    converted = outdir / pdf_path.name
    if completed.returncode != 0 or not converted.exists():
        message = completed.stderr or completed.stdout or "LibreOffice n'a pas produit de PDF."
        raise HTMLRendererUnavailable(message.strip())
    return converted.read_bytes()


def _preferred_engines():
    configured = _safe_text(getattr(settings, "CV_HTML_RENDERER", "auto")).lower() or "auto"
    if configured in {"off", "none", "disabled"}:
        return []
    if configured == "auto":
        return ["weasyprint", "chromium", "libreoffice"]
    return [configured]


def _convert_html_to_pdf(html, base_name):
    errors = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        safe_name = _safe_base_name(base_name)
        html_path = tmp / f"{safe_name}.html"
        pdf_path = tmp / f"{safe_name}.pdf"
        html_path.write_text(html, encoding="utf-8")

        for engine in _preferred_engines():
            try:
                if engine == "weasyprint":
                    return _pdf_with_weasyprint(html, tmp, safe_name)
                if engine == "chromium":
                    return _pdf_with_chromium(html_path, pdf_path, tmp)
                if engine == "libreoffice":
                    return _pdf_with_libreoffice(html_path, pdf_path, tmp)
                errors.append(f"Moteur inconnu: {engine}")
            except Exception as exc:
                errors.append(str(exc))
        raise HTMLRendererUnavailable("Aucun moteur HTML/PDF disponible. " + " | ".join(errors))


def _pdf_page_count(pdf_bytes):
    try:
        from pypdf import PdfReader

        return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception:
        return 1


def _supports_section_move(template):
    spec = _html_spec_for_template(template)
    return bool(spec) and spec.get("variant") == "chic"


# Niveaux de compression (police + espaces), du plus aéré au plus dense.
_FIT_LEVELS = ["fit-0", "fit-1", "fit-2", "fit-3", "fit-4", "fit-5", "fit-6"]


def _best_layout(template, data, base_name):
    """« Shrink-to-fit » : affiche TOUTES les infos, puis réduit progressivement
    tailles + espaces, et au besoin déplace une section vers la colonne latérale,
    jusqu'à tenir sur UNE page — sans jamais supprimer d'information."""
    # Point de départ : un cran sous le niveau estimé (on évite de sur-compresser
    # si l'estimation surévalue la densité ; on remontera si besoin).
    start = _fit_class(data)
    try:
        start_index = max(0, _FIT_LEVELS.index(start) - 1)
    except ValueError:
        start_index = 0

    html = render_cv_html(template, data, fit_class=_FIT_LEVELS[start_index])
    pdf = _convert_html_to_pdf(html, base_name)
    if not _supports_section_move(template) or _pdf_page_count(pdf) <= 1:
        return html, pdf

    best_html, best_pdf, best_pages = html, pdf, _pdf_page_count(pdf)

    # 1) Compression progressive (sans déplacer de section).
    for level in _FIT_LEVELS[start_index + 1:]:
        alt_html = render_cv_html(template, data, fit_class=level)
        alt_pdf = _convert_html_to_pdf(alt_html, base_name)
        pages = _pdf_page_count(alt_pdf)
        if pages < best_pages:
            best_html, best_pdf, best_pages = alt_html, alt_pdf, pages
        if pages <= 1:
            return best_html, best_pdf

    # 2) Toujours trop dense : on déplace une section vers la colonne latérale,
    #    au niveau de compression le plus fort, et on garde la version à 1 page.
    for section in _move_candidates(data):
        alt_html = render_cv_html(template, data, moved_section=section, fit_class="fit-6")
        if alt_html == best_html:
            continue
        alt_pdf = _convert_html_to_pdf(alt_html, base_name)
        pages = _pdf_page_count(alt_pdf)
        if pages < best_pages:
            best_html, best_pdf, best_pages = alt_html, alt_pdf, pages
        if pages <= 1:
            return best_html, best_pdf

    return best_html, best_pdf


def render_html_template_pdf_bytes(template, data, base_name="cv"):
    return _best_layout(template, data, base_name)[1]


def resolve_cv_html(template, data, base_name="preview"):
    """HTML avec placement résolu, pour l'aperçu (le même que le PDF final).
    On ne mesure (rendu PDF) que si le contenu peut déborder, afin de garder
    l'aperçu instantané sur les CV légers."""
    if not _supports_section_move(template) or _main_column_lines(data) <= 20:
        return render_cv_html(template, data)
    return _best_layout(template, data, base_name)[0]


def render_html_cv_pdf_bytes(cv, base_name=None):
    return render_html_template_pdf_bytes(
        cv.template,
        cv.data or {},
        base_name=base_name or getattr(cv, "title", "cv") or "cv",
    )


def render_html_template_preview_png_bytes(template, data, base_name="preview"):
    pdf_bytes = render_html_template_pdf_bytes(template, data, base_name=base_name)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        pdf_path = tmp / f"{_safe_base_name(base_name)}.pdf"
        output_prefix = tmp / "preview"
        pdf_path.write_bytes(pdf_bytes)
        command = ["pdftoppm", "-singlefile", "-png", "-r", "144", str(pdf_path), str(output_prefix)]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        png_path = tmp / "preview.png"
        if completed.returncode != 0 or not png_path.exists():
            message = completed.stderr or completed.stdout or "Conversion PDF vers PNG impossible."
            raise HTMLRendererUnavailable(message.strip())
        return png_path.read_bytes()
