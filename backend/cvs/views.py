import threading
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
        # Le CV de référence est toujours listé en premier.
        return (
            CV.objects.filter(user=self.request.user)
            .select_related("template")
            .order_by("-is_reference", "-updated_at")
        )

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
        # Une ou plusieurs pièces jointes pour l'offre (images et/ou PDF, en
        # nombre libre — ex. une offre en 2-3 captures d'écran, ou un PDF).
        # Le texte de CHAQUE fichier est extrait selon son vrai type (OCR/vision
        # pour une image, pdftotext pour un PDF) puis concaténé dans
        # job_offer_text, qui est la source prioritaire pour l'adaptation.
        offer_files = request.FILES.getlist("job_offer_file")
        if offer_files:
            cv.job_offer_file = offer_files[0]
            from .services.ai import extract_uploaded_files_text

            extracted = extract_uploaded_files_text(offer_files)
            if extracted:
                manual_text = (data.get("job_offer_text") or "").strip()
                cv.job_offer_text = f"{manual_text}\n\n{extracted}".strip() if manual_text else extracted
        if "job_offer_url" in data:
            cv.job_offer_url = data.get("job_offer_url") or ""
        if not offer_files and "job_offer_text" in data:
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


def _run_product_signals(cv_id):
    """Après une analyse IA réussie : repère les infos sans champ dédié
    (FieldSuggestion) et fait noter le visuel du PDF importé pour un futur
    modèle (TemplateSubmission). Tourne en tâche de fond (pas de file Celery
    ici) pour ne pas ralentir la réponse à l'utilisateur ; échoue en
    silence, ces signaux sont un bonus produit, jamais bloquants."""
    from django.db import connections

    def _worker():
        try:
            from .services.ai import record_field_suggestions, score_template_design

            cv = CV.objects.filter(pk=cv_id).select_related("user").first()
            if not cv:
                return
            record_field_suggestions(cv)
            score_template_design(cv)
        except Exception:
            pass
        finally:
            connections.close_all()

    threading.Thread(target=_worker, daemon=True).start()


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
            _run_product_signals(cv.id)
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

        # Fichier périmé si le CV a été modifié APRÈS la dernière génération, OU
        # si le moteur de rendu a changé depuis (correctifs de design : sans ça,
        # l'utilisateur retélécharge un ancien rendu différent de l'aperçu).
        from datetime import timedelta

        stale = bool(cv.generated_at and cv.updated_at and cv.updated_at > cv.generated_at + timedelta(seconds=10))
        stale = stale or bool(cv.generated_at and cv.generated_at.timestamp() < _renderers_version())
        if stale and cv.generated_pdf:
            allowed, _message = require_generation_access(request.user, cv)
            if allowed:
                try:
                    from .generator import generate_cv_documents

                    generate_cv_documents(cv)
                except Exception:
                    pass  # au pire on sert le dernier fichier disponible

        file_format = request.query_params.get("file") or request.query_params.get("download_format") or "pdf"
        file_field = cv.generated_file if file_format == "docx" else cv.generated_pdf
        if not file_field:
            return Response(
                {"detail": "Aucun fichier généré pour ce CV."},
                status=status.HTTP_404_NOT_FOUND,
            )
        filename = Path(file_field.name).name
        return FileResponse(file_field.open("rb"), as_attachment=True, filename=filename)


def _renderers_version():
    """Version du moteur de rendu (mtime le plus récent des templates HTML ET du
    code python des renderers) : sert à invalider le cache d'aperçu et à
    détecter les PDF générés avec une ancienne version du design."""
    from pathlib import Path

    base = Path(__file__).resolve().parent
    candidates = list((base / "templates" / "cvs" / "html_renderers").glob("*.html"))
    candidates += list((base / "renderers").glob("*.py"))
    try:
        return max(int(path.stat().st_mtime) for path in candidates)
    except ValueError:
        return 0


class CVPreviewView(APIView):
    """
    POST /api/cvs/preview/ — rend le HTML d'un CV (modèle + données) sans le sauvegarder.
    C'est la source unique : ce HTML alimente l'aperçu navigateur ET le PDF final.
    """

    def post(self, request):
        import hashlib
        import json

        from django.core.cache import cache

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

        # Le rendu « 1 page garantie » coûte plusieurs passes WeasyPrint (jusqu'à
        # 15-30 s sur un CV dense) : on met le HTML en cache par contenu pour que
        # les demandes identiques (double composant d'aperçu, retours en arrière,
        # re-clics) soient instantanées. L'empreinte inclut la version des
        # fichiers de rendu : une modification de style invalide le cache.
        fingerprint = hashlib.md5(
            f"{template.pk}:{int(fast)}:{_renderers_version()}:"
            f"{json.dumps(data, sort_keys=True, ensure_ascii=False)}".encode()
        ).hexdigest()
        cache_key = f"cv-preview-{fingerprint}"
        html = cache.get(cache_key)
        if html is None:
            try:
                html = render_cv_html(template, data) if fast else resolve_cv_html(template, data)
            except Exception as exc:
                return Response({"detail": f"Aperçu indisponible : {exc}"}, status=status.HTTP_400_BAD_REQUEST)
            cache.set(cache_key, html, 15 * 60)
        return Response({"html": html})


class CVAdaptPreviewView(APIView):
    """POST /api/cvs/{id}/adapt/ — compare le CV à l'offre fournie et renvoie
    les propositions en miroir SANS modifier le CV : {report, adapted_data}.
    C'est le bouton « Remplacer » côté client qui applique ensuite."""

    def post(self, request, pk):
        cv = CV.objects.filter(user=request.user).filter(pk=pk).select_related("template").first()
        if not cv:
            return Response({"detail": "CV non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        allowed, message = require_ai_access(request.user, cv)
        if not allowed:
            return Response({"detail": message, "access": access_payload(request.user, cv)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        from .services.ai import AIServiceError, adapt_cv_proposals

        try:
            report, adapted = adapt_cv_proposals(cv)
        except AIServiceError as exc:
            return Response(
                {"detail": str(exc), "code": getattr(exc, "code", "ai_error")},
                status=getattr(exc, "status_code", 500),
            )
        return Response({"report": report, "adapted_data": adapted})


class CVAdaptApplyView(APIView):
    """POST /api/cvs/{id}/adapt/apply/ — crée un NOUVEAU CV avec les données
    adaptées, titré avec le poste visé. L'ORIGINAL n'est jamais modifié : c'est
    toujours lui qu'on ré-adapte pour les prochaines offres.
    Body: {adapted_data} -> CV créé (201)."""

    def post(self, request, pk):
        cv = CV.objects.filter(user=request.user).filter(pk=pk).select_related("template").first()
        if not cv:
            return Response({"detail": "CV non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        adapted = request.data.get("adapted_data")
        if not isinstance(adapted, dict) or not adapted:
            return Response({"detail": "Données adaptées manquantes."}, status=status.HTTP_400_BAD_REQUEST)

        # Mêmes garanties que la prévisualisation, même si le client a modifié
        # le payload : photo/sections gérées par le front + diplômes/certifs
        # strictement identiques à l'original.
        from .services.ai import _restore_protected_sections

        current = cv.data or {}
        for key in ("photo_url", "enabled_sections", "section_order"):
            if current.get(key):
                adapted[key] = current[key]
        _restore_protected_sections(current, adapted, {})

        # Titre qui donne l'idée du CV dès la première ligne de la carte :
        # le poste visé d'abord, la mention d'adaptation ensuite.
        job_title = str(adapted.get("job_title") or "").strip()
        title = f"{job_title} — CV adapté" if job_title else f"CV adapté — {cv.title or 'Mon CV'}"
        new_cv = CV.objects.create(
            user=request.user,
            template=cv.template,
            title=title[:255],
            data=adapted,
            photo_file=cv.photo_file or None,
            job_offer_url=cv.job_offer_url,
            job_offer_text=cv.job_offer_text,
            job_offer_file=cv.job_offer_file or None,
            template_mode=cv.template_mode,
        )
        return Response(CVSerializer(new_cv, context={"request": request}).data, status=status.HTTP_201_CREATED)


class CVSetReferenceView(APIView):
    """POST /api/cvs/{id}/reference/ — définit CE CV comme CV de référence
    (un seul par utilisateur : c'est lui qu'on adapte à toutes les offres)."""

    def post(self, request, pk):
        cv = CV.objects.filter(user=request.user).filter(pk=pk).select_related("template").first()
        if not cv:
            return Response({"detail": "CV non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        CV.objects.filter(user=request.user, is_reference=True).exclude(pk=cv.pk).update(is_reference=False)
        if not cv.is_reference:
            cv.is_reference = True
            cv.save(update_fields=["is_reference"])
        return Response(CVSerializer(cv, context={"request": request}).data)


class CVCoverLetterView(APIView):
    """POST /api/cvs/{id}/cover-letter/ — rédige la lettre de motivation du CV
    (basée sur le CV adapté + l'offre) et la sauvegarde sur le CV.
    Body: {instruction?} -> {letter, objet, corps}."""

    def post(self, request, pk):
        cv = CV.objects.filter(user=request.user).filter(pk=pk).select_related("template").first()
        if not cv:
            return Response({"detail": "CV non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        allowed, message = require_ai_access(request.user, cv)
        if not allowed:
            return Response({"detail": message, "access": access_payload(request.user, cv)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        from .services.ai import AIServiceError, write_cover_letter

        instruction = str(request.data.get("instruction") or "")
        try:
            result = write_cover_letter(cv, instruction=instruction)
        except AIServiceError as exc:
            return Response(
                {"detail": str(exc), "code": getattr(exc, "code", "ai_error")},
                status=getattr(exc, "status_code", 500),
            )
        objet, corps = result["objet"], result["corps"]
        letter = f"Objet : {objet}\n\n{corps}" if objet else corps
        cv.cover_letter = letter
        cv.save(update_fields=["cover_letter", "updated_at"])
        return Response({"letter": letter, "objet": objet, "corps": corps})


class CVCoverLetterDownloadView(APIView):
    """GET /api/cvs/{id}/cover-letter/download/ — PDF de la lettre (rendu
    WeasyPrint accordé à la palette du modèle du CV)."""

    def get(self, request, pk):
        cv = CV.objects.filter(user=request.user).filter(pk=pk).select_related("template").first()
        if not cv:
            return Response({"detail": "CV non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        if not (cv.cover_letter or "").strip():
            return Response(
                {"detail": "Aucune lettre de motivation pour ce CV : rédige-la d'abord."},
                status=status.HTTP_404_NOT_FOUND,
            )

        import io

        from .renderers.html import render_cover_letter_pdf_bytes

        try:
            pdf_bytes = render_cover_letter_pdf_bytes(cv)
        except Exception as exc:
            return Response({"detail": f"PDF de la lettre indisponible : {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = cv.data or {}
        name_part = "-".join(part for part in [str(data.get("first_name") or ""), str(data.get("last_name") or "")] if part)
        filename = f"lettre-motivation-{name_part or cv.pk}.pdf".replace(" ", "-").lower()
        return FileResponse(io.BytesIO(pdf_bytes), as_attachment=True, filename=filename)


class CVAssistantChatView(APIView):
    """POST /api/cvs/assistant/chat/ — dialogue guidé de création de CV.
    Body: {messages: [{role, content}…]} -> {reply, done, covered, missing}.
    `covered`/`missing` viennent d'une extraction automatique tournant à
    chaque tour : le front peut s'en servir pour proposer de continuer avant
    même que l'assistant ait formellement terminé (ex. après un gros pavé de
    texte collé d'un coup)."""

    def post(self, request):
        from .services.ai import AIServiceError, assistant_chat

        messages = request.data.get("messages") or []
        try:
            reply, done, covered, missing = assistant_chat(messages)
        except AIServiceError as exc:
            return Response(
                {"detail": str(exc), "code": getattr(exc, "code", "ai_error")},
                status=getattr(exc, "status_code", 500),
            )
        return Response({"reply": reply, "done": done, "covered": covered, "missing": missing})


class CVAssistantFinalizeView(APIView):
    """POST /api/cvs/assistant/finalize/ — organise les réponses du dialogue en
    données de CV structurées. Body: {messages} -> {data}."""

    def post(self, request):
        from .services.ai import AIServiceError, assistant_finalize

        messages = request.data.get("messages") or []
        try:
            data = assistant_finalize(messages)
        except AIServiceError as exc:
            return Response(
                {"detail": str(exc), "code": getattr(exc, "code", "ai_error")},
                status=getattr(exc, "status_code", 500),
            )
        return Response({"data": data})


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
