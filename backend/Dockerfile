# Backend CVBuilder — Django + WeasyPrint + LibreOffice + Tesseract + OpenCV.
# À déployer sur un hébergeur conteneur (Render, Railway, Fly.io, VPS).
# NE PEUT PAS tourner sur Vercel (serverless) : ces dépendances natives sont requises.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_DEBUG=false

# Dépendances système :
# - WeasyPrint : libpango, libcairo, libgdk-pixbuf, libffi, libharfbuzz, fonts
# - LibreOffice : conversion DOCX (secours)
# - Tesseract : OCR des CV scannés (+ français)
# - Poppler : pdftoppm / pdfimages / pdftotext / pdfinfo
# - OpenCV : libgl1, libglib2.0-0 (détection de visage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev \
    libcairo2 libharfbuzz0b libfribidi0 \
    libreoffice-writer \
    tesseract-ocr tesseract-ocr-fra \
    poppler-utils \
    libgl1 libglib2.0-0 \
    fonts-dejavu fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Fichiers statiques (admin Django) servis par WhiteNoise.
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Migrations puis serveur. (gunicorn ; 2 workers, timeout long car génération PDF.)
CMD sh -c "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"
