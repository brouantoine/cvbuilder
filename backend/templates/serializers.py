from rest_framework import serializers
from .models import CVTemplate


class CVTemplateSerializer(serializers.ModelSerializer):
    """Sérializer complet pour les templates"""
    thumbnail_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    
    class Meta:
        model = CVTemplate
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "long_description",
            "category",
            "category_display",
            "thumbnail_url",
            "preview_url",
            "preview_full",
            "thumbnail",
            "preview_image_url",
            "docx_filename",
            "is_premium",
            "is_active",
            "order",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
    
    def get_thumbnail_url(self, obj):
        """Retourne l'URL de la miniature pour la grille"""
        request = self.context.get("request")
        url = obj.thumbnail_url
        if request and url and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url
    
    def get_preview_url(self, obj):
        """Retourne l'URL de l'aperçu complet"""
        request = self.context.get("request")
        url = obj.preview_url
        if request and url and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url


class CVTemplateListSerializer(serializers.ModelSerializer):
    """Sérializer léger pour la liste"""
    thumbnail_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    
    class Meta:
        model = CVTemplate
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "category",
            "category_display",
            "thumbnail_url",
            "preview_url",
            "preview_image_url",
            "docx_filename",
            "long_description",
            "is_premium",
            "is_active",
            "order",
        )
        read_only_fields = fields
    
    def get_thumbnail_url(self, obj):
        """Retourne l'URL de la miniature"""
        request = self.context.get("request")
        url = obj.thumbnail_url
        if request and url and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url

    def get_preview_url(self, obj):
        """Retourne l'URL de l'aperçu complet"""
        request = self.context.get("request")
        url = obj.preview_url
        if request and url and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url
