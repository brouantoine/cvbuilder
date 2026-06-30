import json
from pathlib import Path

from django.conf import settings
from django.utils.text import slugify

from templates.models import CVTemplate

VALID_CATEGORIES = {"classic", "modern", "creative", "minimal", "colorful"}
MANIFEST_NAME = "templates.json"


def _library_dir():
    path = Path(settings.CV_TEMPLATE_LIBRARY_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_docx_path(value):
    if not value:
        return None
    relative = Path(str(value).strip())
    if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".docx":
        return None
    return relative


def _read_manifest(directory):
    path = directory / MANIFEST_NAME
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("templates"), list):
        return payload["templates"]
    return []


def _name_from_file(relative):
    return relative.stem.replace("_", " ").replace("-", " ").strip().title() or "Modele CV"


def _entry_from_file(relative, index):
    return {
        "filename": relative.as_posix(),
        "name": _name_from_file(relative),
        "category": "classic",
        "description": "Modele CV pret a utiliser.",
        "is_premium": False,
        "is_active": True,
        "order": 1000 + index,
    }


def _manifest_key(entry):
    relative = _safe_docx_path(entry.get("filename")) if isinstance(entry, dict) else None
    return relative.as_posix() if relative else None


def align_template_manifest():
    directory = _library_dir()
    manifest_path = directory / MANIFEST_NAME
    entries = [entry for entry in _read_manifest(directory) if isinstance(entry, dict)]
    by_filename = {}
    for entry in entries:
        key = _manifest_key(entry)
        if key and (directory / key).exists():
            by_filename[key] = entry

    added = []
    files = sorted(path.relative_to(directory) for path in directory.rglob("*.docx"))
    next_order = max([int(entry.get("order", 0) or 0) for entry in by_filename.values()] + [0]) + 1

    aligned = []
    for index, relative in enumerate(files):
        key = relative.as_posix()
        entry = by_filename.get(key)
        if entry is None:
            entry = _entry_from_file(relative, next_order + index)
            added.append(key)
        aligned.append(entry)

    payload = {"templates": aligned}
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sync_count = sync_template_library()
    return {
        "templates_count": len(aligned),
        "synced_count": sync_count,
        "added": added,
        "manifest": str(manifest_path),
    }


def _normalize_entry(entry, directory, index):
    relative = _safe_docx_path(entry.get("filename"))
    if relative is None or not (directory / relative).exists():
        return None

    category = entry.get("category") if entry.get("category") in VALID_CATEGORIES else "classic"
    name = str(entry.get("name") or _name_from_file(relative)).strip()
    slug_source = relative.with_suffix("").as_posix().replace("/", "-").replace("_", "-")
    slug_value = str(entry.get("slug") or f"custom-{slugify(slug_source) or index}").strip()
    return {
        "name": name,
        "slug": slug_value,
        "description": str(entry.get("description") or "Modele CV pret a utiliser.").strip(),
        "long_description": str(entry.get("long_description") or "").strip(),
        "category": category,
        "docx_filename": f"examples/{relative.as_posix()}",
        "is_premium": bool(entry.get("is_premium", False)),
        "is_active": bool(entry.get("is_active", True)),
        "order": int(entry.get("order", 1000 + index)),
    }


def sync_template_library():
    directory = _library_dir()
    manifest_entries = _read_manifest(directory)
    known_files = set()
    normalized = []

    for index, entry in enumerate(manifest_entries):
        item = _normalize_entry(entry, directory, index)
        if item:
            known_files.add(item["docx_filename"])
            normalized.append(item)

    auto_files = sorted(path.relative_to(directory) for path in directory.rglob("*.docx"))
    for index, relative in enumerate(auto_files, start=len(normalized)):
        docx_filename = f"examples/{relative.as_posix()}"
        if docx_filename in known_files:
            continue
        item = _normalize_entry(_entry_from_file(relative, index), directory, index)
        if item:
            known_files.add(item["docx_filename"])
            normalized.append(item)

    active_docx = set()
    for item in normalized:
        docx_filename = item.pop("docx_filename")
        active_docx.add(docx_filename)
        CVTemplate.objects.update_or_create(
            slug=item["slug"],
            defaults={**item, "docx_filename": docx_filename},
        )

    CVTemplate.objects.filter(docx_filename__startswith="examples/").exclude(
        docx_filename__in=active_docx
    ).update(is_active=False)

    return len(normalized)
