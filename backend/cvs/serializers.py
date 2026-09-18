from rest_framework import serializers
from templates.serializers import CVTemplateSerializer
from .models import AccessGrant, CV, PaymentTransaction


class CVSerializer(serializers.ModelSerializer):
    template_detail = CVTemplateSerializer(source="template", read_only=True)
    has_active_access = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()

    class Meta:
        model = CV
        fields = (
            "id",
            "template",
            "template_detail",
            "title",
            "status",
            "data",
            "source_file",
            "photo_file",
            "job_offer_file",
            "job_offer_url",
            "job_offer_text",
            "template_mode",
            "is_reference",
            "cover_letter",
            "ai_status",
            "ai_error",
            "ai_data",
            "ai_messages",
            "generated_file",
            "generated_pdf",
            "generated_at",
            "has_active_access",
            "is_public",
            "public_url",
            "public_view_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "status",
            "is_reference",
            "source_file",
            "photo_file",
            "job_offer_file",
            "ai_status",
            "ai_error",
            "ai_data",
            "ai_messages",
            "generated_file",
            "generated_pdf",
            "generated_at",
            "has_active_access",
            "is_public",
            "public_view_count",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def get_has_active_access(self, obj):
        from .services.access import has_active_access

        return has_active_access(obj.user, obj)

    def get_public_url(self, obj):
        # Chemin relatif : le frontend préfixe avec son propre domaine
        # (window.location.origin), pour rester correct en local comme en prod.
        if not (obj.is_public and obj.public_slug):
            return ""
        return f"/cv/{obj.public_slug}"


class CVListSerializer(serializers.ModelSerializer):
    """Liste dashboard avec assez de données pour afficher un aperçu fidèle."""
    template_name = serializers.CharField(source="template.name", read_only=True)
    template_detail = CVTemplateSerializer(source="template", read_only=True)
    has_active_access = serializers.SerializerMethodField()
    has_job_offer = serializers.SerializerMethodField()
    has_cover_letter = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()

    class Meta:
        model = CV
        fields = (
            "id",
            "template",
            "template_name",
            "template_detail",
            "title",
            "status",
            "data",
            "is_reference",
            "has_job_offer",
            "has_cover_letter",
            "ai_status",
            "generated_file",
            "generated_pdf",
            "generated_at",
            "has_active_access",
            "is_public",
            "public_url",
            "public_view_count",
            "created_at",
            "updated_at",
        )

    def get_has_active_access(self, obj):
        from .services.access import has_active_access

        return has_active_access(obj.user, obj)

    def get_public_url(self, obj):
        if not (obj.is_public and obj.public_slug):
            return ""
        return f"/cv/{obj.public_slug}"

    def get_has_job_offer(self, obj):
        return bool((obj.job_offer_text or "").strip() or obj.job_offer_url or obj.job_offer_file)

    def get_has_cover_letter(self, obj):
        return bool((obj.cover_letter or "").strip())


class CVContextSerializer(serializers.Serializer):
    MAX_SOURCE_FILE_SIZE = 5 * 1024 * 1024

    source_file = serializers.FileField(required=False, allow_empty_file=False)
    photo_file = serializers.FileField(required=False, allow_empty_file=False)
    job_offer_file = serializers.FileField(required=False, allow_empty_file=False)
    job_offer_url = serializers.URLField(required=False, allow_blank=True)
    job_offer_text = serializers.CharField(required=False, allow_blank=True)
    template_mode = serializers.ChoiceField(choices=CV.TEMPLATE_MODE_CHOICES, required=False)

    def validate_source_file(self, value):
        suffix = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
        if suffix != "pdf":
            raise serializers.ValidationError("Ancien CV accepté: PDF uniquement.")
        if value.size > self.MAX_SOURCE_FILE_SIZE:
            raise serializers.ValidationError("Ancien CV trop lourd: 5 MB maximum.")
        return value


class AIImproveSerializer(serializers.Serializer):
    instruction = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class PlanSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    amount_xof = serializers.IntegerField()
    description = serializers.CharField()
    duration_hours = serializers.IntegerField(required=False, allow_null=True)
    ai_credits = serializers.IntegerField(required=False, allow_null=True)


class PaymentInitializeSerializer(serializers.Serializer):
    plan_type = serializers.ChoiceField(choices=PaymentTransaction.PLAN_CHOICES)
    cv = serializers.IntegerField(required=False, allow_null=True)


class PaymentVerifySerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=120)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = (
            "id",
            "cv",
            "plan_type",
            "amount_xof",
            "currency",
            "reference",
            "authorization_url",
            "access_code",
            "status",
            "paid_at",
            "created_at",
        )
        read_only_fields = fields


class AccessGrantSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = AccessGrant
        fields = (
            "id",
            "cv",
            "plan_type",
            "starts_at",
            "expires_at",
            "ai_credits",
            "is_active",
            "created_at",
        )
        read_only_fields = fields
