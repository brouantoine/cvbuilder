"""Statistiques en direct du tableau de bord admin (/moncvservices/stats.json).

Vue réservée au staff, consommée par le template admin/dashboard_index.html
qui se rafraîchit automatiquement.
"""
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone

from cvs.models import CV, AccessGrant, PaymentTransaction, UserActivity

ONLINE_WINDOW_MINUTES = 5
SERIES_DAYS = 14


def _daily_series(queryset, date_field, start_day, today):
    """Comptes par jour sur [start_day, today] — les jours vides valent 0."""
    raw = dict(
        queryset.filter(**{f"{date_field}__date__gte": start_day})
        .annotate(day=TruncDate(date_field))
        .values_list("day")
        .annotate(n=Count("id"))
        .values_list("day", "n")
    )
    days = [start_day + timedelta(days=i) for i in range((today - start_day).days + 1)]
    return [{"day": day.strftime("%d/%m"), "value": raw.get(day, 0)} for day in days]


@staff_member_required
def admin_stats(request):
    now = timezone.now()
    today = timezone.localdate()
    start_day = today - timedelta(days=SERIES_DAYS - 1)
    week_ago = now - timedelta(days=7)
    online_cutoff = now - timedelta(minutes=ONLINE_WINDOW_MINUTES)

    users = User.objects.all()
    online_qs = UserActivity.objects.filter(last_seen__gte=online_cutoff).select_related("user")

    success = PaymentTransaction.objects.filter(status=PaymentTransaction.STATUS_SUCCESS)
    active_grants = AccessGrant.objects.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now), starts_at__lte=now)

    payload = {
        "generated_at": timezone.localtime(now).strftime("%H:%M:%S"),
        "users": {
            "total": users.count(),
            "today": users.filter(date_joined__date=today).count(),
            "week": users.filter(date_joined__gte=week_ago).count(),
            "online": online_qs.count(),
            "online_names": list(online_qs.values_list("user__username", flat=True)[:15]),
        },
        "cvs": {
            "total": CV.objects.count(),
            "today": CV.objects.filter(created_at__date=today).count(),
            "generated": CV.objects.filter(generated_at__isnull=False).count(),
            "unlocked": CV.objects.filter(is_unlocked=True).count(),
        },
        "payments": {
            "revenue_total": success.aggregate(t=Sum("amount_xof"))["t"] or 0,
            "revenue_today": success.filter(paid_at__date=today).aggregate(t=Sum("amount_xof"))["t"] or 0,
            "success_count": success.count(),
            "pending_count": PaymentTransaction.objects.filter(status=PaymentTransaction.STATUS_PENDING).count(),
        },
        "access": {
            "trials": active_grants.filter(plan_type=PaymentTransaction.PLAN_TRIAL).count(),
            "weekly": active_grants.filter(plan_type=PaymentTransaction.PLAN_WEEKLY).count(),
        },
        "series": {
            "signups": _daily_series(users, "date_joined", start_day, today),
            "cvs": _daily_series(CV.objects.all(), "created_at", start_day, today),
        },
        "recent": {
            "users": [
                {"name": u.username, "when": timezone.localtime(u.date_joined).strftime("%d/%m %H:%M")}
                for u in users.order_by("-date_joined")[:5]
            ],
            "payments": [
                {
                    "ref": p.reference,
                    "user": p.user.username,
                    "amount": f"{p.amount_xof} {p.currency}",
                    "status": p.get_status_display(),
                    "ok": p.status == PaymentTransaction.STATUS_SUCCESS,
                }
                for p in PaymentTransaction.objects.select_related("user").order_by("-created_at")[:5]
            ],
            "cvs": [
                {
                    "title": c.title,
                    "user": c.user.username,
                    "status": c.get_status_display(),
                    "when": timezone.localtime(c.created_at).strftime("%d/%m %H:%M"),
                }
                for c in CV.objects.select_related("user").order_by("-created_at")[:5]
            ],
        },
    }
    return JsonResponse(payload)
