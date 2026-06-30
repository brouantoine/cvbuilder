from django.contrib import admin
from django.utils.html import format_html
from .models import CVTemplate


@admin.register(CVTemplate)
class CVTemplateAdmin(admin.ModelAdmin):
    """Admin riche pour gérer les templates de CV"""
    
    list_display = (
        "name",
        "category_display",
        "status_badge",
        "preview_thumbnail",
        "is_premium_badge",
        "order",
    )
    list_filter = ("category", "is_premium", "is_active", "created_at")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("order",)
    ordering = ("order", "name")
    
    fieldsets = (
        ("Informations de base", {
            "fields": ("name", "slug", "description", "long_description", "category")
        }),
        ("Aperçus visuels", {
            "fields": ("thumbnail", "preview_full", "preview_image_url"),
            "description": "Thumbnail (200x280px) pour la grille, Preview (1200x1697px A4) pour le modal"
        }),
        ("Template DOCX", {
            "fields": ("docx_filename",),
            "description": "Chemin du fichier DOCX dans cvs/docx_templates/"
        }),
        ("Statut", {
            "fields": ("is_active", "is_premium", "order")
        }),
        ("Métadonnées", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("created_at", "updated_at")
    
    def category_display(self, obj):
        """Affiche la catégorie"""
        return obj.get_category_display()
    category_display.short_description = "Catégorie"
    
    def status_badge(self, obj):
        """Affiche le statut (actif/inactif)"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">Actif</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">Inactif</span>'
        )
    status_badge.short_description = "Statut"
    
    def is_premium_badge(self, obj):
        """Affiche le badge premium"""
        if obj.is_premium:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">🔒 Premium</span>'
            )
        return format_html(
            '<span style="background-color: #17a2b8; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">Gratuit</span>'
        )
    is_premium_badge.short_description = "Type"
    
    def preview_thumbnail(self, obj):
        """Affiche la miniature"""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="50" height="70" style="border: 1px solid #ddd; '
                'border-radius: 3px;" alt="{}"/>',
                obj.thumbnail.url,
                obj.name
            )
        return "—"
    preview_thumbnail.short_description = "Aperçu"
