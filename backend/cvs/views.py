from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CV
from .serializers import (
    AIImproveSerializer,
    CVContextSerializer,
    CVListSerializer,
    CVSerializer,
    PaymentInitializeSerializer,
    PaymentTransactionSerializer,
    PaymentVerifySerializer,
)
from .services.access import access_payload, payment_plans, require_ai_access, require_generation_access


class CVListCreateView(ListCreateAPIView):
    def get_queryset(self):
        return CV.objects.filter(user=self.request.user).select_related("template")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CVListSerializer
        return CVSerializer


class CVDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = CVSerializer

    def get_queryset(self):
        return CV.objects.filter(user=self.request.user).select_related("template")


class CVContextUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        cv = CV.objects.filter(user=request.user).filter(pk=pk).first()
        if not cv:
            return Response({"detail": "CV non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CVContextSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get("source_file"):
            cv.source_file = data["source_file"]
        if data.get("photo_file"):
            cv.photo_file = data["photo_file"]
        if data.get("job_offer_file"):
            cv.job_offer_file = data["job_offer_file"]
        if "job_offer_url" in data:
            cv.job_offer_url = data.get("job_offer_url") or ""
        if "job_offer_text" in data:
            cv.job_offer_text = data.get("job_offer_text") or ""
        if data.get("template_mode"):
            cv.template_mode = data["template_mode"]
        cv.ai_status = CV.AI_STATUS_IDLE
        cv.ai_error = ""
        update_fields = [
            "source_file",
            "photo_file",
            "job_offer_file",
            "job_offer_url",
            "job_offer_text",
            "template_mode",
            "ai_status",
            "ai_error",
            "updated_at",
        ]
        cv.save(update_fields=update_fields)

        photo_url = ""
        if cv.photo_file:
            from .services.photo import PhotoError, save_cv_portrait

            try:
                photo_url = save_cv_portrait(cv.photo_file.path, cv, request=request)
            except PhotoError as exc:
                return Response({"detail": str(exc), "code": "invalid_photo"}, status=status.HTTP_400_BAD_REQUEST)
        if not photo_url and cv.source_file:
            from .services.ai import extract_source_photo_url

            photo_url = extract_source_photo_url(cv, request=request)
        if photo_url:
            cv.data = {**(cv.data or {}), "photo_url": photo_url}
            cv.save(update_fields=["data", "updated_at"])

        return Response(CVSerializer(cv, context={"request": request}).data)


class CVAIImproveView(APIView):
    def post(self, request, pk):
        cv = CV.objects.filter(user=request.user).filter(pk=pk).select_related("template").first()
        if not cv:
            return Response({"detail": "CV non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        allowed, message = require_ai_access(request.user, cv)
        if not allowed:
            return Response({"detail": message, "access": access_payload(request.user, cv)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        serializer = AIImproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instruction = serializer.validated_data.get("instruction", "")

        cv.ai_status = CV.AI_STATUS_PROCESSING
        cv.ai_error = ""
        cv.save(update_fields=["ai_status", "ai_error", "updated_at"])
        try:
            from .services.ai import improve_cv, merge_ai_result

            result = improve_cv(cv, instruction=instruction)
            merge_ai_result(cv, result, instruction=instruction)
            return Response({
                "detail": "CV optimisé par IA.",
                "cv": CVSerializer(cv, context={"request": request}).data,
                "ai": result,
                "access": access_payload(request.user, cv),
            })
        except Exception as exc:
            message = str(exc)
            error_status = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
            cv.ai_status = CV.AI_STATUS_FAILED
            cv.ai_error = message
            cv.status = CV.STATUS_FAILED
            cv.save(update_fields=["ai_status", "ai_error", "status", "updated_at"])
            return Response(
                {
                    "detail": f"Erreur IA: {message}",
                    "code": getattr(exc, "code", "ai_error"),
                    "access": access_payload(request.user, cv),
                },
                status=error_status,
            )


class CVGenerateView(APIView):
    def post(self, request, pk):
        cv = CV.objects.filter(user=request.user).filter(pk=pk).select_related("template").first()
        if not cv:
            return Response({"detail": "CV non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        if not (cv.data or {}).get("photo_url"):
            return Response(
                {"detail": "Une photo de profil est obligatoire pour générer votre CV.", "code": "photo_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed, message = require_generation_access(request.user, cv)
        if not allowed:
            return Response({"detail": message, "access": access_payload(request.user, cv)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        try:
            from .generator import generate_cv_documents
            from .services.access import unlock_cv

            generate_cv_documents(cv)
            # Consomme 1 crédit hebdo si ce CV n'était pas encore débloqué (gratuit pendant l'essai).
            unlock_cv(request.user, cv)
            cv.refresh_from_db(fields=["is_unlocked"])
            pages = getattr(cv, "_page_count", 1)
            warning = None
            if pages > 1:
                warning = (
                    f"Ton CV tient sur {pages} pages. Pour un CV percutant sur 1 seule page, "
                    "allège le contenu (moins de missions par poste, sections plus courtes). "
                    "Les écritures restent à 10 pt minimum pour rester lisibles par les recruteurs."
                )
            return Response(
                {
                    "detail": "PDF généré.",
                    "download_url": cv.generated_pdf.url if cv.generated_pdf else None,
                    "docx_url": cv.generated_file.url if cv.generated_file else None,
                    "pages": pages,
                    "warning": warning,
                    "cv": CVSerializer(cv, context={"request": request}).data,
                },
                status=status.HTTP_200_OK,
            )
        except FileNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            cv.status = CV.STATUS_FAILED
            cv.save(update_fields=["status", "updated_at"])
            return Response({"detail": f"Erreur lors de la génération : {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CVDuplicateView(APIView):
    def post(self, request, pk):
        cv = CV.objects.filter(user=request.user).filter(pk=pk).first()
        if not cv:
            return Response({"detail": "CV non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        duplicate = CV.objects.create(
            user=request.user,
            template=cv.template,
            title=f"Copie de {cv.title}",
            data=cv.data or {},
            job_offer_url=cv.job_offer_url,
            job_offer_text=cv.job_offer_text,
            template_mode=cv.template_mode,
        )
        return Response(CVSerializer(duplicate, context={"request": request}).data, status=status.HTTP_201_CREATED)


class CVDownloadView(APIView):
    def get(self, request, pk):
        cv = CV.objects.filter(user=request.user).filter(pk=pk).first()
        if not cv:
            return Response({"detail": "CV non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        file_format = request.query_params.get("file") or request.query_params.get("download_format") or "pdf"
        file_field = cv.generated_file if file_format == "docx" else cv.generated_pdf
        if not file_field:
            return Response(
                {"detail": "Aucun fichier généré pour ce CV."},
                status=status.HTTP_404_NOT_FOUND,
            )
        filename = Path(file_field.name).name
        return FileResponse(file_field.open("rb"), as_attachment=True, filename=filename)


class CVPreviewView(APIView):
    """
    POST /api/cvs/preview/ — rend le HTML d'un CV (modèle + données) sans le sauvegarder.
    C'est la source unique : ce HTML alimente l'aperçu navigateur ET le PDF final.
    """

    def post(self, request):
        from templates.models import CVTemplate

        from .renderers.html import render_cv_html, resolve_cv_html

        template_id = request.data.get("template")
        data = request.data.get("data") or {}
        fast = bool(request.data.get("fast"))  # vignettes : rendu direct, sans la mesure 1-page

        template = None
        if template_id:
            template = CVTemplate.objects.filter(pk=template_id).first()
        if template is None:
            template = CVTemplate.objects.filter(is_active=True).first()
        if template is None:
            return Response({"detail": "Aucun modèle disponible."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            html = render_cv_html(template, data) if fast else resolve_cv_html(template, data)
        except Exception as exc:
            return Response({"detail": f"Aperçu indisponible : {exc}"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"html": html})


class CVRewriteView(APIView):
    """
    POST /api/cvs/rewrite/ — propose une version plus courte et fluide d'un texte.
    Body: {text, kind?: profile|mission|experience, max_words?}. Renvoie {rewrite}.
    """

    def post(self, request):
        from .services.ai import AIServiceError, rewrite_cv_text

        text = request.data.get("text") or ""
        kind = request.data.get("kind") or "texte"
        try:
            max_words = int(request.data.get("max_words") or 55)
        except (TypeError, ValueError):
            max_words = 55
        try:
            rewrite = rewrite_cv_text(text, kind=kind, max_words=max_words)
        except AIServiceError as exc:
            return Response(
                {"detail": str(exc), "code": getattr(exc, "code", "ai_error")},
                status=getattr(exc, "status_code", 500),
            )
        return Response({"rewrite": rewrite})


class CVProfileView(APIView):
    """POST /api/cvs/profile/ — rédige/améliore le profil à partir des infos. Body: {data} -> {profile}."""

    def post(self, request):
        from .services.ai import AIServiceError, write_profile

        data = request.data.get("data") or {}
        job_offer = request.data.get("job_offer") or ""
        try:
            profile = write_profile(data, job_offer=job_offer)
        except AIServiceError as exc:
            return Response(
                {"detail": str(exc), "code": getattr(exc, "code", "ai_error")},
                status=getattr(exc, "status_code", 500),
            )
        return Response({"profile": profile})


class CVCorrectView(APIView):
    """POST /api/cvs/correct/ — correction globale (fautes, accents, périodes). Body: {data} -> {data}."""

    def post(self, request):
        from .services.ai import AIServiceError, correct_cv_data

        data = request.data.get("data") or {}
        try:
            corrected = correct_cv_data(data)
        except AIServiceError as exc:
            return Response(
                {"detail": str(exc), "code": getattr(exc, "code", "ai_error")},
                status=getattr(exc, "status_code", 500),
            )
        return Response({"data": corrected})


class CVPlansView(APIView):
    def get(self, request):
        cv = None
        cv_id = request.query_params.get("cv")
        if cv_id:
            cv = CV.objects.filter(user=request.user, pk=cv_id).first()
        # Récupère les paiements bloqués (téléphone éteint, onglet fermé après paiement).
        if settings.PAYSTACK_SECRET_KEY:
            try:
                from .services.payments import reconcile_pending_payments

                reconcile_pending_payments(request.user)
            except Exception:
                pass
        return Response({
            "plans": payment_plans(),
            "access": access_payload(request.user, cv),
            "paystack_public_key": settings.PAYSTACK_PUBLIC_KEY,
            "payments_enforced": settings.PAYMENTS_ENFORCED,
        })


class PaymentInitializeView(APIView):
    def post(self, request):
        serializer = PaymentInitializeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            from .services.payments import initialize_payment

            payment = initialize_payment(
                request.user,
                serializer.validated_data["plan_type"],
                cv_id=serializer.validated_data.get("cv"),
            )
            return Response({
                "payment": PaymentTransactionSerializer(payment).data,
                "authorization_url": payment.authorization_url,
            }, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentVerifyView(APIView):
    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            from .services.payments import verify_payment

            payment = verify_payment(serializer.validated_data["reference"], user=request.user)
            return Response({
                "payment": PaymentTransactionSerializer(payment).data,
                "access": access_payload(request.user, payment.cv),
            })
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PaystackWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.headers.get("X-Paystack-Signature", "")
        try:
            from .services.payments import handle_webhook

            handle_webhook(request.body, signature)
            return Response({"detail": "ok"})
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
