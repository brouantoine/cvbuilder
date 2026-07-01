import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.request

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from cvs.models import PaymentTransaction
from cvs.services.access import grant_access, plan_for

PAYSTACK_BASE_URL = "https://api.paystack.co"


def _secret_key():
    if not settings.PAYSTACK_SECRET_KEY:
        raise RuntimeError("PAYSTACK_SECRET_KEY manquant dans backend/.env.")
    return settings.PAYSTACK_SECRET_KEY


def _paystack_request(method, path, payload=None):
    body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{PAYSTACK_BASE_URL}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {_secret_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Paystack a refusé la requête: {detail}") from exc


def _amount_for_paystack(amount_xof):
    return int(amount_xof) * int(settings.PAYSTACK_SUBUNIT_MULTIPLIER)


def _metadata_from(data):
    metadata = data.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return metadata if isinstance(metadata, dict) else {}


def _validate_payment_confirmation(payment, data):
    expected_amount = _amount_for_paystack(payment.amount_xof)
    received_amount = data.get("amount")
    received_currency = str(data.get("currency") or "").upper()
    expected_currency = str(payment.currency).upper()
    metadata = _metadata_from(data)

    if int(received_amount or 0) != expected_amount:
        raise ValueError("Montant Paystack invalide.")
    if received_currency != expected_currency:
        raise ValueError("Devise Paystack invalide.")
    if str(metadata.get("user_id")) != str(payment.user_id):
        raise ValueError("Utilisateur Paystack invalide.")
    if str(metadata.get("plan_type")) != payment.plan_type:
        raise ValueError("Plan Paystack invalide.")

    expected_cv = "" if payment.cv_id is None else str(payment.cv_id)
    received_cv = metadata.get("cv_id")
    received_cv = "" if received_cv is None else str(received_cv)
    if received_cv != expected_cv:
        raise ValueError("CV Paystack invalide.")


def _reference(user_id, plan_type):
    return f"cvb_{user_id}_{plan_type}_{secrets.token_hex(8)}"


def initialize_payment(user, plan_type, cv_id=None):
    # Modèle actuel : seul l'abonnement hebdomadaire est vendu (essai gratuit à l'inscription).
    plan_type = plan_type or PaymentTransaction.PLAN_WEEKLY
    plan = plan_for(plan_type)

    payment = PaymentTransaction.objects.create(
        user=user,
        cv=None,
        plan_type=plan_type,
        amount_xof=plan["amount_xof"],
        currency=settings.PAYSTACK_CURRENCY,
        reference=_reference(user.id, plan_type),
    )

    payload = {
        "email": user.email or f"{user.username}@cvbuilder.local",
        "amount": _amount_for_paystack(payment.amount_xof),
        "currency": payment.currency,
        "reference": payment.reference,
        "callback_url": settings.PAYSTACK_CALLBACK_URL,
        "metadata": {
            "user_id": user.id,
            "cv_id": None,
            "plan_type": payment.plan_type,
            "amount_xof": payment.amount_xof,
        },
    }
    response = _paystack_request("POST", "/transaction/initialize", payload)
    data = response.get("data") or {}
    payment.authorization_url = data.get("authorization_url", "")
    payment.access_code = data.get("access_code", "")
    payment.raw_response = response
    payment.save(update_fields=["authorization_url", "access_code", "raw_response", "updated_at"])
    return payment


@transaction.atomic
def mark_success(payment, raw_response=None):
    """Marque le paiement réussi et octroie le droit. IDEMPOTENT : un 2e appel
    (webhook + verify) ne crée pas de second droit (verrou + état)."""
    payment = PaymentTransaction.objects.select_for_update().get(pk=payment.pk)
    if payment.status == PaymentTransaction.STATUS_SUCCESS:
        grant_access(payment)  # update_or_create(payment=...) : idempotent
        return payment
    payment.status = PaymentTransaction.STATUS_SUCCESS
    payment.paid_at = payment.paid_at or timezone.now()
    if raw_response is not None:
        payment.raw_response = raw_response
    payment.save(update_fields=["status", "paid_at", "raw_response", "updated_at"])
    grant_access(payment)
    return payment


def verify_payment(reference, user=None):
    payment = PaymentTransaction.objects.filter(reference=reference).first()
    if payment is None:
        raise ValueError("Transaction introuvable.")
    if user is not None and payment.user_id != user.id:
        raise ValueError("Transaction introuvable.")

    response = _paystack_request("GET", f"/transaction/verify/{reference}")
    data = response.get("data") or {}
    status = data.get("status")
    payment.raw_response = response
    if status == "success":
        _validate_payment_confirmation(payment, data)
        return mark_success(payment, response)
    if status in {"failed", "abandoned", "reversed"}:
        payment.status = PaymentTransaction.STATUS_FAILED if status == "reversed" else status
        payment.save(update_fields=["status", "raw_response", "updated_at"])
    else:
        payment.save(update_fields=["raw_response", "updated_at"])
    return payment


def reconcile_pending_payments(user):
    """Re-vérifie auprès de Paystack les paiements en attente de l'utilisateur.
    Récupère les cas où le webhook n'est pas arrivé (téléphone éteint, connexion
    coupée, onglet fermé après paiement). Sûr à appeler souvent (ex. au login)."""
    pending = PaymentTransaction.objects.filter(
        user=user, status=PaymentTransaction.STATUS_PENDING
    ).order_by("-created_at")[:10]
    updated = 0
    for payment in pending:
        try:
            result = verify_payment(payment.reference, user=user)
            if result.status == PaymentTransaction.STATUS_SUCCESS:
                updated += 1
        except Exception:
            continue
    return updated


def verify_webhook_signature(raw_body, signature):
    if not signature:
        return False
    expected = hmac.new(_secret_key().encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_webhook(raw_body, signature):
    if not verify_webhook_signature(raw_body, signature):
        raise ValueError("Signature Paystack invalide.")
    payload = json.loads(raw_body.decode("utf-8"))
    event = payload.get("event")
    data = payload.get("data") or {}
    reference = data.get("reference")
    if event == "charge.success" and reference:
        payment = PaymentTransaction.objects.filter(reference=reference).first()
        if payment:
            _validate_payment_confirmation(payment, data)
            return mark_success(payment, payload)
    return None
