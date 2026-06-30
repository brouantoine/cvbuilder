from copy import deepcopy
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageDraw, ImageFont, ImageOps

from templates.models import CVTemplate


A4_SIZE = (1200, 1697)
THUMB_SIZE = (320, 448)

PALETTES = [
    {"accent": "#1d4ed8", "dark": "#111827", "soft": "#eff6ff", "muted": "#64748b"},
    {"accent": "#0f766e", "dark": "#0f172a", "soft": "#ecfdf5", "muted": "#64748b"},
    {"accent": "#9f1239", "dark": "#1f2937", "soft": "#fff1f2", "muted": "#6b7280"},
    {"accent": "#7c2d12", "dark": "#1c1917", "soft": "#fff7ed", "muted": "#78716c"},
    {"accent": "#4338ca", "dark": "#111827", "soft": "#eef2ff", "muted": "#64748b"},
    {"accent": "#0e7490", "dark": "#0f172a", "soft": "#ecfeff", "muted": "#64748b"},
    {"accent": "#4d7c0f", "dark": "#1f2937", "soft": "#f7fee7", "muted": "#64748b"},
    {"accent": "#be123c", "dark": "#18181b", "soft": "#fff1f2", "muted": "#71717a"},
    {"accent": "#374151", "dark": "#111827", "soft": "#f3f4f6", "muted": "#6b7280"},
    {"accent": "#b45309", "dark": "#1f2937", "soft": "#fffbeb", "muted": "#78716c"},
]

CATEGORIES = ["classic", "modern", "creative", "minimal", "colorful"]

STYLE_LABELS = {
    "classic": "Classique",
    "modern": "Moderne",
    "creative": "Standard",
    "minimal": "Minimaliste",
    "colorful": "Coloré",
}

PHOTO_IDENTITIES = [
    {"first": "Awa", "last": "Kone"},
    {"first": "Kevin", "last": "Amani"},
    {"first": "Moussa", "last": "Traore"},
    {"first": "Isaac", "last": "Kouadio"},
    {"first": "Samuel", "last": "N'Da"},
    {"first": "Yann", "last": "Brou"},
    {"first": "Sarah", "last": "Bamba"},
    {"first": "Junior", "last": "Diallo"},
]

ROLES = [
    "Ingenieur DevOps",
    "Cheffe de projet digital",
    "Auditeur interne",
    "Responsable commercial",
    "Data analyst",
    "Chargee de recrutement",
    "Technicien reseaux",
    "Comptable confirme",
    "Designer UI",
    "Ingenieur genie civil",
    "Juriste d'entreprise",
    "Assistant administratif",
    "Consultant support client",
    "Responsable logistique",
    "Developpeur full stack",
]

COMPANIES = [
    "NOVA Consulting",
    "Atlas Digital",
    "Groupe Horizon",
    "Impact Services",
    "Koral Solutions",
    "Afrik Data Lab",
]

FONT_REGULAR = None
FONT_BOLD = None


def _font_path(bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return str(path)
    return None


def _font(size, bold=False):
    global FONT_REGULAR, FONT_BOLD
    if bold:
        if FONT_BOLD is None:
            path = _font_path(bold=True)
            FONT_BOLD = ImageFont.truetype(path, size) if path else ImageFont.load_default()
        return ImageFont.truetype(_font_path(bold=True), size) if _font_path(bold=True) else FONT_BOLD
    if FONT_REGULAR is None:
        path = _font_path()
        FONT_REGULAR = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    return ImageFont.truetype(_font_path(), size) if _font_path() else FONT_REGULAR


def _rgb(hex_color):
    value = hex_color.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _text_width(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _wrap(draw, text, font, max_width, max_lines=None):
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if max_lines and len(lines) >= max_lines:
            break
    if current and (not max_lines or len(lines) < max_lines):
        lines.append(current)
    return lines


def _draw_wrapped(draw, xy, text, font, fill, max_width, line_gap=8, max_lines=None):
    x, y = xy
    line_height = font.size + line_gap
    for line in _wrap(draw, text, font, max_width, max_lines=max_lines):
        draw.text((x, y), line, fill=fill, font=font)
        y += line_height
    return y


def _draw_section(draw, title, x, y, width, palette, body=None, compact=False):
    title_font = _font(25 if not compact else 22, bold=True)
    body_font = _font(20 if not compact else 18)
    draw.text((x, y), title.upper(), fill=palette["accent"], font=title_font)
    draw.line((x, y + 35, x + min(width, 260), y + 35), fill=palette["accent"], width=3)
    y += 58
    for paragraph in body or []:
        if isinstance(paragraph, tuple):
            label, value = paragraph
            draw.text((x, y), label, fill="#111827", font=_font(20 if not compact else 18, bold=True))
            y += 28
            y = _draw_wrapped(draw, (x, y), value, body_font, "#475569", width, max_lines=2 if compact else 3)
            y += 18
        else:
            y = _draw_wrapped(draw, (x, y), paragraph, body_font, "#475569", width, max_lines=3 if compact else 4)
            y += 20
    return y


def _draw_skill_pills(draw, skills, x, y, width, palette, compact=False):
    font = _font(18 if not compact else 16, bold=True)
    cursor_x = x
    cursor_y = y
    for skill in skills:
        pill_w = _text_width(draw, skill, font) + 30
        if cursor_x + pill_w > x + width:
            cursor_x = x
            cursor_y += 42
        draw.rounded_rectangle((cursor_x, cursor_y, cursor_x + pill_w, cursor_y + 31), radius=15, fill=palette["soft"], outline=palette["accent"], width=1)
        draw.text((cursor_x + 15, cursor_y + 6), skill, fill=palette["dark"], font=font)
        cursor_x += pill_w + 12
    return cursor_y + 46


def _draw_bullet_list(draw, title, items, x, y, width, palette, compact=False, dark=False):
    title_font = _font(23 if not compact else 20, bold=True)
    body_font = _font(18 if not compact else 16)
    heading_fill = "#ffffff" if dark else palette["accent"]
    body_fill = "#dbeafe" if dark else "#475569"
    bullet_fill = "#ffffff" if dark else palette["accent"]
    draw.text((x, y), title.upper(), fill=heading_fill, font=title_font)
    if not dark:
        draw.line((x, y + 33, x + min(width, 250), y + 33), fill=palette["accent"], width=3)
    y += 54 if not compact else 46
    for item in items:
        draw.ellipse((x, y + 8, x + 10, y + 18), fill=bullet_fill)
        y = _draw_wrapped(draw, (x + 24, y), item, body_font, body_fill, width - 24, max_lines=2)
        y += 18 if not compact else 14
    return y


def _draw_soft_panel(draw, box, palette):
    draw.rounded_rectangle(box, radius=18, fill=palette["soft"], outline="#e5e7eb", width=1)


def _draw_bottom_band(draw, data, y, palette):
    draw.rounded_rectangle((405, y, 1124, y + 178), radius=18, fill=palette["soft"], outline="#e5e7eb", width=1)
    draw.text((438, y + 30), "VALEUR AJOUTEE", fill=palette["accent"], font=_font(23, bold=True))
    _draw_wrapped(
        draw,
        (438, y + 78),
        data["achievements"][0],
        _font(18),
        "#475569",
        638,
        max_lines=3,
    )


def _draw_footer_note(draw, data, x, y, width, palette):
    draw.rounded_rectangle((x, y, x + width, y + 92), radius=14, fill=palette["soft"], outline="#e5e7eb", width=1)
    draw.text((x + 24, y + 20), "REFERENCES / DISPONIBILITE", fill=palette["accent"], font=_font(19, bold=True))
    _draw_wrapped(draw, (x + 24, y + 52), data["references"][0], _font(16), "#475569", width - 48, max_lines=1)


def _circle_photo(path, size, border=0, border_color="#ffffff"):
    image = Image.open(path).convert("RGB")
    image = ImageOps.fit(image, (size, size), Image.Resampling.LANCZOS, centering=(0.5, 0.34))
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    output.paste(image, (0, 0), mask)
    if border:
        framed = Image.new("RGBA", (size + border * 2, size + border * 2), (0, 0, 0, 0))
        border_mask = Image.new("L", framed.size, 0)
        ImageDraw.Draw(border_mask).ellipse((0, 0, framed.width - 1, framed.height - 1), fill=255)
        border_layer = Image.new("RGBA", framed.size, border_color)
        framed.paste(border_layer, (0, 0), border_mask)
        framed.paste(output, (border, border), output)
        return framed
    return output


def _rounded_photo(path, size):
    image = Image.open(path).convert("RGB")
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS, centering=(0.5, 0.34))
    output = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=34, fill=255)
    output.paste(image, (0, 0), mask)
    return output


def _profile(index):
    identity = PHOTO_IDENTITIES[index % len(PHOTO_IDENTITIES)]
    role = ROLES[index % len(ROLES)]
    company = COMPANIES[index % len(COMPANIES)]
    return {
        "name": f"{identity['first']} {identity['last']}",
        "role": role,
        "contact": "Abidjan | +225 07 00 00 00 00 | profil@email.com",
        "profile": (
            "Professionnel rigoureux avec une approche orientee resultats, "
            "capable de structurer les priorites, collaborer avec les equipes "
            "et livrer des solutions fiables dans des environnements exigeants."
        ),
        "experiences": [
            (
                role,
                f"{company} | 2023 - Aujourd'hui",
                "Pilotage des activites cles, suivi des indicateurs et amelioration continue des processus.",
            ),
            (
                "Charge de mission",
                "Horizon Services | 2020 - 2023",
                "Coordination operationnelle, reporting mensuel et accompagnement des parties prenantes.",
            ),
            (
                "Assistant de projet",
                "Nova Partners | 2018 - 2020",
                "Preparation des supports de suivi, controle qualite des livrables et relation avec les clients internes.",
            ),
        ],
        "education": [
            ("Cycle Ingenieur", "Institut National Polytechnique | 2018 - 2021"),
            ("Certification professionnelle", "Formation continue | 2022"),
        ],
        "skills": ["Analyse", "Gestion", "Communication", "Reporting", "Leadership", "Organisation", "Excel", "Power BI"],
        "languages": ["Francais - Courant", "Anglais - Intermediaire"],
        "tools": ["Pack Office", "Notion", "Jira", "Power BI", "Canva"],
        "achievements": [
            "Reduction des delais de traitement grace a une meilleure priorisation des taches.",
            "Mise en place de tableaux de bord simples pour suivre les objectifs mensuels.",
            "Amelioration de la coordination entre les equipes metier et les intervenants externes.",
        ],
        "certifications": ["Gestion de projet agile", "Analyse de donnees", "Communication professionnelle"],
        "references": ["Reference disponible sur demande", "Portfolio et recommandations transmis apres entretien"],
        "interests": ["Innovation", "Lecture", "Veille metier", "Formation continue"],
    }


def _draw_experiences(draw, data, x, y, width, palette, compact=False):
    title_font = _font(25 if not compact else 22, bold=True)
    role_font = _font(21 if not compact else 18, bold=True)
    meta_font = _font(18 if not compact else 16)
    body_font = _font(18 if not compact else 16)
    draw.text((x, y), "EXPERIENCES PROFESSIONNELLES", fill=palette["accent"], font=title_font)
    draw.line((x, y + 35, x + min(width, 330), y + 35), fill=palette["accent"], width=3)
    y += 62
    for role, meta, detail in data["experiences"]:
        draw.ellipse((x, y + 7, x + 13, y + 20), fill=palette["accent"])
        draw.text((x + 28, y), role, fill="#111827", font=role_font)
        y += 29
        draw.text((x + 28, y), meta, fill=palette["muted"], font=meta_font)
        y += 30
        y = _draw_wrapped(draw, (x + 28, y), detail, body_font, "#475569", width - 28, max_lines=2)
        y += 28
    return y


def _draw_left_sidebar(canvas, draw, data, photo, palette, variant):
    sidebar = 345 if variant == 0 else 305
    draw.rectangle((0, 0, sidebar, A4_SIZE[1]), fill=palette["dark"])
    draw.rectangle((sidebar, 0, A4_SIZE[0], A4_SIZE[1]), fill="#ffffff")
    draw.rounded_rectangle((sidebar + 58, 86, A4_SIZE[0] - 78, 260), radius=14, fill=palette["soft"])
    canvas.paste(_circle_photo(photo, 178, border=8, border_color="#ffffff"), (84, 76), _circle_photo(photo, 178, border=8, border_color="#ffffff"))
    draw.text((sidebar + 88, 108), data["name"].upper(), fill=palette["dark"], font=_font(44, bold=True))
    draw.text((sidebar + 90, 168), data["role"], fill=palette["accent"], font=_font(25, bold=True))
    _draw_wrapped(draw, (sidebar + 90, 207), data["contact"], _font(17), palette["muted"], 600, max_lines=2)

    side_x = 58
    y = 315
    for title, lines in [
        ("Contact", [data["contact"]]),
        ("Competences", data["skills"][:5]),
        ("Langues", data["languages"]),
        ("Outils", data["tools"][:5]),
        ("Interets", data["interests"][:3]),
    ]:
        draw.text((side_x, y), title.upper(), fill="#ffffff", font=_font(23, bold=True))
        y += 43
        for line in lines:
            y = _draw_wrapped(draw, (side_x, y), line, _font(18), "#dbeafe", sidebar - 96, max_lines=2)
            y += 18
        y += 34

    main_x = sidebar + 70
    y = 330
    y = _draw_section(draw, "Profil", main_x, y, 710, palette, [data["profile"]])
    y = _draw_experiences(draw, data, main_x, y + 10, 720, palette)
    y = _draw_section(draw, "Formation", main_x, y + 10, 720, palette, data["education"], compact=True)
    _draw_bullet_list(draw, "Realisations", data["achievements"][:2], main_x, y + 18, 350, palette, compact=True)
    _draw_bullet_list(draw, "Certifications", data["certifications"], main_x + 390, y + 18, 315, palette, compact=True)
    _draw_bottom_band(draw, data, 1456, palette)


def _draw_header_band(canvas, draw, data, photo, palette, variant):
    band_h = 318 if variant == 1 else 270
    draw.rectangle((0, 0, A4_SIZE[0], band_h), fill=palette["accent"])
    draw.rectangle((0, band_h, A4_SIZE[0], A4_SIZE[1]), fill="#ffffff")
    photo_asset = _circle_photo(photo, 202, border=8, border_color="#ffffff")
    canvas.paste(photo_asset, (865, 64 if variant == 1 else 38), photo_asset)
    draw.text((86, 78), data["name"].upper(), fill="#ffffff", font=_font(50, bold=True))
    draw.text((88, 144), data["role"], fill="#e0f2fe", font=_font(28, bold=True))
    _draw_wrapped(draw, (88, 195), data["contact"], _font(18), "#f8fafc", 690, max_lines=2)

    left_x = 86
    right_x = 760
    y = band_h + 64
    y = _draw_section(draw, "Profil", left_x, y, 620, palette, [data["profile"]])
    y = _draw_experiences(draw, data, left_x, y + 16, 640, palette)
    y = _draw_section(draw, "Formation", left_x, y + 12, 640, palette, data["education"], compact=True)
    _draw_bullet_list(draw, "Realisations", data["achievements"][:2], left_x, y + 12, 640, palette, compact=True)

    draw.rounded_rectangle((right_x, band_h + 64, 1114, 1620), radius=18, fill=palette["soft"], outline="#e5e7eb")
    side_y = band_h + 104
    draw.text((right_x + 38, side_y), "COMPETENCES", fill=palette["accent"], font=_font(24, bold=True))
    side_y = _draw_skill_pills(draw, data["skills"], right_x + 38, side_y + 54, 280, palette, compact=True)
    side_y = _draw_section(draw, "Langues", right_x + 38, side_y + 12, 280, palette, data["languages"], compact=True)
    side_y = _draw_bullet_list(draw, "Outils", data["tools"][:4], right_x + 38, side_y + 52, 280, palette, compact=True)
    side_y = _draw_bullet_list(draw, "Certifications", data["certifications"][:2], right_x + 38, side_y + 16, 280, palette, compact=True)
    side_y = _draw_section(draw, "Interets", right_x + 38, side_y + 16, 280, palette, [", ".join(data["interests"])], compact=True)
    _draw_section(draw, "References", right_x + 38, max(side_y + 18, 1450), 280, palette, data["references"][:1], compact=True)
    _draw_footer_note(draw, data, left_x, 1570, 620, palette)


def _draw_minimal(canvas, draw, data, photo, palette, variant):
    draw.rectangle((0, 0, A4_SIZE[0], A4_SIZE[1]), fill="#ffffff")
    draw.rectangle((80, 80, 100, 1565), fill=palette["accent"])
    draw.rounded_rectangle((140, 78, 1110, 300), radius=22, outline="#e5e7eb", width=2)
    photo_asset = _rounded_photo(photo, (160, 196))
    canvas.paste(photo_asset, (175, 98), photo_asset)
    draw.text((375, 112), data["name"].upper(), fill=palette["dark"], font=_font(47, bold=True))
    draw.text((377, 176), data["role"], fill=palette["accent"], font=_font(26, bold=True))
    _draw_wrapped(draw, (378, 224), data["contact"], _font(17), palette["muted"], 620, max_lines=2)

    x = 150
    y = 360
    y = _draw_section(draw, "Profil", x, y, 900, palette, [data["profile"]])
    y = _draw_experiences(draw, data, x, y + 18, 910, palette)
    y = _draw_section(draw, "Formation", x, y + 8, 430, palette, data["education"], compact=True)
    _draw_skill_pills(draw, data["skills"], 610, y - 164, 450, palette, compact=True)
    _draw_section(draw, "Langues", 610, y + 56, 430, palette, data["languages"], compact=True)
    _draw_soft_panel(draw, (140, 1250, 1110, 1618), palette)
    _draw_bullet_list(draw, "Realisations cles", data["achievements"][:3], 172, 1288, 470, palette, compact=True)
    _draw_bullet_list(draw, "Certifications et outils", data["certifications"] + data["tools"][:2], 690, 1288, 360, palette, compact=True)
    _draw_footer_note(draw, data, 172, 1508, 878, palette)


def _draw_right_rail(canvas, draw, data, photo, palette, variant):
    rail_x = 820
    draw.rectangle((0, 0, A4_SIZE[0], A4_SIZE[1]), fill="#ffffff")
    draw.rectangle((rail_x, 0, A4_SIZE[0], A4_SIZE[1]), fill=palette["soft"])
    draw.rectangle((0, 0, A4_SIZE[0], 26), fill=palette["accent"])
    photo_asset = _circle_photo(photo, 190, border=7, border_color="#ffffff")
    canvas.paste(photo_asset, (914, 94), photo_asset)
    draw.text((82, 96), data["name"].upper(), fill=palette["dark"], font=_font(52, bold=True))
    draw.text((84, 164), data["role"], fill=palette["accent"], font=_font(28, bold=True))
    _draw_wrapped(draw, (84, 214), data["contact"], _font(18), palette["muted"], 630, max_lines=2)

    y = 330
    y = _draw_section(draw, "Profil", 84, y, 660, palette, [data["profile"]])
    y = _draw_experiences(draw, data, 84, y + 18, 680, palette)
    y = _draw_section(draw, "Formation", 84, y + 10, 680, palette, data["education"], compact=True)
    _draw_bullet_list(draw, "Realisations", data["achievements"][:3], 84, y + 18, 680, palette, compact=True)

    side_y = 345
    _draw_section(draw, "Competences", rail_x + 48, side_y, 280, palette, [], compact=True)
    side_y = _draw_skill_pills(draw, data["skills"], rail_x + 48, side_y + 60, 280, palette, compact=True)
    side_y = _draw_section(draw, "Langues", rail_x + 48, side_y + 24, 280, palette, data["languages"], compact=True)
    side_y = _draw_bullet_list(draw, "Outils", data["tools"], rail_x + 48, side_y + 52, 280, palette, compact=True)
    side_y = _draw_bullet_list(draw, "Certifications", data["certifications"][:2], rail_x + 48, side_y + 16, 280, palette, compact=True)
    _draw_section(draw, "References", rail_x + 48, side_y + 16, 280, palette, data["references"], compact=True)
    _draw_footer_note(draw, data, 84, 1540, 680, palette)


def _draw_executive(canvas, draw, data, photo, palette, variant):
    draw.rectangle((0, 0, A4_SIZE[0], A4_SIZE[1]), fill="#ffffff")
    draw.rectangle((70, 70, 1130, 1627), outline="#e5e7eb", width=3)
    draw.line((190, 325, 1010, 325), fill=palette["accent"], width=4)
    photo_asset = _circle_photo(photo, 170, border=6, border_color=palette["soft"])
    canvas.paste(photo_asset, (515, 88), photo_asset)
    name_font = _font(48, bold=True)
    role_font = _font(25, bold=True)
    name_w = _text_width(draw, data["name"].upper(), name_font)
    role_w = _text_width(draw, data["role"], role_font)
    draw.text(((A4_SIZE[0] - name_w) / 2, 275), data["name"].upper(), fill=palette["dark"], font=name_font)
    draw.text(((A4_SIZE[0] - role_w) / 2, 338), data["role"], fill=palette["accent"], font=role_font)
    contact_w = _text_width(draw, data["contact"], _font(17))
    draw.text(((A4_SIZE[0] - min(contact_w, 850)) / 2, 382), data["contact"], fill=palette["muted"], font=_font(17))

    y = 465
    y = _draw_section(draw, "Profil", 140, y, 920, palette, [data["profile"]])
    y = _draw_experiences(draw, data, 140, y + 14, 920, palette)
    draw.rounded_rectangle((140, y + 8, 530, y + 260), radius=16, fill=palette["soft"])
    _draw_section(draw, "Formation", 170, y + 38, 330, palette, data["education"], compact=True)
    draw.rounded_rectangle((585, y + 8, 1060, y + 260), radius=16, fill=palette["soft"])
    _draw_skill_pills(draw, data["skills"], 620, y + 56, 390, palette, compact=True)
    bottom_y = y + 296
    draw.rounded_rectangle((140, bottom_y, 1060, 1608), radius=16, fill="#ffffff", outline="#e5e7eb", width=2)
    _draw_bullet_list(draw, "Realisations", data["achievements"][:2], 178, bottom_y + 36, 520, palette, compact=True)
    _draw_bullet_list(draw, "Certifications et references", data["certifications"][:2] + data["references"][:1], 750, bottom_y + 36, 265, palette, compact=True)


LAYOUTS = [
    ("Colonne sombre", _draw_left_sidebar),
    ("Bandeau moderne", _draw_header_band),
    ("Minimal vertical", _draw_minimal),
    ("Rail lateral", _draw_right_rail),
    ("Executif centre", _draw_executive),
    ("Colonne compacte", _draw_left_sidebar),
    ("Bandeau clair", _draw_header_band),
    ("Minimal structure", _draw_minimal),
    ("Rail doux", _draw_right_rail),
    ("Executif sobre", _draw_executive),
]


def _render_preview(index, photo_path):
    palette = deepcopy(PALETTES[index % len(PALETTES)])
    layout_name, layout = LAYOUTS[index % len(LAYOUTS)]
    data = _profile(index)
    canvas = Image.new("RGB", A4_SIZE, "#ffffff")
    draw = ImageDraw.Draw(canvas)
    layout(canvas, draw, data, photo_path, palette, index % len(LAYOUTS))
    return canvas, data, layout_name


def _save_thumb(preview, path):
    thumb = ImageOps.contain(preview, THUMB_SIZE, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", THUMB_SIZE, "#ffffff")
    left = (THUMB_SIZE[0] - thumb.width) // 2
    top = (THUMB_SIZE[1] - thumb.height) // 2
    canvas.paste(thumb, (left, top))
    canvas.save(path, "PNG", optimize=True)


class Command(BaseCommand):
    help = "Genere une galerie locale de modeles CV en images avec les photos nettoyees."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100, help="Nombre d'aperçus a generer.")
        parser.add_argument(
            "--photos",
            default=str(settings.BASE_DIR.parent / "frontend" / "src" / "assets" / "cv-photos" / "normalized"),
            help="Dossier contenant les portraits normalises.",
        )
        parser.add_argument("--order-start", type=int, default=3000, help="Ordre d'affichage du premier modele.")

    def handle(self, *args, **options):
        count = int(options["count"])
        if count < 1:
            raise CommandError("--count doit etre superieur a 0.")

        photo_dir = Path(options["photos"]).resolve()
        if not photo_dir.exists():
            raise CommandError(f"Dossier photos introuvable: {photo_dir}")

        photos = sorted(photo_dir.glob("*.png"))
        if not photos:
            raise CommandError(f"Aucune photo PNG trouvee dans {photo_dir}")

        preview_dir = Path(settings.MEDIA_ROOT) / "templates" / "previews" / "generated"
        thumb_dir = Path(settings.MEDIA_ROOT) / "templates" / "thumbnails" / "generated"
        preview_dir.mkdir(parents=True, exist_ok=True)
        thumb_dir.mkdir(parents=True, exist_ok=True)

        generated = 0
        for index in range(count):
            number = index + 1
            slug = f"galerie-cv-{number:03d}"
            photo = photos[index % len(photos)]
            preview, data, layout_name = _render_preview(index, photo)
            preview_rel = Path("templates") / "previews" / "generated" / f"{slug}.png"
            thumb_rel = Path("templates") / "thumbnails" / "generated" / f"{slug}.png"
            preview_path = Path(settings.MEDIA_ROOT) / preview_rel
            thumb_path = Path(settings.MEDIA_ROOT) / thumb_rel

            preview.save(preview_path, "PNG", optimize=True)
            _save_thumb(preview, thumb_path)

            category = CATEGORIES[(index + (index % len(LAYOUTS))) % len(CATEGORIES)]
            style_label = STYLE_LABELS[category]
            template, _ = CVTemplate.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": f"CV {style_label} - {data['role']}",
                    "description": f"Modele {layout_name.lower()} avec photo professionnelle et structure ATS claire.",
                    "long_description": (
                        "Apercu genere localement a partir des portraits nettoyes. "
                        "Le modele reste utilisable via le moteur interne DOCX/PDF."
                    ),
                    "category": category,
                    "docx_filename": "",
                    "is_premium": False,
                    "is_active": True,
                    "order": int(options["order_start"]) + index,
                },
            )
            template.preview_full.name = preview_rel.as_posix()
            template.thumbnail.name = thumb_rel.as_posix()
            template.save(update_fields=["preview_full", "thumbnail", "updated_at"])
            generated += 1

        self.stdout.write(self.style.SUCCESS(f"{generated} apercu(s) de galerie generes."))
