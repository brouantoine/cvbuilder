"""
Modèle commercial :
- À l'inscription, l'utilisateur reçoit un ESSAI GRATUIT de 7 jours (CV illimités).
- Ensuite, abonnement HEBDOMADAIRE : 1000 F = 7 jours + 5 CV à débloquer.
- Un CV débloqué (essai ou crédit) reste téléchargeable à vie (is_unlocked).
"""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from cvs.models import AccessGrant, CV, PaymentTransaction


def payment_plans():
    return [
        {
            "code": PaymentTransaction.PLAN_WEEKLY,
            "label": "Abonnement 1 semaine",
            "amount_xof": settings.CV_WEEKLY_PRICE_XOF,
            "description": f"7 jours d'accès — {settings.CV_WEEKLY_CV_CREDITS} CV à télécharger.",
            "duration_hours": settings.CV_WEEKLY_ACCESS_HOURS,
            "cv_credits": settings.CV_WEEKLY_CV_CREDITS,
            "ai_credits": None,
        },
    ]


def plan_for(code):
    for plan in payment_plans():
        if plan["code"] == code:
            return plan
    if code == PaymentTransaction.PLAN_WEEKLY:
        return payment_plans()[0]
    raise ValueError("Plan inconnu.")


def _active_grants(user):
    now = timezone.now()
    return AccessGrant.objects.filter(user=user, starts_at__lte=now).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gte=now)
    )


def active_grant(user):
    """Renvoie le droit actif le plus pertinent (essai illimité d'abord, sinon
    hebdo avec crédits restants), ou None."""
    grants = list(_active_grants(user).order_by("-expires_at"))
    trial = next((g for g in grants if g.cv_credits is None), None)
    if trial:
        return trial
    return next((g for g in grants if (g.cv_credits or 0) > 0), None)


def grant_trial(user):
    """Octroie l'essai gratuit (idempotent : une seule fois par utilisateur)."""
    if AccessGrant.objects.filter(user=user, plan_type=PaymentTransaction.PLAN_TRIAL).exists():
        return None
    now = timezone.now()
    return AccessGrant.objects.create(
        user=user,
        plan_type=PaymentTransaction.PLAN_TRIAL,
        starts_at=now,
        expires_at=now + timedelta(days=settings.CV_TRIAL_DAYS),
        cv_credits=None,  # illimité pendant l'essai
    )


def has_active_access(user, cv=None):
    """Peut générer/télécharger ce CV ?"""
    if not settings.PAYMENTS_ENFORCED:
        return True
    if cv is not None and getattr(cv, "is_unlocked", False):
        return True  # CV déjà débloqué : retéléchargeable à vie
    return active_grant(user) is not None


def has_ai_access(user, cv=None):
    """L'IA (profil, correction…) est disponible tant qu'un droit est actif
    (essai ou hebdo, même crédits CV épuisés : on peut peaufiner avant de payer)."""
    if not settings.PAYMENTS_ENFORCED:
        return True
    if has_active_access(user, cv):
        return True
    return _active_grants(user).exists()


@transaction.atomic
def unlock_cv(user, cv):
    """Débloque un CV au moment de la génération : consomme 1 crédit hebdo si
    nécessaire (gratuit pendant l'essai). Idempotent."""
    if not settings.PAYMENTS_ENFORCED:
        return True
    cv = CV.objects.select_for_update().get(pk=cv.pk)
    if cv.is_unlocked:
        return True
    grants = list(
        _active_grants(user).select_for_update().order_by("-expires_at")
    )
    trial = next((g for g in grants if g.cv_credits is None), None)
    if trial is not None:
        cv.is_unlocked = True
        cv.save(update_fields=["is_unlocked", "updated_at"])
        return True
    weekly = next((g for g in grants if (g.cv_credits or 0) > 0), None)
    if weekly is not None:
        weekly.cv_credits -= 1
        weekly.save(update_fields=["cv_credits"])
        cv.is_unlocked = True
        cv.save(update_fields=["is_unlocked", "updated_at"])
        return True
    return False


def has_expired_cv_access(user, cv=None):
    # Conservé pour compatibilité (ancien plan 1 CV). Plus utilisé activement.
    return False


def access_payload(user, cv=None):
    now = timezone.now()
    grant = active_grant(user)
    trial = (
        AccessGrant.objects.filter(user=user, plan_type=PaymentTransaction.PLAN_TRIAL)
        .order_by("-expires_at")
        .first()
    )
    trial_active = bool(trial and trial.expires_at and trial.expires_at >= now)
    days_left = None
    if grant and grant.expires_at:
        days_left = max(0, (grant.expires_at - now).days + (1 if (grant.expires_at - now).seconds else 0))
    return {
        "payments_enforced": settings.PAYMENTS_ENFORCED,
        "has_active_access": has_active_access(user, cv),
        "has_ai_access": has_ai_access(user, cv),
        "is_trial": bool(grant and grant.plan_type == PaymentTransaction.PLAN_TRIAL),
        "trial_active": trial_active,
        "trial_ends_at": trial.expires_at.isoformat() if trial and trial.expires_at else None,
        "plan": grant.plan_type if grant else None,
        "expires_at": grant.expires_at.isoformat() if grant and grant.expires_at else None,
        "days_left": days_left,
        "cv_credits": grant.cv_credits if grant else 0,
        "cv_unlocked": bool(cv and getattr(cv, "is_unlocked", False)),
    }


def grant_access(payment):
    """Octroie le droit après un paiement réussi (idempotent par paiement)."""
    plan = plan_for(payment.plan_type)
    now = timezone.now()
    expires_at = now + timedelta(hours=plan["duration_hours"]) if plan.get("duration_hours") else None
    grant, _ = AccessGrant.objects.update_or_create(
        payment=payment,
        defaults={
            "user": payment.user,
            "cv": None,
            "plan_type": payment.plan_type,
            "starts_at": now,
            "expires_at": expires_at,
            "cv_credits": plan.get("cv_credits"),
            "ai_credits": plan.get("ai_credits"),
        },
    )
    return grant


def require_generation_access(user, cv: CV):
    if has_active_access(user, cv):
        return True, ""
    return False, f"Abonnement requis : {settings.CV_WEEKLY_PRICE_XOF} F pour 1 semaine ({settings.CV_WEEKLY_CV_CREDITS} CV)."


def require_ai_access(user, cv: CV):
    if has_ai_access(user, cv):
        return True, ""
    return False, f"Abonnement requis : {settings.CV_WEEKLY_PRICE_XOF} F pour 1 semaine ({settings.CV_WEEKLY_CV_CREDITS} CV)."
