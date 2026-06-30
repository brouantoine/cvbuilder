from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from cvs.models import AccessGrant, CV, PaymentTransaction


def payment_plans():
    return [
        {
            "code": PaymentTransaction.PLAN_SINGLE_CV,
            "label": "1 CV complet",
            "amount_xof": settings.CV_SINGLE_PRICE_XOF,
            "description": "PDF + modifications et IA pendant 2 h sur ce CV.",
            "duration_hours": settings.CV_SINGLE_ACCESS_HOURS,
            "ai_credits": None,
        },
        {
            "code": PaymentTransaction.PLAN_WEEKLY,
            "label": "Semaine illimitée",
            "amount_xof": settings.CV_WEEKLY_PRICE_XOF,
            "description": "Accès à tous vos CV et générations pendant 7 jours.",
            "duration_hours": settings.CV_WEEKLY_ACCESS_HOURS,
            "ai_credits": None,
        },
        {
            "code": PaymentTransaction.PLAN_EXTRA_AI,
            "label": "Prolonger l'IA",
            "amount_xof": settings.CV_EXTRA_AI_PRICE_XOF,
            "description": "Disponible après les 2 h: ajoute 1 échange IA.",
            "duration_hours": None,
            "ai_credits": settings.CV_EXTRA_AI_CREDITS,
        },
    ]


def plan_for(code):
    for plan in payment_plans():
        if plan["code"] == code:
            return plan
    raise ValueError("Plan inconnu.")


def _active_grants(user):
    now = timezone.now()
    return AccessGrant.objects.filter(user=user, starts_at__lte=now).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gte=now)
    )


def has_active_access(user, cv=None):
    if not settings.PAYMENTS_ENFORCED:
        return True
    grants = _active_grants(user).filter(ai_credits__isnull=True)
    if grants.filter(plan_type=PaymentTransaction.PLAN_WEEKLY).exists():
        return True
    if cv is not None and grants.filter(plan_type=PaymentTransaction.PLAN_SINGLE_CV, cv=cv).exists():
        return True
    return False


def has_ai_access(user, cv=None):
    if has_active_access(user, cv):
        return True
    return _active_grants(user).filter(plan_type=PaymentTransaction.PLAN_EXTRA_AI, ai_credits__gt=0).exists()


def has_expired_cv_access(user, cv=None):
    if cv is None:
        return False
    now = timezone.now()
    return AccessGrant.objects.filter(
        user=user,
        cv=cv,
        plan_type=PaymentTransaction.PLAN_SINGLE_CV,
        expires_at__lt=now,
    ).exists()


@transaction.atomic
def consume_ai_credit(user, cv=None):
    if has_active_access(user, cv):
        return True
    grant = (
        _active_grants(user)
        .select_for_update()
        .filter(plan_type=PaymentTransaction.PLAN_EXTRA_AI, ai_credits__gt=0)
        .first()
    )
    if not grant:
        return False
    grant.ai_credits -= 1
    grant.save(update_fields=["ai_credits"])
    return True


def access_payload(user, cv=None):
    active_grants = _active_grants(user).filter(
        Q(ai_credits__isnull=True) | Q(ai_credits__gt=0)
    )
    expired_cv_access = has_expired_cv_access(user, cv)
    active_access = has_active_access(user, cv)
    return {
        "payments_enforced": settings.PAYMENTS_ENFORCED,
        "has_active_access": active_access,
        "has_ai_access": has_ai_access(user, cv),
        "has_expired_cv_access": expired_cv_access,
        "can_buy_extension": settings.PAYMENTS_ENFORCED and expired_cv_access and not active_access,
        "active_grants": [
            {
                "id": grant.id,
                "plan_type": grant.plan_type,
                "cv": grant.cv_id,
                "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
                "ai_credits": grant.ai_credits,
            }
            for grant in active_grants
        ],
    }


def grant_access(payment):
    plan = plan_for(payment.plan_type)
    now = timezone.now()
    expires_at = None
    cv = payment.cv

    if payment.plan_type == PaymentTransaction.PLAN_SINGLE_CV:
        if cv is None:
            raise ValueError("Le paiement 1 CV doit être lié à un CV.")
        expires_at = now + timedelta(hours=plan["duration_hours"])
    elif payment.plan_type == PaymentTransaction.PLAN_WEEKLY:
        cv = None
        expires_at = now + timedelta(hours=plan["duration_hours"])

    grant, _ = AccessGrant.objects.update_or_create(
        payment=payment,
        defaults={
            "user": payment.user,
            "cv": cv,
            "plan_type": payment.plan_type,
            "starts_at": now,
            "expires_at": expires_at,
            "ai_credits": plan.get("ai_credits"),
        },
    )
    return grant


def require_generation_access(user, cv: CV):
    if not has_active_access(user, cv):
        return False, "Paiement requis: 200 F pour 2 h ou 500 F pour la semaine."
    return True, ""


def require_ai_access(user, cv: CV):
    if settings.PAYMENTS_ENFORCED and not consume_ai_credit(user, cv):
        return False, "Vos 2 h sont terminées. Payez 50 F pour prolonger l'IA." if has_expired_cv_access(user, cv) else "Paiement requis: 200 F pour 2 h ou 500 F pour la semaine."
    return True, ""
