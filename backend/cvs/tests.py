import io
import json
import shutil
import subprocess
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient
from templates.models import CVTemplate

from .models import AccessGrant, CV, PaymentTransaction
from .services.payments import verify_payment


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CVGenerationAPITest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username="user", password="password123")
        self.template = CVTemplate.objects.create(
            name="Modele test",
            slug="modele-test",
            docx_filename="modele_simple.docx",
        )
        self.cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="CV test",
            data={
                "first_name": "Awa",
                "last_name": "Kone",
                "job_title": "Developpeuse web",
                "email": "awa@example.com",
                "experiences": [],
                "education": [],
                "skills": ["React", "Django"],
            },
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch("cvs.generator._convert_docx_to_pdf", return_value=b"%PDF-1.4\n% test pdf")
    def test_generate_then_download_pdf_and_docx(self, _convert):
        response = self.client.post(f"/api/cvs/{self.cv.id}/generate/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["cv"]["status"], CV.STATUS_GENERATED)
        self.assertTrue(response.data["cv"]["generated_file"])
        self.assertTrue(response.data["cv"]["generated_pdf"])

        self.cv.refresh_from_db()
        self.assertTrue(self.cv.generated_file.name.endswith(".docx"))
        self.assertTrue(self.cv.generated_pdf.name.endswith(".pdf"))
        _convert.assert_called_once()

        download_response = self.client.get(f"/api/cvs/{self.cv.id}/download/")

        self.assertEqual(download_response.status_code, 200)
        self.assertIn("attachment", download_response["Content-Disposition"])
        self.assertIn(".pdf", download_response["Content-Disposition"])

        docx_response = self.client.get(f"/api/cvs/{self.cv.id}/download/?file=docx")

        self.assertEqual(docx_response.status_code, 200)
        self.assertIn("attachment", docx_response["Content-Disposition"])
        self.assertIn(".docx", docx_response["Content-Disposition"])

    @patch("cvs.generator._convert_docx_to_pdf", return_value=b"%PDF-1.4\n% test pdf")
    def test_generate_without_docx_filename_uses_programmatic_renderer(self, _convert):
        template = CVTemplate.objects.create(
            name="Modele visuel",
            slug="modele-visuel",
            category="modern",
            docx_filename="",
        )
        cv = CV.objects.create(
            user=self.user,
            template=template,
            title="CV visuel",
            data=self.cv.data,
        )

        response = self.client.post(f"/api/cvs/{cv.id}/generate/")

        self.assertEqual(response.status_code, 200)
        cv.refresh_from_db()
        self.assertTrue(cv.generated_file.name.endswith(".docx"))
        self.assertTrue(cv.generated_pdf.name.endswith(".pdf"))
        _convert.assert_called_once()

    def test_html_renderer_builds_template_html_from_cv_data(self):
        from cvs.renderers.html import render_cv_html

        template = CVTemplate.objects.get(slug="galerie-cv-001")

        html = render_cv_html(template, self.cv.data)

        self.assertIn("Awa Kone", html)
        self.assertIn("Developpeuse web", html)
        self.assertIn("React", html)

    @patch("cvs.generator._convert_docx_to_pdf")
    @patch("cvs.generator._render_gallery_pdf_bytes")
    @patch("cvs.renderers.html.render_html_cv_pdf_bytes", return_value=b"%PDF-1.4\n% html renderer")
    def test_gallery_pilot_uses_html_renderer_for_pdf(self, render_html, render_gallery, convert):
        template = CVTemplate.objects.get(slug="galerie-cv-001")
        cv = CV.objects.create(
            user=self.user,
            template=template,
            title="CV HTML",
            data=self.cv.data,
        )

        response = self.client.post(f"/api/cvs/{cv.id}/generate/")

        self.assertEqual(response.status_code, 200)
        cv.refresh_from_db()
        self.assertTrue(cv.generated_pdf.name.endswith(".pdf"))
        render_html.assert_called_once()
        render_gallery.assert_not_called()
        convert.assert_not_called()

    def test_context_upload_accepts_missing_profile_photo(self):
        response = self.client.post(
            f"/api/cvs/{self.cv.id}/context/",
            {"job_offer_text": "Offre test"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["job_offer_text"], "Offre test")
        self.assertFalse(response.data["data"].get("photo_url"))

    def test_context_upload_saves_profile_photo_url(self):
        image_buffer = io.BytesIO()
        Image.new("RGB", (320, 420), "#ffffff").save(image_buffer, "PNG")
        image_buffer.seek(0)
        photo = SimpleUploadedFile("photo.png", image_buffer.read(), content_type="image/png")

        response = self.client.post(
            f"/api/cvs/{self.cv.id}/context/",
            {"photo_file": photo},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("/media/cvs/photos/", response.data["data"]["photo_url"])

    def test_context_upload_rejects_unreadable_source_cv_format(self):
        image_buffer = io.BytesIO()
        Image.new("RGB", (320, 420), "#ffffff").save(image_buffer, "PNG")
        image_buffer.seek(0)
        source = SimpleUploadedFile("ancien-cv.png", image_buffer.read(), content_type="image/png")

        photo_buffer = io.BytesIO()
        Image.new("RGB", (320, 420), "#ffffff").save(photo_buffer, "PNG")
        photo_buffer.seek(0)
        photo = SimpleUploadedFile("photo.png", photo_buffer.read(), content_type="image/png")

        response = self.client.post(
            f"/api/cvs/{self.cv.id}/context/",
            {"source_file": source, "photo_file": photo},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("source_file", response.data)

    def test_context_upload_rejects_large_source_pdf(self):
        source = SimpleUploadedFile("ancien-cv.pdf", b"x" * (5 * 1024 * 1024 + 1), content_type="application/pdf")

        response = self.client.post(
            f"/api/cvs/{self.cv.id}/context/",
            {"source_file": source},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("source_file", response.data)

    @override_settings(CV_OCR_LANGUAGES="fra+eng", CV_OCR_MAX_PAGES=2, CV_OCR_DPI=144)
    @patch("cvs.services.ai.shutil.which")
    @patch("cvs.services.ai.subprocess.run")
    def test_pdf_ocr_extracts_text_when_tesseract_available(self, run, which):
        from .services.ai import _extract_pdf_ocr

        which.side_effect = lambda name: f"/usr/bin/{name}" if name in {"tesseract", "pdftoppm"} else None

        def fake_run(args, **kwargs):
            if args[0].endswith("pdftoppm"):
                prefix = Path(args[-1])
                Image.new("RGB", (900, 1200), "#ffffff").save(prefix.parent / f"{prefix.name}-1.png", "PNG")
                return subprocess.CompletedProcess(args, 0, "", "")
            if args[0].endswith("tesseract"):
                return subprocess.CompletedProcess(
                    args,
                    0,
                    "Jean Dupont\njean.dupont@example.com\nDeveloppeur Django avec cinq ans experience projets web API REST React SQL CI CD",
                    "",
                )
            return subprocess.CompletedProcess(args, 1, "", "unexpected")

        run.side_effect = fake_run
        with tempfile.NamedTemporaryFile(suffix=".pdf") as pdf:
            pdf.write(b"%PDF-1.4\n")
            pdf.flush()
            text = _extract_pdf_ocr(Path(pdf.name))

        self.assertIn("Jean Dupont", text)
        self.assertGreaterEqual(run.call_count, 2)
        self.assertIn("--psm", run.call_args_list[-1].args[0])

    @override_settings(AI_PROVIDER="groq", GROQ_API_KEY="gsk-test", GROQ_MODEL="openai/gpt-oss-120b")
    @patch("cvs.services.ai.urllib.request.urlopen")
    def test_ai_quota_error_returns_friendly_message(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.groq.com/openai/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(
                b'{"error":{"message":"You exceeded your current quota","type":"insufficient_quota","code":"insufficient_quota"}}'
            ),
        )

        response = self.client.post(f"/api/cvs/{self.cv.id}/ai/improve/", {"instruction": ""}, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "insufficient_quota")
        self.assertIn("quota Groq", response.data["detail"])
        self.assertNotIn("You exceeded your current quota", response.data["detail"])
        request = urlopen.call_args.args[0]
        headers = {name.lower(): value for name, value in request.header_items()}
        self.assertEqual(headers["user-agent"], "CVBuilder/1.0")
        self.cv.refresh_from_db()
        self.assertIn("quota Groq", self.cv.ai_error)

    @override_settings(AI_PROVIDER="groq", GROQ_API_KEY="gsk-test", GROQ_MODEL="openai/gpt-oss-120b")
    @patch("cvs.services.ai.urllib.request.urlopen")
    def test_ai_forbidden_error_does_not_report_invalid_key(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.groq.com/openai/v1/chat/completions",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=io.BytesIO(b"error code: 1010"),
        )

        response = self.client.post(f"/api/cvs/{self.cv.id}/ai/improve/", {"instruction": ""}, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "groq_error")
        self.assertIn("bloqué", response.data["detail"])
        self.assertNotIn("clé Groq", response.data["detail"])

    @override_settings(AI_PROVIDER="groq", GROQ_API_KEY="gsk-test", GROQ_MODEL="openai/gpt-oss-120b")
    @patch("cvs.services.ai.extract_file_text", return_value="")
    @patch("cvs.services.ai._ai_responses_create")
    def test_ai_rejects_unreadable_source_pdf_before_groq(self, ai_request, _extract_text):
        source = SimpleUploadedFile("scan-vide.pdf", b"%PDF-1.4\n% image-only", content_type="application/pdf")
        self.cv.source_file.save("scan-vide.pdf", source, save=True)

        response = self.client.post(f"/api/cvs/{self.cv.id}/ai/improve/", {"instruction": ""}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "source_cv_unreadable")
        ai_request.assert_not_called()

    @override_settings(
        AI_PROVIDER="groq",
        GROQ_API_KEY="",
        OPENAI_API_KEY="sk-real",
        OPENAI_MODEL="gpt-test",
    )
    @patch("cvs.services.ai._ai_responses_create")
    def test_ai_does_not_fallback_to_openai_when_groq_is_selected(self, ai_request):
        response = self.client.post(f"/api/cvs/{self.cv.id}/ai/improve/", {"instruction": ""}, format="json")

        self.assertEqual(response.status_code, 200)
        ai_request.assert_not_called()
        self.assertIn("GROQ_API_KEY", response.data["ai"]["fit_summary"])

    @override_settings(AI_PROVIDER="openai", OPENAI_API_KEY="sk-real", OPENAI_MODEL="gpt-test")
    @patch("cvs.services.ai._pdf_pages_image_content", return_value=[{"type": "input_image", "image_url": "data:image/jpeg;base64,abc"}])
    @patch("cvs.services.ai.extract_file_text", return_value="")
    @patch("cvs.services.ai._ai_responses_create")
    def test_ai_sends_pdf_page_images_to_openai_when_source_text_is_empty(self, ai_request, _extract_text, pdf_images):
        source = SimpleUploadedFile("ancien-cv.pdf", b"%PDF-1.4\n% image-only", content_type="application/pdf")
        self.cv.source_file.save("ancien-cv.pdf", source, save=True)
        ai_request.return_value = {
            "output_text": json.dumps(
                {
                    "data": {
                        "first_name": "Awa",
                        "last_name": "Kone",
                        "job_title": "Developpeuse web",
                        "photo_url": "",
                        "phone": "",
                        "email": "",
                        "address": "",
                        "linkedin": "",
                        "driving_license": "",
                        "profile": "Profil extrait depuis image.",
                        "experiences": [],
                        "education": [],
                        "skills": [],
                        "languages": [],
                        "hobbies": [],
                        "extra_sections": [],
                    },
                    "fit_summary": "OK",
                    "missing_info_questions": [],
                    "change_log": ["OCR visuel"],
                    "template_recommendation": {"mode": "selected", "notes": ""},
                }
            )
        }

        response = self.client.post(f"/api/cvs/{self.cv.id}/ai/improve/", {"instruction": ""}, format="json")

        self.assertEqual(response.status_code, 200)
        pdf_images.assert_called_once()
        payload = ai_request.call_args.args[0]
        content = payload["input"][0]["content"]
        self.assertTrue(any(item.get("type") == "input_image" for item in content))

    def test_duplicate_cv(self):
        response = self.client.post(f"/api/cvs/{self.cv.id}/duplicate/")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "Copie de CV test")
        self.assertEqual(response.data["template"], self.template.id)
        self.assertEqual(CV.objects.filter(user=self.user).count(), 2)

    def test_delete_cv(self):
        response = self.client.delete(f"/api/cvs/{self.cv.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(CV.objects.filter(pk=self.cv.id).exists())


class PaymentVerificationSecurityTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="payer", email="payer@example.com", password="password123")
        self.template = CVTemplate.objects.create(
            name="Modele paiement",
            slug="modele-paiement",
            docx_filename="modele_simple.docx",
        )
        self.cv = CV.objects.create(user=self.user, template=self.template, title="CV paiement")
        self.payment = PaymentTransaction.objects.create(
            user=self.user,
            cv=self.cv,
            plan_type=PaymentTransaction.PLAN_SINGLE_CV,
            amount_xof=200,
            currency="XOF",
            reference="cvb_test_reference",
        )

    def paystack_response(self, **overrides):
        data = {
            "status": "success",
            "amount": self.payment.amount_xof * settings.PAYSTACK_SUBUNIT_MULTIPLIER,
            "currency": self.payment.currency,
            "metadata": {
                "user_id": self.user.id,
                "cv_id": self.cv.id,
                "plan_type": self.payment.plan_type,
                "amount_xof": self.payment.amount_xof,
            },
        }
        data.update(overrides)
        return {"data": data}

    @patch("cvs.services.payments._paystack_request")
    def test_verify_payment_validates_amount_and_grants_access(self, paystack_request):
        paystack_request.return_value = self.paystack_response()

        payment = verify_payment(self.payment.reference, user=self.user)

        self.assertEqual(payment.status, PaymentTransaction.STATUS_SUCCESS)
        self.assertTrue(
            AccessGrant.objects.filter(
                payment=payment,
                user=self.user,
                cv=self.cv,
                plan_type=PaymentTransaction.PLAN_SINGLE_CV,
            ).exists()
        )

    @patch("cvs.services.payments._paystack_request")
    def test_verify_payment_rejects_amount_mismatch(self, paystack_request):
        expected_amount = self.payment.amount_xof * settings.PAYSTACK_SUBUNIT_MULTIPLIER
        paystack_request.return_value = self.paystack_response(amount=expected_amount - 1)

        with self.assertRaisesMessage(ValueError, "Montant Paystack invalide."):
            verify_payment(self.payment.reference, user=self.user)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentTransaction.STATUS_PENDING)
        self.assertFalse(AccessGrant.objects.filter(payment=self.payment).exists())
