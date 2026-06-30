# 🎨 Système de Modèles de CV - Guide d'Intégration Complète

## 📋 Vue d'ensemble

Un système professionnel et complet de gestion des modèles de CV avec:
- ✅ Aperçus visuels (miniature + haute résolution)
- ✅ Modal d'aperçu interactif
- ✅ Catégorisation des templates
- ✅ Support premium/gratuit
- ✅ Gestion complète par Django Admin
- ✅ Interface réactive et responsive

---

## 🔧 Installation & Configuration

### 1. Appliquer les migrations Django

```bash
cd backend
python manage.py migrate templates
```

Cela créera les nouveaux champs dans le modèle `CVTemplate`:
- `category`: Catégorie du template
- `thumbnail`: Image miniature (200x280px)
- `preview_full`: Aperçu haute résolution (1200x1697px)
- `long_description`: Description détaillée
- `is_active`: Statut d'activation
- `order`: Ordre d'affichage

### 2. Charger les données initiales

```bash
python manage.py load_template_data
```

Cela crée 5 templates de démonstration dans la base de données.

### 3. Vérifier l'installation backend

```bash
python manage.py runserver
# Accéder à http://localhost:8000/admin
# Connexion avec vos credentials
# Naviguer vers "Templates CV" pour voir les modèles
```

---

## 🎯 Structure des Templates

### Modèle CVTemplate enrichi

```python
class CVTemplate(models.Model):
    # Infos de base
    name              # "Classique Élégant"
    slug              # "classique-elegant" (unique, pour URL)
    description       # "Un design intemporel et professionnel"
    long_description  # Description détaillée
    category          # "classic", "modern", "creative", "minimal", "colorful"
    
    # Images d'aperçu
    thumbnail         # Miniature pour grille (200x280px)
    preview_full      # Aperçu haute résolution (1200x1697px A4)
    
    # Métadonnées
    docx_filename     # "modele_classique.docx" (fichier source)
    is_premium        # True/False
    is_active         # True/False (contrôle la visibilité)
    order             # Ordre d'affichage (0=premier)
```

### Catégories disponibles

- **Classique**: Pour candidatures traditionnelles (banque, administration)
- **Moderne**: Designs contemporains avec couleurs (tech, startups)
- **Minimaliste**: Épuré et impactant (luxe, consulting)
- **Créatif**: Asymétrique et unique (design, art, création)
- **Coloré**: Vibrant et énergique (marketing, startup)

---

## 📱 Côté Frontend

### Fichiers créés/modifiés

```
src/
├── components/
│   ├── TemplateCard.jsx          [MODIFIÉ] + Overlay preview
│   ├── TemplateGrid.jsx          [MODIFIÉ] + Gestion modal
│   └── TemplatePreviewModal.jsx  [NOUVEAU] ← Composant modal
├── pages/
│   └── Templates.jsx             [MODIFIÉ] + État modal
├── stores/
│   └── cvStore.js                (aucun changement nécessaire)
└── styles/
    ├── TemplateCard.css          [NOUVEAU]
    ├── TemplateGrid.css          [NOUVEAU]
    ├── TemplatePreviewModal.css  [NOUVEAU]
    └── Templates.css             [NOUVEAU]
```

### Fonctionnement du flux

1. **Page Templates.jsx** affiche:
   - Titre et sous-titre
   - Grille de TemplateCard
   - TemplatePreviewModal (invisible par défaut)

2. **TemplateCard** pour chaque template:
   - Miniature (thumbnail_url)
   - Overlay au survol avec bouton "👁️ Aperçu"
   - Badges (premium, inactif)
   - Description courte
   - Bouton "Choisir" → Builder

3. **TemplatePreviewModal** au clic sur "Aperçu":
   - Aperçu haute résolution (preview_full)
   - Infos détaillées (description, catégorie, type)
   - Modal responsive avec fullscreen
   - Bouton pour sélectionner le template

---

## 🖼️ Gestion des Images

### Où stocker les images

```
backend/media/
├── templates/
│   ├── thumbnails/     # Miniatures (200x280px)
│   │   ├── classique-elegant.png
│   │   ├── moderne-dynamique.png
│   │   └── ...
│   └── previews/       # Aperçus haute résolution (1200x1697px)
│       ├── classique-elegant.png
│       ├── moderne-dynamique.png
│       └── ...
└── cvs/
    └── generated/      # CVs générés (existant)
```

### Dimensions recommandées

| Type | Dimension | Format | Qualité |
|------|-----------|--------|---------|
| Thumbnail | 200 x 280 px | PNG/JPG | 72 DPI |
| Preview | 1200 x 1697 px | PNG/JPG | 150 DPI |
| A4 Preview | Ratio 1:1.414 | PNG | 72 DPI |

### Générer les images

Depuis Django Admin (/admin):
1. Aller à "Templates CV"
2. Cliquer sur un template
3. Upload `thumbnail` et `preview_full`
4. Sauvegarder

Les URLs seront servies automatiquement depuis `/media/templates/`.

---

## 🚀 Déploiement Complet

### Checklist de mise en ligne

- [ ] **Backend**: Migrations appliquées
- [ ] **Backend**: Fixtures chargées (ou data créée via admin)
- [ ] **Backend**: Images uploadées dans `/media/templates/`
- [ ] **Backend**: MEDIA_URL et MEDIA_ROOT configurés
- [ ] **Frontend**: Composants créés et styles intégrés
- [ ] **Frontend**: API client compatible avec nouveaux champs
- [ ] **Frontend**: Tester chaque template en aperçu
- [ ] **Frontend**: Tester responsive (mobile, tablet, desktop)

### Servir les fichiers media en production

```python
# config/settings.py
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# config/urls.py
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... vos URLs
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

En production (nginx/Apache):
```nginx
location /media/ {
    alias /path/to/backend/media/;
}
```

---

## 💾 API Endpoints

### Lister tous les templates actifs

```bash
GET /api/templates/
Authorization: Optional (gratuit pour tous)
```

Response:
```json
[
  {
    "id": 1,
    "name": "Classique Élégant",
    "slug": "classique-elegant",
    "description": "Un design intemporel et professionnel",
    "category": "classic",
    "category_display": "Classique",
    "thumbnail_url": "http://localhost:8000/media/templates/thumbnails/classique-elegant.png",
    "preview_url": "http://localhost:8000/media/templates/previews/classique-elegant.png",
    "is_premium": false,
    "is_active": true,
    "order": 1
  }
]
```

### Détail d'un template

```bash
GET /api/templates/{id}/
```

Response: Tous les champs du template (incluant `long_description`)

---

## 🧪 Tests

### Tester localement

```bash
# Terminal 1: Backend Django
cd backend
python manage.py runserver

# Terminal 2: Frontend Vite
cd frontend
npm run dev
```

Naviguer vers: http://localhost:5173/templates

### Checklist test

- [ ] Affichage des templates dans la grille
- [ ] Miniatures chargent correctement
- [ ] Hover overlay affiche bouton "Aperçu"
- [ ] Clic aperçu ouvre la modal
- [ ] Modal affiche l'aperçu haute résolution
- [ ] Modal affiche descriptions et info détails
- [ ] Bouton plein écran fonctionne
- [ ] Responsive sur mobile
- [ ] Clic "Choisir" ouvre le builder
- [ ] Templates premium affichent badge

---

## 🔒 Gestion des Permissions

### Actuellement:
- **Lister templates**: AllowAny (anonyme OK)
- **Détail template**: AllowAny (anonyme OK)
- **Admin templates**: Administrateurs uniquement

### Pour ajouter des restrictions:

```python
# Si vous voulez restreindre aux users authentifiés
from rest_framework.permissions import IsAuthenticated

class TemplateListView(ListAPIView):
    permission_classes = [IsAuthenticated]
```

---

## 🎓 Exemple d'utilisation (Frontend)

```jsx
import { useState } from 'react';
import { Templates } from './pages/Templates';

function App() {
  return <Templates />;
}

// Templates.jsx gère:
// - Chargement des templates via cvStore
// - Affichage en grille avec TemplateCard
// - Modal d'aperçu
// - Navigation vers builder
```

---

## 📊 Statistiques & Analytics

Pour tracker les templates populaires:

```python
# Ajouter un champ au modèle CV
class CV(models.Model):
    template = models.ForeignKey(CVTemplate, ...)
    # Les templates sont trackés via les CVs créés
    
# Query pour voir les templates les plus utilisés:
from django.db.models import Count
popular = CVTemplate.objects.annotate(
    usage_count=Count('cvs')
).order_by('-usage_count')
```

---

## 🐛 Troubleshooting

### Images ne s'affichent pas?
- Vérifier que `MEDIA_ROOT` et `MEDIA_URL` sont configurés
- Vérifier que les fichiers sont dans le bon dossier
- Vérifier les permissions du dossier `media/`

### Modal ne s'ouvre pas?
- Vérifier les erreurs console du navigateur
- S'assurer que `preview_url` est défini dans le template
- Vérifier que `onPreview` est passé à `TemplateCard`

### Templates ne chargent pas?
- Tester l'API: `curl http://localhost:8000/api/templates/`
- Vérifier CORS dans `settings.py`
- Vérifier les migrations appliquées: `python manage.py showmigrations templates`

---

## 📝 Prochaines améliorations possibles

- [ ] Systèmes d'filtrage par catégorie
- [ ] Recherche de templates
- [ ] Favoris / wishlist
- [ ] Évaluation des templates (rating)
- [ ] Prévisualisation 3D ou animation
- [ ] Génération d'images de preview automatique
- [ ] Support des thèmes personnalisés
- [ ] API de customisation des templates

---

## 📞 Support

Pour des questions ou problèmes d'intégration, consultez la documentation Django REST Framework:
https://www.django-rest-framework.org/

Pour des questions sur React/Vite:
https://vitejs.dev/
https://react.dev/
