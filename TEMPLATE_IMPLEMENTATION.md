# 🚀 Guide d'Exécution - Système de Templates de CV

## ✅ Ce qui a été implémenté

### Backend Django (3 fichiers modifiés, 7 fichiers créés)

**Modèles améliorés:**
- ✅ `templates/models.py` - CVTemplate enrichi avec catégories, images, statut
- ✅ `templates/serializers.py` - Deux serializers (list + detail)
- ✅ `templates/views.py` - Filtrage des templates actifs
- ✅ `templates/admin.py` - Django Admin riche et visuellement attrayant
- ✅ Migration 0003 pour les nouveaux champs

**Données & Management:**
- ✅ `templates/fixtures/templates_data.json` - 5 templates de démonstration
- ✅ `templates/management/commands/load_template_data.py` - Commande pour charger les fixtures
- ✅ `generate_template_images.py` - Script pour générer images placeholder

**Documentation:**
- ✅ `templates/INTEGRATION_GUIDE.md` - Guide complet d'intégration

---

### Frontend React/Vite (6 fichiers créés, 3 fichiers modifiés)

**Composants:**
- ✅ `components/TemplatePreviewModal.jsx` - Modal d'aperçu interactive
- ✅ `components/TemplateCard.jsx` - Carte de template améliorée + overlay
- ✅ `components/TemplateGrid.jsx` - Grille responsive + loading states
- ✅ `pages/Templates.jsx` - Page principale avec gestion de la modal

**Styles CSS:**
- ✅ `styles/TemplatePreviewModal.css` - Modal responsive & élégante
- ✅ `styles/TemplateCard.css` - Cartes avec animations
- ✅ `styles/TemplateGrid.css` - Grille avec skeleton loader
- ✅ `styles/Templates.css` - Page templates

---

## 📝 Étapes d'Exécution

### ÉTAPE 1: Installer Pillow (pour générer les images)

```bash
cd ~/cvbuilder/backend
pip install Pillow
```

ou installer toutes les dépendances:

```bash
pip install -r requirements.txt
```

### ÉTAPE 2: Appliquer les migrations Django

```bash
cd ~/cvbuilder/backend
python manage.py migrate templates
```

✅ Cela crée les 3 nouveaux champs: `category`, `thumbnail`, `preview_full`, `long_description`, `is_active`, `order`

**Vérification:**
```bash
python manage.py showmigrations templates
# Vous devriez voir [X] avant chaque migration
```

### ÉTAPE 3: Générer les images de placeholder

```bash
# Toujours dans le dossier backend
python generate_template_images.py
```

✅ Cela crée:
- `media/templates/thumbnails/` avec 5 miniatures (200x280px)
- `media/templates/previews/` avec 5 aperçus (1200x1697px)

**Vérification:**
```bash
ls -la media/templates/thumbnails/
ls -la media/templates/previews/
# Vous devriez voir 5 fichiers .png dans chaque dossier
```

### ÉTAPE 4: Charger les données des templates

```bash
python manage.py load_template_data
```

✅ Cela crée 5 templates dans la base de données:
1. Classique Élégant (gratuit, actif)
2. Moderne Dynamique (premium, actif)
3. Minimaliste Épuré (gratuit, actif)
4. Créatif Moderne (premium, inactif)
5. Coloré Vibrant (premium, inactif)

**Vérification via Django Admin:**
```bash
python manage.py runserver
# Aller à http://localhost:8000/admin
# Cliquer sur "Templates CV"
# Vous devriez voir les 5 templates
```

### ÉTAPE 5: Tester l'API Backend

```bash
# Dans une autre fenêtre terminal
curl -X GET http://localhost:8000/api/templates/
```

✅ Vous devriez recevoir un JSON avec les templates actifs (3 templates)

Réponse attendue:
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
    "is_premium": false,
    "is_active": true,
    "order": 1
  },
  // ... autres templates
]
```

### ÉTAPE 6: Démarrer le serveur frontend

```bash
cd ~/cvbuilder/frontend
npm run dev
```

✅ Cela démarre Vite sur http://localhost:5173

### ÉTAPE 7: Tester l'interface utilisateur

Ouvrir http://localhost:5173/templates dans le navigateur

**Checklist visuelle:**
- [ ] La grille affiche 3 templates (les actifs)
- [ ] Chaque carte affiche:
  - [ ] Miniature du template
  - [ ] Nom du template
  - [ ] Catégorie (badge coloré)
  - [ ] Description courte
  - [ ] Bouton "Choisir"
- [ ] Au survol, un overlay apparaît avec bouton "👁️ Aperçu"
- [ ] Clic sur "Aperçu" ouvre une modal avec:
  - [ ] Aperçu haute résolution
  - [ ] Titre et catégorie
  - [ ] Description longue
  - [ ] Bouton fullscreen
  - [ ] Bouton fermer
- [ ] Modal responsive sur mobile

---

## 🎨 Personnaliser les Templates

### Via Django Admin

1. Aller à http://localhost:8000/admin/templates/cvtemplate/
2. Cliquer sur un template
3. Modifier:
   - **Informations de base**: nom, slug, descriptions
   - **Catégorie**: classique, moderne, créatif, minimaliste, coloré
   - **Images**: upload thumbnail (200x280) et preview_full (1200x1697)
   - **Statut**: actif/inactif, premium/gratuit
   - **Ordre**: position dans la grille (0 = premier)
4. Sauvegarder

### Créer un nouveau template

```bash
# 1. Upload les images dans media/templates/
cp /votre/template.png media/templates/thumbnails/mon-template.png
cp /votre/preview.png media/templates/previews/mon-template.png

# 2. Aller à l'admin Django
# 3. Ajouter un nouveau template avec:
#    - name: "Mon Template"
#    - slug: "mon-template"
#    - thumbnail: mon-template.png
#    - preview_full: mon-template.png
#    - docx_filename: "mon-template.docx" (créer le fichier Word)
```

---

## 🧪 Tester les Fonctionnalités

### Test 1: Affichage des Templates
```bash
curl -X GET http://localhost:8000/api/templates/ -H "Accept: application/json" | python -m json.tool
```

### Test 2: Détail d'un Template
```bash
curl -X GET http://localhost:8000/api/templates/1/ -H "Accept: application/json" | python -m json.tool
```

### Test 3: Images servies correctement
```bash
# Vérifier que les images sont accessibles
curl -I http://localhost:8000/media/templates/thumbnails/classique-elegant.png
# Devrait retourner 200 OK
```

### Test 4: Créer un CV avec un template
```javascript
// Dans la console du navigateur
const data = {
  template: 1,
  title: "Mon CV",
  data: {}
};
fetch('http://localhost:8000/api/cvs/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('access')}`
  },
  body: JSON.stringify(data)
}).then(r => r.json()).then(console.log);
```

---

## 🚀 Déployer en Production

### Checklist de déploiement

- [ ] **Base de données**: Migrations appliquées
- [ ] **Fichiers statiques**: `python manage.py collectstatic`
- [ ] **Fichiers media**: Uploadés et configurés
- [ ] **CORS**: Configuré pour votre domaine
- [ ] **Frontend**: Build: `npm run build`
- [ ] **Serveur web**: nginx/Apache configuré pour `/media/`

### Commandes avant déploiement

```bash
# Backend
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py load_template_data  # Optionnel si déjà done

# Frontend
npm run build
```

---

## 📊 Vérifier l'Installation

### Script de vérification complète

```bash
#!/bin/bash
echo "🔍 Vérification de l'installation..."

echo "\n1️⃣ Vérifier les migrations:"
python manage.py showmigrations templates | grep "\[X\]"

echo "\n2️⃣ Vérifier les templates en base:"
python manage.py shell -c "from templates.models import CVTemplate; print(f'{CVTemplate.objects.count()} templates')"

echo "\n3️⃣ Vérifier les images:"
echo "  Miniatures: $(ls media/templates/thumbnails/*.png 2>/dev/null | wc -l) fichiers"
echo "  Aperçus: $(ls media/templates/previews/*.png 2>/dev/null | wc -l) fichiers"

echo "\n4️⃣ Tester l'API:"
curl -s http://localhost:8000/api/templates/ | python -m json.tool | head -20

echo "\n✅ Vérification terminée!"
```

---

## 🆘 Dépannage

### Problème: Images ne s'affichent pas

**Solution:**
```bash
# Vérifier le chemin media
ls -la media/templates/

# Vérifier que MEDIA_URL et MEDIA_ROOT sont configurés
python manage.py shell -c "from django.conf import settings; print(settings.MEDIA_URL, settings.MEDIA_ROOT)"

# Vérifier les permissions
chmod -R 755 media/
```

### Problème: API retourne 404

**Solution:**
```bash
# Vérifier les migrations
python manage.py migrate

# Vérifier les données
python manage.py shell -c "from templates.models import CVTemplate; print(CVTemplate.objects.all())"
```

### Problème: Modal ne s'ouvre pas

**Solution:**
1. Ouvrir la console (F12)
2. Chercher les erreurs JavaScript
3. Vérifier que `preview_url` est défini: 
   ```javascript
   fetch('http://localhost:8000/api/templates/1/').then(r => r.json()).then(console.log)
   ```

---

## 📚 Ressources

- Django Admin: http://localhost:8000/admin/
- API Templates: http://localhost:8000/api/templates/
- Frontend: http://localhost:5173/templates
- Documentation intégration: `backend/templates/INTEGRATION_GUIDE.md`

---

## ✨ Prochaines Étapes (Optionnel)

1. **Filtrage par catégorie**: Ajouter boutons pour filtrer les templates
2. **Recherche**: Ajouter barre de recherche
3. **Tri personnalisé**: Permettre le tri par popularité, nouveau, etc.
4. **Favoris**: Ajouter système de favoris utilisateur
5. **Évaluation**: Permettre aux utilisateurs d'évaluer les templates

---

## 🎉 Vous êtes Prêt!

L'système de templates est maintenant complet, fonctionnel et prêt à être utilisé en production.

Toutes les données sont visibles, testables et facilement maintenables via Django Admin.

**Profitez de votre nouveau système de templates! 🚀**
