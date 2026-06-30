import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from PIL import Image, ImageOps

from templates.models import CVTemplate
from templates.services.template_library import align_template_manifest


def _read_manifest(path):
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict) and isinstance(payload.get("templates"), list):
        return [item for item in payload["templates"] if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _pretty_name(path):
    stem = path.stem.replace("_", " ").replace("-", " ").strip()
    prefixes = ["modele cv", "curriculum vitae"]
    cleaned = stem
    lowered = cleaned.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    return cleaned.title() or "Modèle CV"


def _category_for(path):
    name = path.stem.lower()
    if any(token in name for token in ["moderne", "ingenieur", "reconversion"]):
        return "modern"
    if any(token in name for token in ["femme", "anglais"]):
        return "creative"
    if any(token in name for token in ["neutre", "debutant", "etudiant", "sans-payer"]):
        return "minimal"
    return "classic"


def _description_for(path):
    name = path.stem.lower()
    if "ingenieur" in name:
        return "Modèle structuré pour profils techniques et ingénierie."
    if "etudiant" in name or "debutant" in name:
        return "Modèle clair pour profils étudiants ou premiers emplois."
    if "reconversion" in name:
        return "Modèle adapté aux transitions professionnelles."
    if "anglais" in name:
        return "Modèle CV en anglais pour candidatures internationales."
    return "Modèle professionnel prêt à personnaliser."


def _write_manifest(library_dir, copied_files):
    manifest_path = library_dir / "templates.json"
    existing = _read_manifest(manifest_path)
    by_filename = {str(item.get("filename")): item for item in existing if item.get("filename")}
    next_order = max([int(item.get("order", 0) or 0) for item in existing] + [0]) + 1

    for index, path in enumerate(copied_files):
        filename = path.name
        if filename in by_filename:
            continue
        slug = f"custom-{slugify(path.stem) or index}"
        by_filename[filename] = {
            "filename": filename,
            "name": _pretty_name(path),
            "slug": slug,
            "category": _category_for(path),
            "description": _description_for(path),
            "long_description": "Aperçu généré depuis la première page du fichier DOCX réel.",
            "is_premium": False,
            "is_active": True,
            "order": next_order + index,
        }

    ordered = sorted(by_filename.values(), key=lambda item: int(item.get("order", 0) or 0))
    manifest_path.write_text(json.dumps({"templates": ordered}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest_path


def _template_docx_path(template):
    value = (template.docx_filename or "").strip()
    prefix = "examples/"
    if not value.startswith(prefix):
        return None
    relative = Path(value[len(prefix):])
    if relative.is_absolute() or ".." in relative.parts:
        return None
    path = Path(settings.CV_TEMPLATE_LIBRARY_DIR) / relative
    return path if path.exists() else None


def _convert_first_page_to_png(docx_path, tmpdir):
    profile_dir = tmpdir / "lo-profile"
    config_dir = tmpdir / "config"
    cache_dir = tmpdir / "cache"
    runtime_dir = tmpdir / "runtime"
    pdf_dir = tmpdir / "pdf"
    profile_dir.mkdir()
    config_dir.mkdir()
    cache_dir.mkdir()
    runtime_dir.mkdir(mode=0o700)
    pdf_dir.mkdir()
    env = os.environ.copy()
    env.update({
        "HOME": str(tmpdir),
        "XDG_CONFIG_HOME": str(config_dir),
        "XDG_CACHE_HOME": str(cache_dir),
        "XDG_RUNTIME_DIR": str(runtime_dir),
    })

    command = [
        settings.LIBREOFFICE_BINARY,
        "--headless",
        f"-env:UserInstallation=file://{profile_dir}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(pdf_dir),
        str(docx_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=90, check=False, env=env)
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if completed.returncode != 0 or not pdfs:
        message = completed.stderr or completed.stdout or "conversion DOCX vers PDF impossible"
        raise RuntimeError(message.strip())

    output_base = tmpdir / "first-page"
    command = [
        "pdftoppm",
        "-png",
        "-f",
        "1",
        "-singlefile",
        "-r",
        "150",
        str(pdfs[0]),
        str(output_base),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    image_path = output_base.with_suffix(".png")
    if completed.returncode != 0 or not image_path.exists():
        message = completed.stderr or completed.stdout or "conversion PDF vers PNG impossible"
        raise RuntimeError(message.strip())
    return image_path


def _save_preview_images(template, source_png):
    previews_dir = Path(settings.MEDIA_ROOT) / "templates" / "previews"
    thumbnails_dir = Path(settings.MEDIA_ROOT) / "templates" / "thumbnails"
    previews_dir.mkdir(parents=True, exist_ok=True)
    thumbnails_dir.mkdir(parents=True, exist_ok=True)

    preview_rel = Path("templates") / "previews" / f"{template.slug}.png"
    thumbnail_rel = Path("templates") / "thumbnails" / f"{template.slug}.png"
    preview_path = Path(settings.MEDIA_ROOT) / preview_rel
    thumbnail_path = Path(settings.MEDIA_ROOT) / thumbnail_rel

    with Image.open(source_png) as image:
        image = image.convert("RGB")
        image.save(preview_path, "PNG", optimize=True)

        thumb = ImageOps.contain(image, (320, 448))
        canvas = Image.new("RGB", (320, 448), "#ffffff")
        left = (canvas.width - thumb.width) // 2
        top = (canvas.height - thumb.height) // 2
        canvas.paste(thumb, (left, top))
        canvas.save(thumbnail_path, "PNG", optimize=True)

    template.preview_full.name = preview_rel.as_posix()
    template.thumbnail.name = thumbnail_rel.as_posix()
    template.save(update_fields=["preview_full", "thumbnail", "updated_at"])


class Command(BaseCommand):
    help = "Importe les DOCX du dossier exemple et génère des aperçus depuis leur première page."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=str(settings.BASE_DIR.parent / "exemple"),
            help="Dossier contenant les fichiers DOCX à importer.",
        )
        parser.add_argument(
            "--no-previews",
            action="store_true",
            help="Importer les modèles sans générer les images d'aperçu.",
        )

    def handle(self, *args, **options):
        source_dir = Path(options["source"]).resolve()
        if not source_dir.exists():
            raise CommandError(f"Dossier source introuvable: {source_dir}")

        library_dir = Path(settings.CV_TEMPLATE_LIBRARY_DIR)
        library_dir.mkdir(parents=True, exist_ok=True)

        docx_files = sorted(source_dir.glob("*.docx"))
        if not docx_files:
            raise CommandError(f"Aucun fichier DOCX trouvé dans {source_dir}")

        copied = []
        for source in docx_files:
            target = library_dir / source.name
            shutil.copy2(source, target)
            copied.append(target)

        manifest_path = _write_manifest(library_dir, copied)
        result = align_template_manifest()
        self.stdout.write(f"{len(copied)} fichier(s) DOCX importé(s).")
        self.stdout.write(f"Manifest synchronisé: {manifest_path}")
        self.stdout.write(f"{result} modèle(s) aligné(s) en base.")

        if options["no_previews"]:
            return

        generated = 0
        failures = []
        templates = CVTemplate.objects.filter(is_active=True, docx_filename__startswith="examples/")
        for template in templates:
            docx_path = _template_docx_path(template)
            if not docx_path:
                continue
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    first_page = _convert_first_page_to_png(docx_path, Path(tmp))
                    _save_preview_images(template, first_page)
                generated += 1
                self.stdout.write(self.style.SUCCESS(f"Aperçu généré: {template.name}"))
            except Exception as exc:
                failures.append(f"{template.name}: {exc}")
                self.stdout.write(self.style.WARNING(f"Aperçu ignoré: {template.name} ({exc})"))

        self.stdout.write(self.style.SUCCESS(f"{generated} aperçu(s) généré(s) depuis la première page."))
        if failures:
            self.stdout.write(self.style.WARNING("Échecs:"))
            for failure in failures:
                self.stdout.write(f"- {failure}")
