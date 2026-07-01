from django.conf import settings
from django.db import models
from django.utils import timezone
from templates.models import CVTemplate


class CV(models.Model):
    """
    CV lié à un utilisateur, un modèle et un contexte de candidature.
    """
    STATUS_DRAFT = "draft"
    STATUS_AI_READY = "ai_ready"
    STATUS_GENERATED = "generated"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Brouillon"),
        (STATUS_AI_READY, "Optimisé par IA"),
        (STATUS_GENERATED, "Généré"),
        (STATUS_FAILED, "Erreur"),
    ]

    AI_STATUS_IDLE = "idle"
    AI_STATUS_PROCESSING = "processing"
    AI_STATUS_READY = "ready"
    AI_STATUS_FAILED = "failed"
    AI_STATUS_CHOICES = [
        (AI_STATUS_IDLE, "En attente"),
        (AI_STATUS_PROCESSING, "Traitement IA"),
        (AI_STATUS_READY, "IA prête"),
        (AI_STATUS_FAILED, "Erreur IA"),
    ]

    TEMPLATE_MODE_SELECTED = "selected"
    TEMPLATE_MODE_MATCH_UPLOAD = "match_upload"
    TEMPLATE_MODE_CHOICES = [
        (TEMPLATE_MODE_SELECTED, "Utiliser le modèle choisi"),
        (TEMPLATE_MODE_MATCH_UPLOAD, "Se rapprocher de l'ancien CV"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cvs")
    template = models.ForeignKey(CVTemplate, on_delete=models.PROTECT, related_name="cvs")
    title = models.CharField(max_length=255, default="Mon CV")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    data = models.JSONField(default=dict, blank=True)

    source_file = models.FileField(upload_to="cvs/source/", blank=True, null=True)
    photo_file = models.FileField(upload_to="cvs/photos/source/", blank=True, null=True)
    job_offer_file = models.FileField(upload_to="cvs/offers/", blank=True, null=True)
    job_offer_url = models.URLField(blank=True)
    job_offer_text = models.TextField(blank=True)
    template_mode = models.CharField(
        max_length=30,
        choices=TEMPLATE_MODE_CHOICES,
        default=TEMPLATE_MODE_SELECTED,
    )

    ai_status = models.CharField(max_length=20, choices=AI_STATUS_CHOICES, default=AI_STATUS_IDLE)
    ai_error = models.TextField(blank=True)
    ai_data = models.JSONField(default=dict, blank=True)
    ai_messages = models.JSONField(default=list, blank=True)

    generated_file = models.FileField(upload_to="cvs/generated/", blank=True, null=True)
    generated_pdf = models.FileField(upload_to="cvs/generated/", blank=True, null=True)
    generated_at = models.DateTimeField(blank=True, null=True)
    # Un CV « déverrouillé » a consommé un crédit (ou a été créé pendant l'essai) ;
    # il peut être régénéré/retéléchargé librement ensuite.
    is_unlocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "CV"
        verbose_name_plural = "CVs"

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class PaymentTransaction(models.Model):
    """Transaction Paystack initiée depuis l'application."""

    PLAN_SINGLE_CV = "single_cv"
    PLAN_WEEKLY = "weekly"
    PLAN_EXTRA_AI = "extra_ai"
    PLAN_TRIAL = "trial"
    PLAN_CHOICES = [
        (PLAN_TRIAL, "Essai gratuit"),
        (PLAN_WEEKLY, "Abonnement semaine"),
        (PLAN_SINGLE_CV, "CV individuel"),
        (PLAN_EXTRA_AI, "Prolongation IA"),
    ]

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_ABANDONED = "abandoned"
    STATUS_CHOICES = [
        (STATUS_PENDING, "En attente"),
        (STATUS_SUCCESS, "Réussi"),
        (STATUS_FAILED, "Échoué"),
        (STATUS_ABANDONED, "Abandonné"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_payments")
    cv = models.ForeignKey(CV, on_delete=models.SET_NULL, blank=True, null=True, related_name="payments")
    plan_type = models.CharField(max_length=30, choices=PLAN_CHOICES)
    amount_xof = models.PositiveIntegerField()
    currency = models.CharField(max_length=10, default="XOF")
    reference = models.CharField(max_length=120, unique=True)
    authorization_url = models.URLField(blank=True)
    access_code = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    raw_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Transaction Paystack"
        verbose_name_plural = "Transactions Paystack"

    def __str__(self):
        return f"{self.reference} - {self.plan_type} - {self.status}"


class AccessGrant(models.Model):
    """Droit d'usage obtenu après paiement."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_access_grants")
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, blank=True, null=True, related_name="access_grants")
    payment = models.OneToOneField(
        PaymentTransaction,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="access_grant",
    )
    plan_type = models.CharField(max_length=30, choices=PaymentTransaction.PLAN_CHOICES)
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True)
    ai_credits = models.PositiveIntegerField(blank=True, null=True)
    # Nombre de CV restant à débloquer sur ce droit (None = illimité, ex. essai).
    cv_credits = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Droit d'accès CV"
        verbose_name_plural = "Droits d'accès CV"

    def __str__(self):
        target = self.cv_id or "global"
        return f"{self.user_id}:{self.plan_type}:{target}"

    @property
    def is_active(self):
        now = timezone.now()
        if self.starts_at and self.starts_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        if self.ai_credits is not None and self.ai_credits <= 0:
            return False
        return True
