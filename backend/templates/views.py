from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import CVTemplate
from .serializers import CVTemplateSerializer, CVTemplateListSerializer


class TemplateListView(ListAPIView):
    """
    GET /api/templates/ — liste tous les modèles de CV actifs.
    """
    serializer_class = CVTemplateListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # La BDD est la source de vérité (catalogue géré via `seed_catalog`).
        return CVTemplate.objects.filter(is_active=True)


class TemplateDetailView(RetrieveAPIView):
    """
    GET /api/templates/{id}/ — détail complet d'un modèle avec aperçus.
    """
    serializer_class = CVTemplateSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return CVTemplate.objects.filter(is_active=True)


class TemplateLibrarySyncView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        from .services.template_library import align_template_manifest
        from .services.public_catalog import sync_public_template_catalog

        result = align_template_manifest()
        public_count = sync_public_template_catalog()
        return Response({
            "detail": "Modèles synchronisés.",
            "public_count": public_count,
            **result,
        })
