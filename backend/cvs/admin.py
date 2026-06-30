from django.contrib import admin

from .models import AccessGrant, CV, PaymentTransaction


@admin.register(CV)
class CVAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "template", "status", "ai_status", "generated_at", "updated_at")
    list_filter = ("status", "ai_status", "template", "template_mode", "created_at")
    search_fields = ("title", "user__username", "user__email", "job_offer_url")
    readonly_fields = ("created_at", "updated_at", "generated_at")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "cv", "plan_type", "amount_xof", "status", "paid_at", "created_at")
    list_filter = ("plan_type", "status", "currency", "created_at")
    search_fields = ("reference", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at", "paid_at")


@admin.register(AccessGrant)
class AccessGrantAdmin(admin.ModelAdmin):
    list_display = ("user", "cv", "plan_type", "starts_at", "expires_at", "ai_credits", "created_at")
    list_filter = ("plan_type", "created_at")
    search_fields = ("user__username", "user__email", "cv__title")
    readonly_fields = ("created_at",)
