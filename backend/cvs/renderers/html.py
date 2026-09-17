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

from cvs.system_bins import candidate_libreoffice_binaries, libreoffice_not_found_message


class UnsupportedHTMLTemplate(Exception):
    """Le modèle choisi n'a pas encore de renderer HTML/CSS."""


class HTMLRendererUnavailable(RuntimeError):
    """Aucun moteur HTML vers PDF n'a pu produire le document."""


HTML_VARIANT_SPECS = {
    "prestige": {
        "template": "cvs/html_renderers/prestige.html",
        "variant": "prestige",
    },
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
    "prestige-orange": {"variant": "prestige", "palette": CHIC_PALETTES["anthracite"], "label": "Prestige Orange"},
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


# ---------- Contraste : icônes et marqueurs toujours visibles sur leur fond ----------

def _hex_to_rgb(value):
    value = _safe_text(value).lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (0, 0, 0)


def _luminance(color):
    def channel(component):
        component /= 255
        return component / 12.92 if component <= 0.03928 else ((component + 0.055) / 1.055) ** 2.4

    red, green, blue = _hex_to_rgb(color)
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def _contrast_ratio(color_a, color_b):
    lum_a, lum_b = _luminance(color_a), _luminance(color_b)
    return (max(lum_a, lum_b) + 0.05) / (min(lum_a, lum_b) + 0.05)


def _visible_on(background, preferred, light="#ffffff", dark="#1f2937", minimum=2.6):
    """Garde `preferred` si le contraste avec le fond suffit ; sinon bascule vers
    blanc (fond sombre) ou une teinte sombre (fond clair). Évite les icônes
    invisibles quand l'accent est proche du fond (ex. bleu sur bleu marine)."""
    if _contrast_ratio(preferred, background) >= minimum:
        return preferred
    return light if _contrast_ratio(light, background) >= _contrast_ratio(dark, background) else dark


def _readable_palette(palette):
    """Enrichit la palette de couleurs dérivées garanties lisibles :
    - on_dark : accent (ou substitut) visible sur le fond sombre de la sidebar ;
    - on_accent : texte/icône visible sur un aplat couleur accent ;
    - on_light : accent (ou substitut) visible sur fond blanc.
    Seuil on_dark à 3.5 : sous ce ratio, les petites icônes paraissent noires à
    l'impression (ex. bleu azur 2.8 sur marine) — on bascule alors en blanc."""
    enriched = dict(palette or {})
    accent = enriched.get("accent", "#2563eb")
    dark = enriched.get("dark", "#111827")
    enriched.setdefault("on_dark", _visible_on(dark, accent, minimum=3.5))
    enriched.setdefault("on_accent", _visible_on(accent, "#ffffff", dark="#111827"))
    enriched.setdefault("on_light", _visible_on("#ffffff", accent, dark=dark))
    return enriched


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


# Icônes SVG des hobbies (line-icons, stroke=currentColor), appariées par mot-clé.
_HOBBY_ICONS = (
    (("voyage", "travel", "avion"), _SVG_OPEN + '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/></svg>'),
    (("lecture", "livre", "reading"), _SVG_OPEN + '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>'),
    (("foot", "sport", "basket", "gym", "fitness", "course", "running", "tennis"), _SVG_OPEN + '<circle cx="12" cy="12" r="10"/><path d="m12 6 5.7 4.1-2.2 6.7H8.5L6.3 10.1z"/></svg>'),
    (("musique", "music", "chant", "danse", "dance"), _SVG_OPEN + '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>'),
    (("cuisine", "cooking", "patisserie", "pâtisserie"), _SVG_OPEN + '<path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4z"/></svg>'),
    (("natation", "swim", "plongee", "plongée"), _SVG_OPEN + '<path d="M2 12c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2M2 18c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2"/></svg>'),
    (("echec", "échec", "chess", "jeu"), _SVG_OPEN + '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18M3 9h18M3 15h18"/></svg>'),
    (("benevolat", "bénévolat", "volontariat", "association", "caritatif"), _SVG_OPEN + '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>'),
    (("veille", "tech", "informatique", "code"), _SVG_OPEN + '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>'),
    (("photo",), _SVG_OPEN + '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>'),
    (("cinema", "cinéma", "film", "serie", "série"), _SVG_OPEN + '<rect x="2" y="2" width="20" height="20" rx="2.2"/><path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 7h5M17 17h5"/></svg>'),
)
_HOBBY_DEFAULT_ICON = _SVG_OPEN + '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/></svg>'


def _hobby_items(data):
    items = []
    for hobby in _clean_items(data.get("hobbies")):
        label = _safe_text(hobby)
        folded = _fold(label)
        icon = next((svg for tokens, svg in _HOBBY_ICONS if any(token in folded for token in tokens)), _HOBBY_DEFAULT_ICON)
        items.append({"label": label, "icon": icon})
    return items


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


def _project_items(data):
    """Projets réalisés, structurés comme une expérience (titre, sous-titre,
    période, missions) avec une distinction/prix optionnelle (badge trophée).
    Deux liens indépendants : celui du site/projet (rend le titre cliquable) et
    celui du prix (rend le badge cliquable). Si le site n'est pas en ligne,
    `link_note` sert de justification texte (ex. « Déploiement en cours »,
    « Démo locale »), affichée à la place ou en complément du lien."""
    items = []
    for proj in _clean_items(data.get("projects")):
        title = _safe_text(proj.get("title")) or _safe_text(proj.get("job_title"))
        if not title:
            continue
        subtitle = _safe_text(proj.get("subtitle"))
        period = _safe_text(proj.get("period"))
        award = _safe_text(proj.get("award"))
        award_link = _safe_text(proj.get("award_link") or proj.get("award_url"))
        link = _safe_text(proj.get("link") or proj.get("url") or proj.get("site"))
        link_note = _safe_text(proj.get("link_note") or proj.get("status"))
        missions = [_safe_text(item) for item in proj.get("missions") or [] if _safe_text(item)]
        items.append({
            "title": title, "subtitle": subtitle, "period": period, "missions": missions,
            "award": award, "award_link": award_link, "link": link, "link_note": link_note,
        })
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
        raw_items = section.get("items") or []
        items = []
        for item in raw_items:
            if isinstance(item, dict):
                # Structured item (déjà label/subtitle/link) : conservé tel quel.
                label = _safe_text(item.get("label") or item.get("title") or item.get("name") or item.get("degree") or item.get("project") or "")
                subtitle = _safe_text(item.get("subtitle") or item.get("sub") or item.get("meta") or "")
                link = _safe_text(item.get("link") or item.get("url") or item.get("verify_url") or "")
                if label:
                    entry = {"label": label}
                    if subtitle:
                        entry["subtitle"] = subtitle
                    if link:
                        entry["link"] = link
                    items.append(entry)
                    continue
                # Dict sans champ label reconnu : on retente à partir de ses valeurs textuelles.
                s = " ".join(_safe_text(v) for v in item.values() if not isinstance(v, (list, dict)))
            else:
                # Élément texte simple (cas le plus courant : saisie manuelle de
                # l'utilisateur) — SANS ce branchement, ces éléments étaient
                # silencieusement ignorés et la section ressortait vide.
                s = _safe_text(item)

            if not s:
                continue
            # Détecte une URL inline et sépare label / subtitle si présent.
            url_match = re.search(r"(https?://\S+|www\.\S+)", s)
            link = ""
            if url_match:
                link = url_match.group(0)
                s = s.replace(link, "").strip(" ()")

            # Séparer label et subtitle par '—' ou '-' ou '–'.
            parts = re.split(r"\s*[—–-]\s*", s, maxsplit=1)
            label = parts[0].strip()
            subtitle = parts[1].strip() if len(parts) > 1 else ""
            if label:
                entry = {"label": label}
                if subtitle:
                    entry["subtitle"] = subtitle
                if link:
                    entry["link"] = link
                items.append(entry)
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
        "informatique", "outil", "logiciel", "technique",
        "aptitude", "qualite", "qualité", "savoir-etre", "savoir-être",
        "prix", "distinction", "award", "awards", "distinctions",
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
        label = _safe_text(item.get("label")) if isinstance(item, dict) else _safe_text(item)
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
    structured_projects = _project_items(data)
    if structured_projects:
        for proj in structured_projects:
            lines += 3  # période + titre + sous-titre
            for mission in proj["missions"]:
                lines += max(1, len(re.findall(r"\w+", mission)) // 11)
            if proj["award"]:
                lines += 1
    else:
        legacy_projects = _section_items(_extra_sections(data), "projet", "project")
        if legacy_projects:
            lines += 2 + len(legacy_projects)
    certs = _section_items(_extra_sections(data), "certification", "certificat")
    if certs:
        lines += 2 + len(certs)
    return lines


def _side_column_lines(data):
    """Estime le nombre de lignes occupées par la colonne latérale (hors compétences)."""
    extra = _extra_sections(data)
    tools = _clean_items(data.get("tools")) or _section_items(
        extra, "informatique", "outil", "logiciel", "technique"
    )
    lines = 7  # photo + nom
    lines += len(_identity_lines(data)) + len(_contact_items(data)) + 2
    lines += len(_language_ratings(data)) * 2 + 1 if _language_ratings(data) else 0
    lines += len(_skill_ratings(tools)) * 2 + 1 if tools else 0
    lines += len(_section_items(extra, "aptitude", "qualite", "qualité")) + 1
    lines += 2 if _clean_items(data.get("hobbies")) else 0
    return lines


SIDE_CAPACITY = 42  # lignes tenant dans la colonne latérale d'une page

# Hauteur physique approximative d'une ligne dans chaque colonne (mm) : la
# latérale est en ~9pt serré, la principale en ~10pt aéré. Sert à comparer le
# remplissage RÉEL des deux colonnes (pas juste un nombre de lignes brut).
_MAIN_LINE_MM = 4.7
_SIDE_LINE_MM = 4.1

# Cible d'équilibre EN PROPORTION (pas en mm bruts) : on vise un partage
# 50/50 du remplissage entre les deux colonnes, et on tolère un écart
# jusqu'à 60/40 dans le pire des cas — jamais plus. Raisonner en proportion
# (plutôt qu'en écart absolu) rend le réglage stable quel que soit le
# volume du CV : un petit CV et un CV très dense visent le même équilibre
# relatif, pas le même nombre de mm.
_BALANCE_TARGET_RATIO = 0.5
_BALANCE_MAX_SKEW = 0.6

# Jamais plus de 3 sections déplacées en mode esthétique : au-delà, la
# latérale devient un fourre-tout illisible et la principale perd trop de
# substance narrative pour un gain d'équilibre marginal.
_BALANCE_MAX_MOVES = 3


def _side_fill_ratio(main_lines, side_lines):
    """Part de la latérale dans le remplissage total des deux colonnes
    (0.5 = parfaitement équilibré, >0.5 = latérale plus chargée que la
    principale). Raisonne en mm réels (pas en nombre de lignes brut) car les
    deux colonnes n'ont ni la même largeur ni la même taille de police."""
    main_mm = max(main_lines, 0) * _MAIN_LINE_MM
    side_mm = max(side_lines, 0) * _SIDE_LINE_MM
    total_mm = main_mm + side_mm
    return side_mm / total_mm if total_mm else _BALANCE_TARGET_RATIO


def _section_side_lines(items):
    """Lignes qu'occuperait une section déplacée dans la colonne latérale
    (titre + items, avec retours à la ligne probables sur les libellés longs)."""
    lines = 2  # titre + respiration
    for item in items:
        label = item.get("label", "") if isinstance(item, dict) else _safe_text(item)
        lines += max(1, len(_safe_text(label)) // 34 + 1)
    return lines


def _movable_candidates(cv):
    """Sections COMPACTES (listes courtes) éligibles au déplacement vers la
    latérale : compétences, certifications, réalisations, références, et
    chaque section personnalisée non reconnue. Jamais les expériences,
    formations ou projets — ce sont des blocs narratifs qui doivent rester
    entiers et lisibles dans la colonne principale."""
    candidates = []
    if cv.get("skills"):
        candidates.append({"key": "skills", "title": "Compétences", "items": cv["skills"]})
    if cv.get("certifications"):
        candidates.append({"key": "certifications", "title": "Certifications", "items": cv["certifications"]})
    if cv.get("achievements"):
        candidates.append({"key": "achievements", "title": "Réalisations", "items": cv["achievements"]})
    if cv.get("references"):
        candidates.append({"key": "references", "title": "Références", "items": cv["references"]})
    if cv.get("legacy_projects"):
        candidates.append({"key": "legacy_projects", "title": "Projets réalisés", "items": cv["legacy_projects"]})
    for index, section in enumerate(cv.get("other_extra_sections") or []):
        if section.get("items"):
            candidates.append({"key": f"other:{index}", "title": section["title"], "items": section["items"]})
    return candidates


def _auto_balance_sections(cv, data, force_fit=False):
    """Équilibrage MULTI-SECTIONS des deux colonnes par un algorithme du
    « meilleur ajustement » (best-fit), déterministe, rapide et reproductible
    — délibérément SANS appel IA au rendu : un rendu doit rester instantané et
    stable d'un aperçu à l'autre, ce qu'un appel modèle ne garantit pas.

    RÈGLES PRÉCISES (dans cet ordre, à chaque itération) :
    1. Seules les sections COMPACTES sont candidates (cf. _movable_candidates)
       — jamais les expériences, formations ou projets.
    2. La cible est un partage 50/50 du remplissage entre les deux colonnes
       (_BALANCE_TARGET_RATIO) ; on ne déclenche AUCUN déplacement si on est
       déjà entre 40/60 et 60/40 (_BALANCE_MAX_SKEW) : un léger déséquilibre
       est normal et imperceptible, inutile de bouger du contenu pour le
       principe — et ça garde le rendu STABLE d'un aperçu à l'autre.
       Raisonner en proportion plutôt qu'en écart absolu rend le réglage
       identique pour un petit CV et un CV très dense.
    3. Parmi les candidats qui tiennent encore dans l'espace latéral libre,
       on choisit celui qui rapproche le PLUS le ratio de 50/50 (meilleur
       ajustement selon sa taille). Pas de plafond dur à 60/40 ici : si le
       seul candidat disponible ramène le ratio à, disons, 61/39, c'est quand
       même accepté tant que ça rapproche du 50/50 — rester au déséquilibre
       de départ sous prétexte qu'aucun candidat ne « rentre » pile dans la
       fourchette serait pire, pas mieux.
    4. Un déplacement n'est accepté que s'il rapproche RÉELLEMENT du 50/50 —
       jamais de mouvement qui empire ou n'apporte rien (stabilité avant
       tout : pas de va-et-vient inutile entre deux rendus).
    5. On s'arrête dès qu'on est dans la fourchette cible, qu'il n'y a plus
       de candidat qui tienne dans l'espace libre ou qui aide encore, ou
       après _BALANCE_MAX_MOVES déplacements (mode esthétique uniquement —
       en mode force_fit, aucune limite de nombre : on prend tout ce qui
       peut aider à tenir sur une page).

    Renvoie la liste des sections déplacées (dicts {key, title, items}).
    """
    remaining = _movable_candidates(cv)
    if not remaining:
        return []

    main_lines = _main_column_lines(data)
    side_lines = _side_column_lines(data)
    moved = []
    max_moves = len(remaining) if force_fit else _BALANCE_MAX_MOVES
    skew_floor = 1 - _BALANCE_MAX_SKEW

    for _ in range(max_moves):
        ratio = _side_fill_ratio(main_lines, side_lines)
        if not force_fit and skew_floor <= ratio <= _BALANCE_MAX_SKEW:
            break
        free = SIDE_CAPACITY - side_lines
        if free < 1 or not remaining:
            break

        scored = []
        for candidate in remaining:
            side_gain_lines = _section_side_lines(candidate["items"])
            if side_gain_lines > free:
                continue
            main_loss_lines = 2 + len(candidate["items"])
            new_ratio = _side_fill_ratio(main_lines - main_loss_lines, side_lines + side_gain_lines)
            # Meilleur ajustement : le plus proche possible de 50/50. Pas de
            # plafond dur ici — un candidat qui dépasse légèrement 60/40 de
            # l'autre côté reste accepté s'il RAPPROCHE quand même de 50/50
            # (cf. le test juste après la boucle) : rester au pire déséquilibre
            # de départ sous prétexte qu'aucun candidat ne « rentre » pile dans
            # la fourchette serait pire, pas mieux. En mode force_fit, priorité
            # au plus gros gain (libérer un maximum de hauteur en colonne
            # principale pour tenir sur une page).
            fit_score = abs(_BALANCE_TARGET_RATIO - new_ratio) if not force_fit else -side_gain_lines
            scored.append((fit_score, new_ratio, side_gain_lines, main_loss_lines, candidate))

        if not scored:
            break
        scored.sort(key=lambda row: row[0])
        _, new_ratio, side_gain_lines, main_loss_lines, chosen = scored[0]

        if not force_fit and abs(new_ratio - _BALANCE_TARGET_RATIO) >= abs(ratio - _BALANCE_TARGET_RATIO):
            break  # ce déplacement n'améliore rien : on s'arrête là (stabilité)

        moved.append(chosen)
        remaining.remove(chosen)
        main_lines -= main_loss_lines
        side_lines += side_gain_lines

    return moved


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
    explicit_tools = [_safe_text(item) for item in _clean_items(data.get("tools")) if _safe_text(item)]
    hobbies = [_safe_text(item) for item in _clean_items(data.get("hobbies")) if _safe_text(item)]
    experiences = _experience_items(data)
    education = _education_items(data)
    extra_sections = _extra_sections(data)
    # Projets structurés (titre, sous-titre, période, missions, prix) : nouveau
    # format riche, affiché en timeline. Un CV plus ancien qui n'a qu'une
    # section libre "Projets" (simples puces, sans titre/période individuels)
    # NE DOIT JAMAIS être forcé dans ce format — une puce n'est pas un projet à
    # part entière (bug corrigé : ça produisait de fausses fiches-projet avec
    # la puce entière en guise de titre en majuscules, sans sous-titre ni
    # période). Ce cas passe dans `legacy_projects`, affiché en liste simple.
    projects = _project_items(data)
    legacy_projects = [] if projects else _section_items(
        extra_sections, "projet", "project", "prix", "distinction", "award", "awards", "distinctions"
    )
    achievements = _section_items(extra_sections, "realisation", "réalisation", "achievement")
    certifications = _section_items(extra_sections, "certification", "certificat")
    references = _section_items(extra_sections, "reference", "référence", "recommandation")
    tools = explicit_tools or _section_items(
        extra_sections, "informatique", "outil", "logiciel", "technique"
    )
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
        "hobby_items": _hobby_items(data),
        "extra_sections": extra_sections,
        "other_extra_sections": _other_extra_sections(extra_sections),
        "projects": projects,
        "legacy_projects": legacy_projects,
        "achievements": achievements,
        "certifications": certifications,
        "references": references,
        "tools": tools,
        "tagline": _safe_text(data.get("tagline")),
        "identity_lines": _identity_lines(data),
        "language_ratings": _language_ratings(data),
        # Informatique et compétences sont deux rubriques indépendantes. Un CV
        # sans outils renseignés ne doit jamais recopier ses compétences sous
        # un faux titre « Informatiques ».
        "skill_ratings": _skill_ratings(tools),
        "aptitudes": (aptitudes or []),
        "fit_class": _fit_class(data),
        "moved_sections": [],
    }


def _bake_icon_colors(cv, palette):
    """Remplace `currentColor` par la couleur hexadécimale réelle DANS le SVG.
    WeasyPrint n'hérite pas fiablement de `color` (CSS) vers `currentColor`
    (SVG) pour du HTML brut inséré via |safe : les icônes ressortaient toutes
    noires au rendu PDF, quelle que soit la couleur déclarée en CSS. On fixe
    donc la couleur directement dans le balisage, indépendamment de l'héritage."""
    contact_color = palette.get("on_dark", "#ffffff")
    for item in cv.get("contact_items") or []:
        if item.get("icon"):
            item["icon"] = item["icon"].replace("currentColor", contact_color)
    # Hobbies (prestige) : icônes sombres fixes sur fond blanc (cf. .hico en CSS).
    hobby_color = "#2c2d2f"
    for item in cv.get("hobby_items") or []:
        if item.get("icon"):
            item["icon"] = item["icon"].replace("currentColor", hobby_color)


def render_cv_html(template, data, moved_sections=None, fit_class=None, force_fit=False):
    spec = _html_spec_for_template(template)
    if not spec:
        raise UnsupportedHTMLTemplate("Ce modèle n'a pas encore de rendu HTML/CSS.")
    cv = _normalize_data(data or {})
    if fit_class:
        cv["fit_class"] = fit_class
    # Équilibrage automatique des colonnes (sauf déplacement déjà imposé par le
    # moteur « 1 page ») : redistribue les sections compactes (compétences,
    # certifications, réalisations, références, sections perso) vers la
    # latérale selon des règles précises de meilleur ajustement — voir
    # _auto_balance_sections. Jamais un côté presque vide face à l'autre plein.
    if moved_sections is None and spec.get("variant") in {"chic", "prestige"}:
        moved_sections = _auto_balance_sections(cv, data or {}, force_fit=force_fit)
    if moved_sections:
        moved_keys = {candidate["key"] for candidate in moved_sections}
        cv["moved_sections"] = [{"title": c["title"], "items": c["items"]} for c in moved_sections]
        # Retire les sections déplacées de la colonne principale — les
        # templates n'ont ainsi plus besoin de savoir CE QUI a été déplacé.
        for key in ("skills", "certifications", "achievements", "references", "legacy_projects"):
            if key in moved_keys:
                cv[key] = []
        cv["other_extra_sections"] = [
            section for index, section in enumerate(cv["other_extra_sections"])
            if f"other:{index}" not in moved_keys
        ]
    palette = _readable_palette(spec["palette"])
    _bake_icon_colors(cv, palette)
    return render_to_string(
        spec["template"],
        {
            "spec": spec,
            "palette": palette,
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
    converted = outdir / pdf_path.name
    binaries = candidate_libreoffice_binaries()
    if not binaries:
        raise HTMLRendererUnavailable(libreoffice_not_found_message())

    errors = []
    for binary in binaries:
        converted.unlink(missing_ok=True)
        command = [
            binary,
            "--headless",
            f"-env:UserInstallation=file://{profile}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(outdir),
            str(html_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False, env=_subprocess_env(tmp))
        if completed.returncode == 0 and converted.exists():
            return converted.read_bytes()
        errors.append((completed.stderr or completed.stdout or f"{binary}: conversion PDF impossible").strip())
    raise HTMLRendererUnavailable(" | ".join(errors))


def _preferred_engines():
    configured = _safe_text(getattr(settings, "CV_HTML_RENDERER", "auto")).lower() or "auto"
    if configured in {"off", "none", "disabled"}:
        return []
    if configured == "auto":
        return ["weasyprint", "chromium", "libreoffice"]
    return [configured]


def _strip_trailing_blank_pages(pdf_bytes):
    """WeasyPrint fragmente parfois une grille (`.side` à `min-height: 297mm`
    dans une `.page` à `min-height: 297mm`) en page(s) fantômes totalement
    vides quand le contenu dépasse la hauteur d'une fraction de mm — un pur
    artefact de pagination, jamais du vrai contenu qui déborde. On les
    retire pour que le compteur de pages (et le PDF livré) ne comptent que
    les pages qui contiennent réellement quelque chose."""
    try:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = reader.pages
        last = len(pages)
        while last > 1 and not (pages[last - 1].extract_text() or "").strip():
            last -= 1
        if last == len(pages):
            return pdf_bytes
        writer = PdfWriter()
        for page in pages[:last]:
            writer.add_page(page)
        buffer = io.BytesIO()
        writer.write(buffer)
        return buffer.getvalue()
    except Exception:
        return pdf_bytes


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
                    return _strip_trailing_blank_pages(_pdf_with_weasyprint(html, tmp, safe_name))
                if engine == "chromium":
                    return _strip_trailing_blank_pages(_pdf_with_chromium(html_path, pdf_path, tmp))
                if engine == "libreoffice":
                    return _strip_trailing_blank_pages(_pdf_with_libreoffice(html_path, pdf_path, tmp))
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
    return bool(spec) and spec.get("variant") in {"chic", "prestige"}


# Niveaux de compression (police + espaces), du plus aéré au plus dense.
_FIT_LEVELS = ["fit-0", "fit-1", "fit-2", "fit-3", "fit-4", "fit-5", "fit-6"]


def _best_layout(template, data, base_name, aggressive=False):
    """« Shrink-to-fit » : RÈGLE STRICTE — le CV doit tenir sur UNE page.
    Boucle de correction qui essaie, à chaque palier de compression (du plus
    lisible au plus dense), D'ABORD l'équilibrage esthétique normal des deux
    colonnes PUIS un équilibrage maximal (déplacement de tout ce qui peut
    l'être vers la latérale) — et s'arrête au tout premier réglage qui tient
    sur une page, pour rester aussi lisible que possible. Jamais de
    suppression d'information : uniquement compression + redistribution.

    `aggressive=True` (déclenché par l'utilisateur via « Mon CV fait 2 pages,
    corrige-le ») démarre la redistribution maximale dès le premier palier
    au lieu d'attendre d'avoir tout essayé sans — utile quand le rendu
    automatique n'a pas suffi et que l'utilisateur veut le maximum d'effort."""
    # Point de départ : un cran sous le niveau estimé (on évite de sur-compresser
    # si l'estimation surévalue la densité ; on remontera si besoin).
    start = _fit_class(data)
    try:
        start_index = max(0, _FIT_LEVELS.index(start) - 1)
    except ValueError:
        start_index = 0

    html = render_cv_html(template, data, fit_class=_FIT_LEVELS[start_index])
    pdf = _convert_html_to_pdf(html, base_name)
    if not _supports_section_move(template):
        return html, pdf

    if _pdf_page_count(pdf) <= 1 and not aggressive:
        # Dé-escalade : l'estimation sur-évalue parfois la densité, ce qui
        # « reconcentrait » inutilement le CV. Tant que la page tient, on
        # essaie plus AÉRÉ et on garde la version la plus confortable.
        for index in range(start_index - 1, -1, -1):
            alt_html = render_cv_html(template, data, fit_class=_FIT_LEVELS[index])
            alt_pdf = _convert_html_to_pdf(alt_html, base_name)
            if _pdf_page_count(alt_pdf) > 1:
                break
            html, pdf = alt_html, alt_pdf
        return html, pdf

    best_html, best_pdf, best_pages = html, pdf, _pdf_page_count(pdf)
    best_balanced = False

    # Boucle de correction : à chaque palier, essaie sans déplacement forcé
    # PUIS avec (force_fit). S'arrête dès qu'une page suffit. En mode
    # `aggressive`, on inclut aussi le palier de départ (on ne se contente pas
    # de la version « lisible » initiale, l'objectif prioritaire est 1 page).
    # Si aucun palier ne fait tenir sur une page, on ne retombe jamais sur le
    # tout premier rendu (souvent déséquilibré, cf. colonne latérale à moitié
    # vide alors que la principale déborde) : à nombre de pages égal, une
    # version qui a redistribué du contenu (force_fit) l'emporte toujours sur
    # une version qui n'a rien déplacé.
    levels = _FIT_LEVELS[start_index:] if aggressive else _FIT_LEVELS[start_index + 1:]
    for level in levels:
        for force in (False, True):
            alt_html = render_cv_html(template, data, fit_class=level, force_fit=force)
            if alt_html == best_html:
                continue
            alt_pdf = _convert_html_to_pdf(alt_html, base_name)
            pages = _pdf_page_count(alt_pdf)
            if pages < best_pages or (pages == best_pages and force and not best_balanced):
                best_html, best_pdf, best_pages = alt_html, alt_pdf, pages
                best_balanced = force
            if pages <= 1:
                return best_html, best_pdf

    return best_html, best_pdf


def render_html_template_pdf_bytes(template, data, base_name="cv", aggressive=False):
    return _best_layout(template, data, base_name, aggressive=aggressive)[1]


def resolve_cv_html(template, data, base_name="preview"):
    """HTML avec placement résolu, pour l'aperçu (le même que le PDF final).
    On ne mesure (rendu PDF) que si le contenu peut déborder, afin de garder
    l'aperçu instantané sur les CV légers."""
    if not _supports_section_move(template) or _main_column_lines(data) <= 20:
        return render_cv_html(template, data)
    aggressive = bool((data or {}).get("aggressive_fit"))
    return _best_layout(template, data, base_name, aggressive=aggressive)[0]


def render_html_cv_pdf_bytes(cv, base_name=None):
    data = cv.data or {}
    return render_html_template_pdf_bytes(
        cv.template,
        data,
        base_name=base_name or getattr(cv, "title", "cv") or "cv",
        aggressive=bool(data.get("aggressive_fit")),
    )


# ---------- Lettre de motivation : rendu accordé au modèle du CV ----------

_LETTER_FALLBACK_PALETTE = {"accent": "#0f766e", "dark": "#1f2937"}

_FRENCH_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def _letter_palette(template):
    """Palette de la lettre : celle du modèle du CV quand il a un rendu HTML,
    pour que CV et lettre forment un dossier visuellement cohérent."""
    try:
        spec = _html_spec_for_template(template)
        if spec:
            palette = _readable_palette(spec["palette"])
            return {
                "accent": palette.get("accent") or _LETTER_FALLBACK_PALETTE["accent"],
                "dark": palette.get("dark") or _LETTER_FALLBACK_PALETTE["dark"],
            }
    except Exception:
        pass
    return dict(_LETTER_FALLBACK_PALETTE)


def _parse_cover_letter_text(text):
    """Sépare la ligne « Objet : … » (si présente) du corps, et découpe le corps
    en paragraphes sur les lignes vides. Robuste aux éditions manuelles."""
    lines = str(text or "").replace("\r", "").strip().split("\n")
    objet = ""
    if lines and re.match(r"^\s*objet\s*:", lines[0], re.I):
        objet = re.sub(r"^\s*objet\s*:\s*", "", lines[0], flags=re.I).strip()
        lines = lines[1:]
    body = "\n".join(lines).strip()
    paragraphs = [re.sub(r"\s*\n\s*", " ", block).strip() for block in re.split(r"\n\s*\n", body) if block.strip()]
    return objet, paragraphs


def render_cover_letter_html(cv):
    from django.utils import timezone

    data = cv.data or {}
    objet, paragraphs = _parse_cover_letter_text(cv.cover_letter)
    full_name = " ".join(part for part in [_safe_text(data.get("first_name")), _safe_text(data.get("last_name"))] if part)
    contact_items = [
        item for item in [
            _safe_text(data.get("phone")),
            _safe_text(data.get("email")),
            _safe_text(data.get("address")),
        ] if item
    ]
    today = timezone.localdate()
    city = _safe_text(data.get("address")).split(",")[0].strip()
    date_value = f"le {today.day} {_FRENCH_MONTHS[today.month - 1]} {today.year}"
    date_line = f"{city}, {date_value}" if city and len(city) <= 40 else date_value.capitalize()
    return render_to_string(
        "cvs/html_renderers/letter.html",
        {
            "palette": _letter_palette(cv.template),
            "letter": {
                "full_name": full_name or "Candidat",
                "job_title": _safe_text(data.get("job_title")),
                "contact_items": contact_items,
                "date_line": date_line,
                "objet": objet,
                "paragraphs": paragraphs,
            },
        },
    )


def render_cover_letter_pdf_bytes(cv, base_name=None):
    html = render_cover_letter_html(cv)
    return _convert_html_to_pdf(html, base_name or f"lettre-motivation-{cv.pk}")


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
