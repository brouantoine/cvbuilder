from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import AccessGrant, CV, FieldSuggestion, PaymentTransaction, TemplateSubmission, UserActivity


def _user_admin_link(obj):
    """Lien vers la fiche admin de l'utilisateur (suit l'URL réelle de l'admin)."""
    url = reverse("admin:auth_user_change", args=[obj.user_id])
    return format_html('<a href="{}">{}</a>', url, obj.user)


@admin.register(CV)
class CVAdmin(admin.ModelAdmin):
    """Suivi complet des CV : contenu, IA, fichiers générés, déblocage."""

    list_display = (
        "title",
        "user_link",
        "template",
        "status",
        "ai_status",
        "is_unlocked",
        "pdf_link",
        "public_link",
        "public_view_count",
        "created_at",
        "generated_at",
    )
    list_filter = ("status", "ai_status", "is_unlocked", "is_public", "template", "template_mode", "created_at")
    search_fields = ("title", "user__username", "user__email", "job_offer_url", "public_slug")
    readonly_fields = ("created_at", "updated_at", "generated_at", "public_slug", "public_view_count")
    date_hierarchy = "created_at"
    list_select_related = ("user", "template")
    raw_id_fields = ("user",)
    fieldsets = (
        ("Général", {"fields": ("user", "template", "title", "status", "is_unlocked", "template_mode")}),
        ("Contenu du CV", {"fields": ("data",)}),
        ("Partage public", {"fields": ("is_public", "public_slug", "public_view_count"), "classes": ("collapse",)}),
        ("Offre d'emploi ciblée", {"fields": ("job_offer_url", "job_offer_text", "job_offer_file"), "classes": ("collapse",)}),
        ("IA", {"fields": ("ai_status", "ai_error", "ai_data", "ai_messages"), "classes": ("collapse",)}),
        ("Fichiers", {"fields": ("source_file", "photo_file", "generated_file", "generated_pdf", "generated_at"), "classes": ("collapse",)}),
        ("Horodatage", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Utilisateur", ordering="user__username")
    def user_link(self, obj):
        return _user_admin_link(obj)

    @admin.display(description="PDF")
    def pdf_link(self, obj):
        if obj.generated_pdf:
            return format_html('<a href="{}" target="_blank">ouvrir</a>', obj.generated_pdf.url)
        return "—"

    @admin.display(description="Lien public")
    def public_link(self, obj):
        from django.conf import settings

        if obj.is_public and obj.public_slug:
            base = settings.FRONTEND_URL or ""
            return format_html('<a href="{0}/cv/{1}" target="_blank">/cv/{1}</a>', base, obj.public_slug)
        return "—"


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """Suivi des paiements Paystack. Les identifiants et la réponse brute sont
    en lecture seule pour ne pas casser la réconciliation automatique."""

    list_display = (
        "reference",
        "user_link",
        "plan_type",
        "amount_display",
        "status_badge",
        "paid_at",
        "created_at",
    )
    list_filter = ("plan_type", "status", "currency", "created_at")
    search_fields = ("reference", "user__username", "user__email")
    readonly_fields = ("reference", "authorization_url", "access_code", "raw_response", "created_at", "updated_at", "paid_at")
    date_hierarchy = "created_at"
    list_select_related = ("user", "cv")
    raw_id_fields = ("user", "cv")

    @admin.display(description="Utilisateur", ordering="user__username")
    def user_link(self, obj):
        return _user_admin_link(obj)

    @admin.display(description="Montant", ordering="amount_xof")
    def amount_display(self, obj):
        return f"{obj.amount_xof} {obj.currency}"

    @admin.display(description="Statut", ordering="status")
    def status_badge(self, obj):
        colors = {"success": "#0a7d40", "pending": "#b26a00", "failed": "#b3261e", "cancelled": "#6c757d"}
        color = colors.get(obj.status, "#374151")
        label = obj.get_status_display() if hasattr(obj, "get_status_display") else obj.status
        return format_html('<span style="color:{};font-weight:600;">{}</span>', color, label)


@admin.register(AccessGrant)
class AccessGrantAdmin(admin.ModelAdmin):
    """Droits d'accès (essai, abonnement) : validité et crédits restants."""

    list_display = (
        "user_link",
        "plan_type",
        "active_badge",
        "starts_at",
        "expires_at",
        "cv_credits",
        "ai_credits",
        "created_at",
    )
    list_filter = ("plan_type", "created_at")
    search_fields = ("user__username", "user__email", "cv__title")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    list_select_related = ("user", "cv")
    raw_id_fields = ("user", "cv", "payment")

    @admin.display(description="Utilisateur", ordering="user__username")
    def user_link(self, obj):
        return _user_admin_link(obj)

    @admin.display(description="État")
    def active_badge(self, obj):
        if obj.expires_at is None or obj.expires_at > timezone.now():
            return format_html('<span style="color:#0a7d40;font-weight:600;">Actif</span>')
        return format_html('<span style="color:#b3261e;">Expiré</span>')


@admin.register(FieldSuggestion)
class FieldSuggestionAdmin(admin.ModelAdmin):
    """Champs rencontrés dans des CV importés qui n'existaient pas encore
    dans le modèle — triés par fréquence pour prioriser quoi ajouter."""

    list_display = ("label", "occurrences", "sample_preview", "user_link", "status_badge", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("label", "sample_value", "user__username", "user__email")
    readonly_fields = ("occurrences", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_select_related = ("user", "cv")
    raw_id_fields = ("user", "cv")
    actions = ["mark_added", "mark_dismissed"]

    @admin.display(description="Utilisateur", ordering="user__username")
    def user_link(self, obj):
        return _user_admin_link(obj)

    @admin.display(description="Exemple")
    def sample_preview(self, obj):
        text = obj.sample_value or ""
        return text[:80] + ("…" if len(text) > 80 else "")

    @admin.display(description="Statut", ordering="status")
    def status_badge(self, obj):
        colors = {"pending": "#b26a00", "added": "#0a7d40", "dismissed": "#6c757d"}
        color = colors.get(obj.status, "#374151")
        return format_html('<span style="color:{};font-weight:600;">{}</span>', color, obj.get_status_display())

    @admin.action(description="Marquer comme ajouté au modèle")
    def mark_added(self, request, queryset):
        queryset.update(status=FieldSuggestion.STATUS_ADDED)

    @admin.action(description="Ignorer")
    def mark_dismissed(self, request, queryset):
        queryset.update(status=FieldSuggestion.STATUS_DISMISSED)


@admin.register(TemplateSubmission)
class TemplateSubmissionAdmin(admin.ModelAdmin):
    """CV importés au design jugé réussi par l'IA — vivier de futurs modèles."""

    list_display = ("preview_thumb", "user_link", "aesthetic_score", "status_badge", "pdf_link", "created_at")
    list_filter = ("status", "aesthetic_score", "created_at")
    search_fields = ("user__username", "user__email", "aesthetic_notes")
    readonly_fields = ("preview_thumb", "aesthetic_score", "aesthetic_notes", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("user", "cv")
    raw_id_fields = ("user", "cv")
    actions = ["mark_approved", "mark_rejected"]

    @admin.display(description="Utilisateur", ordering="user__username")
    def user_link(self, obj):
        return _user_admin_link(obj)

    @admin.display(description="Aperçu")
    def preview_thumb(self, obj):
        if obj.preview_image:
            return format_html('<img src="{}" style="height:90px;border-radius:6px;" />', obj.preview_image.url)
        return "—"

    @admin.display(description="PDF")
    def pdf_link(self, obj):
        if obj.source_pdf:
            return format_html('<a href="{}" target="_blank">ouvrir</a>', obj.source_pdf.url)
        return "—"

    @admin.display(description="Statut", ordering="status")
    def status_badge(self, obj):
        colors = {"pending": "#b26a00", "approved": "#0a7d40", "rejected": "#b3261e"}
        color = colors.get(obj.status, "#374151")
        return format_html('<span style="color:{};font-weight:600;">{}</span>', color, obj.get_status_display())

    @admin.action(description="Retenir pour le catalogue")
    def mark_approved(self, request, queryset):
        queryset.update(status=TemplateSubmission.STATUS_APPROVED)

    @admin.action(description="Rejeter")
    def mark_rejected(self, request, queryset):
        queryset.update(status=TemplateSubmission.STATUS_REJECTED)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Dernière activité par utilisateur (lecture seule) — base du « en ligne »."""

    list_display = ("user_link", "last_seen", "online_badge")
    search_fields = ("user__username", "user__email")
    date_hierarchy = "last_seen"
    list_select_related = ("user",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Utilisateur", ordering="user__username")
    def user_link(self, obj):
        return _user_admin_link(obj)

    @admin.display(description="État")
    def online_badge(self, obj):
        from datetime import timedelta

        if obj.last_seen >= timezone.now() - timedelta(minutes=5):
            return format_html('<span style="color:#0a7d40;font-weight:600;">● En ligne</span>')
        return format_html('<span style="color:#6c757d;">Hors ligne</span>')
