# Déploiement CVBuilder

## ⚠️ Architecture (important)

Le **backend NE PEUT PAS aller sur Vercel** : il utilise WeasyPrint, LibreOffice,
Tesseract, Poppler et OpenCV — des dépendances natives que le serverless de Vercel
ne supporte pas.

| Partie | Où | Comment |
|--------|-----|---------|
| **Frontend** (React/Vite) | **Vercel** | `vercel.json` fourni |
| **Backend** (Django) | **Render** / Railway / Fly.io | `backend/Dockerfile` + `render.yaml` fournis |
| **Base de données** | Postgres (Render) | via `DATABASE_URL` |
| **Fichiers** (photos, PDF) | disque persistant | `DJANGO_MEDIA_ROOT=/app/media` |

## 1. Backend sur Render

1. Pousse le repo sur GitHub.
2. Render → **New +** → **Blueprint** → sélectionne le repo (il lit `render.yaml`).
3. Renseigne les variables `sync: false` :
   - `DJANGO_ALLOWED_HOSTS` = `cvbuilder-api.onrender.com`
   - `DJANGO_CORS_ORIGINS` = `https://ton-app.vercel.app`
   - `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://ton-app.vercel.app`
   - `PAYSTACK_CALLBACK_URL` = `https://ton-app.vercel.app/dashboard`
   - `GROQ_API_KEY`, `PAYSTACK_SECRET_KEY`, `PAYSTACK_PUBLIC_KEY`
4. Déploie. L'URL de l'API : `https://cvbuilder-api.onrender.com`.
5. Crée l'admin : Render → Shell → `python manage.py createsuperuser`.
6. Charge les modèles : `python manage.py seed_catalog`.

## 2. Frontend sur Vercel

1. Vercel → **Add New** → **Project** → sélectionne le repo.
2. **Root Directory** = `frontend`.
3. Variable d'environnement : `VITE_API_URL` = `https://cvbuilder-api.onrender.com`.
4. Déploie. Vercel build `npm run build` → `dist` (voir `vercel.json`).

## 3. Paystack (webhook)

Dashboard Paystack → **Settings → API Keys & Webhooks** → Webhook URL :
`https://cvbuilder-api.onrender.com/api/cvs/payments/paystack-webhook/`

## 4. Variables d'environnement backend

| Variable | Exemple | Rôle |
|----------|---------|------|
| `DJANGO_DEBUG` | `false` | jamais `true` en prod |
| `DJANGO_SECRET_KEY` | (généré) | clé Django |
| `DJANGO_ALLOWED_HOSTS` | `api.onrender.com` | hôtes autorisés |
| `DJANGO_CORS_ORIGINS` | `https://app.vercel.app` | origines front autorisées |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://app.vercel.app` | CSRF |
| `DATABASE_URL` | `postgres://…` | Postgres |
| `DJANGO_MEDIA_ROOT` | `/app/media` | disque persistant |
| `PAYMENTS_ENFORCED` | `true` | active le paywall |
| `AI_PROVIDER` / `GROQ_API_KEY` / `GROQ_MODEL` | `groq` / … | IA |
| `GROQ_TPM_LIMIT` | `7600` (gratuit) → plus haut si palier Dev | quota IA |
| `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` | `sk_live_…` / `pk_live_…` | paiement |
| `PAYSTACK_CURRENCY` | `XOF` | devise |
| `PAYSTACK_CALLBACK_URL` | `https://app.vercel.app/dashboard` | retour après paiement |

## 5. Modèle commercial

- **Essai gratuit 7 jours** offert à l'inscription (CV illimités).
- Ensuite **abonnement 1 semaine = 1000 F** → 5 CV à débloquer.
- Un CV débloqué (essai ou crédit) reste **téléchargeable à vie**.
- Réglable via `CV_TRIAL_DAYS`, `CV_WEEKLY_PRICE_XOF`, `CV_WEEKLY_CV_CREDITS`.

Voir `PAYMENTS.md` pour la robustesse Paystack (13 scénarios).
