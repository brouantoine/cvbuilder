"""
Script pour générer des images de placeholder pour les templates de CV.
Usage: python generate_template_images.py

Crée des miniatures et des aperçus pour chaque template.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

# Configuration
BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / 'media' / 'templates'
THUMBNAILS_DIR = MEDIA_DIR / 'thumbnails'
PREVIEWS_DIR = MEDIA_DIR / 'previews'

# Créer les répertoires
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# Données des templates
TEMPLATES = [
    {
        'slug': 'classique-elegant',
        'name': 'Classique\nÉlégant',
        'bg_color': '#f8f9fa',
        'text_color': '#1a1a1a',
        'accent_color': '#0066ff',
    },
    {
        'slug': 'moderne-dynamique',
        'name': 'Moderne\nDynamique',
        'bg_color': '#1a1a1a',
        'text_color': '#ffffff',
        'accent_color': '#00ff88',
    },
    {
        'slug': 'minimaliste-epure',
        'name': 'Minimaliste\nÉpuré',
        'bg_color': '#ffffff',
        'text_color': '#333333',
        'accent_color': '#999999',
    },
    {
        'slug': 'creatif-moderne',
        'name': 'Créatif\nModerne',
        'bg_color': '#ff6b6b',
        'text_color': '#ffffff',
        'accent_color': '#ffd93d',
    },
    {
        'slug': 'colore-vibrant',
        'name': 'Coloré\nVibrant',
        'bg_color': '#667eea',
        'text_color': '#ffffff',
        'accent_color': '#764ba2',
    },
]


def hex_to_rgb(hex_color):
    """Convertir couleur hex en RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def create_thumbnail(template_data):
    """Créer une miniature 200x280px."""
    img = Image.new(
        'RGB',
        (200, 280),
        hex_to_rgb(template_data['bg_color'])
    )
    draw = ImageDraw.Draw(img)
    
    # Dessiner des lignes représentant du texte
    accent = hex_to_rgb(template_data['accent_color'])
    text_color = hex_to_rgb(template_data['text_color'])
    
    # Barre de titre
    draw.rectangle([20, 20, 180, 35], fill=accent)
    
    # Lignes de contenu
    y = 50
    for _ in range(8):
        draw.line([20, y, 180, y], fill=text_color, width=2)
        y += 20
    
    # Ajouter le nom du template en petit
    draw.text(
        (100, 240),
        template_data['slug'].replace('-', ' ').title(),
        fill=text_color,
        anchor='mm'
    )
    
    return img


def create_preview(template_data):
    """Créer un aperçu 1200x1697px (A4)."""
    img = Image.new(
        'RGB',
        (1200, 1697),
        hex_to_rgb(template_data['bg_color'])
    )
    draw = ImageDraw.Draw(img)
    
    accent = hex_to_rgb(template_data['accent_color'])
    text_color = hex_to_rgb(template_data['text_color'])
    
    # Barre de titre
    draw.rectangle([80, 80, 1120, 150], fill=accent)
    
    # Ligne de titre
    draw.text(
        (600, 115),
        'Mon CV Professionnel',
        fill=hex_to_rgb(template_data['bg_color']) if template_data['bg_color'] == '#1a1a1a' else text_color,
        anchor='mm'
    )
    
    # Contenu principal
    y = 200
    for section in range(5):
        # Sous-titre
        draw.rectangle([80, y, 400, y+30], fill=accent, width=3)
        y += 60
        
        # Lignes de contenu
        for _ in range(4):
            draw.line([80, y, 1120, y], fill=text_color, width=4)
            y += 40
        
        y += 40
    
    return img


def main():
    """Générer toutes les images."""
    print("🎨 Génération des images de templates...\n")
    
    for template in TEMPLATES:
        print(f"  Création: {template['slug']}")
        
        # Miniature
        thumb = create_thumbnail(template)
        thumb_path = THUMBNAILS_DIR / f"{template['slug']}.png"
        thumb.save(thumb_path, 'PNG')
        print(f"    ✓ Miniature: {thumb_path.name}")
        
        # Aperçu
        preview = create_preview(template)
        preview_path = PREVIEWS_DIR / f"{template['slug']}.png"
        preview.save(preview_path, 'PNG')
        print(f"    ✓ Aperçu: {preview_path.name}\n")
    
    print("✅ Toutes les images ont été générées!")
    print(f"   Miniatures: {THUMBNAILS_DIR}")
    print(f"   Aperçus: {PREVIEWS_DIR}")


if __name__ == '__main__':
    try:
        main()
    except ImportError:
        print("❌ Erreur: Le module PIL n'est pas installé.")
        print("   Installez-le avec: pip install pillow")
    except Exception as e:
        print(f"❌ Erreur: {e}")
