from django.contrib import admin
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone
from django.utils.html import format_html

# Identité de l'interface d'administration.
admin.site.site_header = "Administration MonCVPro"
admin.site.site_title = "MonCVPro"
admin.site.index_title = "Pilotage de l'application"
# Page d'accueil : tableau de bord temps réel (config/templates/admin/dashboard_index.html).
admin.site.index_template = "admin/dashboard_index.html"


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Vue d'ensemble des comptes : inscriptions, activité, CV créés, accès."""

    list_display = (
        "username",
        "email",
        "cv_count",
        "access_state",
        "date_joined",
        "last_login",
        "is_active",
        "is_staff",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    date_hierarchy = "date_joined"
    ordering = ("-date_joined",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(_cv_count=Count("cvs", distinct=True)).prefetch_related("cv_access_grants")

    @admin.display(description="CV créés", ordering="_cv_count")
    def cv_count(self, obj):
        return obj._cv_count

    @admin.display(description="Accès")
    def access_state(self, obj):
        grants = list(obj.cv_access_grants.all())
        if not grants:
            return "—"
        now = timezone.now()
        active = [grant for grant in grants if grant.expires_at is None or grant.expires_at > now]
        if active:
            grant = max(active, key=lambda item: item.expires_at or now)
            label = grant.get_plan_type_display() if hasattr(grant, "get_plan_type_display") else grant.plan_type
            return format_html('<span style="color:#0a7d40;font-weight:600;">{}</span>', label)
        return format_html('<span style="color:#b3261e;">Expiré</span>')


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    """Journal d'audit : qui a fait quoi dans l'admin (lecture seule)."""

    list_display = ("action_time", "user", "action_label", "content_type", "object_repr", "change_message")
    list_filter = ("action_flag", "content_type", "user")
    search_fields = ("object_repr", "change_message", "user__username")
    date_hierarchy = "action_time"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Action", ordering="action_flag")
    def action_label(self, obj):
        return {ADDITION: "Ajout", CHANGE: "Modification", DELETION: "Suppression"}.get(obj.action_flag, obj.action_flag)
