"""
Traitement de la photo de profil : transformer n'importe quelle photo envoyée
par l'utilisateur en une photo de CV « parfaite » (cadrage portrait centré sur
le visage, fond net, contraste équilibré, format standard).
"""
import io
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError

# Format cible : portrait 4:5, qualité impression.
TARGET_WIDTH = 720
TARGET_HEIGHT = 900
MIN_INPUT_SIDE = 200


class PhotoError(ValueError):
    """Photo invalide ou inexploitable."""


def _largest_face(image):
    """Retourne (x, y, w, h) du plus grand visage détecté, sinon None."""
    try:
        import cv2
        import numpy as np
    except Exception:
        return None
    try:
        gray = np.array(image.convert("L"))
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(str(cascade_path))
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(faces) == 0:
            return None
        return max(faces, key=lambda box: box[2] * box[3])
    except Exception:
        return None


def _crop_around_face(image, face):
    """Cadrage portrait (4:5) centré sur le visage, avec espace tête/épaules."""
    iw, ih = image.size
    fx, fy, fw, fh = (int(value) for value in face)
    cx = fx + fw / 2
    cy = fy + fh / 2

    crop_w = fw * 2.4
    crop_h = crop_w * (TARGET_HEIGHT / TARGET_WIDTH)

    # Réduire si le cadrage dépasse l'image.
    if crop_w > iw:
        crop_h *= iw / crop_w
        crop_w = iw
    if crop_h > ih:
        crop_w *= ih / crop_h
        crop_h = ih

    left = cx - crop_w / 2
    top = cy - crop_h * 0.42  # visage placé dans le tiers supérieur
    left = max(0, min(left, iw - crop_w))
    top = max(0, min(top, ih - crop_h))
    return image.crop((int(left), int(top), int(left + crop_w), int(top + crop_h)))


def _center_portrait_crop(image):
    """Repli sans visage : cadrage portrait centré, légèrement vers le haut."""
    iw, ih = image.size
    target_ratio = TARGET_WIDTH / TARGET_HEIGHT
    if iw / ih > target_ratio:
        crop_w = int(ih * target_ratio)
        left = (iw - crop_w) // 2
        return image.crop((left, 0, left + crop_w, ih))
    crop_h = int(iw / target_ratio)
    top = int((ih - crop_h) * 0.18)
    return image.crop((0, top, iw, top + crop_h))


def _enhance(image):
    """Normalise et embellit la photo pour un rendu CV professionnel."""
    image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Color(image).enhance(1.05)
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = ImageEnhance.Brightness(image).enhance(1.02)
    image = ImageEnhance.Sharpness(image).enhance(1.15)
    return image


def make_cv_portrait(source):
    """
    `source` : chemin, file-like ou bytes. Retourne une image PIL portrait propre.
    Lève PhotoError si l'entrée n'est pas une image exploitable.
    """
    try:
        if isinstance(source, (bytes, bytearray)):
            image = Image.open(io.BytesIO(source))
        else:
            image = Image.open(source)
    except (OSError, UnidentifiedImageError):
        raise PhotoError("Le fichier envoyé n'est pas une image valide.")

    image = ImageOps.exif_transpose(image).convert("RGB")
    if min(image.size) < MIN_INPUT_SIDE:
        raise PhotoError("La photo est trop petite : utilisez une image d'au moins 200 px.")

    face = _largest_face(image)
    cropped = _crop_around_face(image, face) if face is not None else _center_portrait_crop(image)
    cropped = cropped.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    return _enhance(cropped), bool(face is not None)


def save_cv_portrait(source, cv, request=None):
    """Traite et enregistre la photo de profil, renvoie son URL média."""
    image, _ = make_cv_portrait(source)
    photos_dir = Path(settings.MEDIA_ROOT) / "cvs" / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    photo_path = photos_dir / f"cv-{cv.id}-portrait.png"
    image.save(photo_path, "PNG", optimize=True)
    relative = photo_path.relative_to(settings.MEDIA_ROOT).as_posix()
    media_url = settings.MEDIA_URL if settings.MEDIA_URL.startswith("/") else f"/{settings.MEDIA_URL}"
    url = f"{media_url}{relative}"
    return request.build_absolute_uri(url) if request else url
