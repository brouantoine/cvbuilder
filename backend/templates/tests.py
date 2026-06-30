import json
import shutil
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings
from .models import CVTemplate


class SeededTemplatesTest(TestCase):
    def test_configured_templates_are_seeded(self):
        templates = CVTemplate.objects.filter(
            slug__in=["modele-simple", "modele-classique", "modele-moderne", "modele-compact"]
        )

        self.assertEqual(templates.count(), 4)
        self.assertTrue(all(template.docx_filename == "modele_simple.docx" for template in templates))


class TemplateLibrarySyncTest(TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmpdir, ignore_errors=True))

    def test_align_template_manifest_adds_docx_files(self):
        from .services.template_library import align_template_manifest

        (self.tmpdir / "modele_commercial.docx").write_bytes(b"docx-test")
        with override_settings(CV_TEMPLATE_LIBRARY_DIR=self.tmpdir):
            result = align_template_manifest()

        manifest = json.loads((self.tmpdir / "templates.json").read_text())
        self.assertEqual(result["templates_count"], 1)
        self.assertEqual(result["added"], ["modele_commercial.docx"])
        self.assertEqual(manifest["templates"][0]["filename"], "modele_commercial.docx")
        self.assertEqual(manifest["templates"][0]["name"], "Modele Commercial")

    def test_sync_endpoint_requires_admin(self):
        from django.contrib.auth.models import User
        from rest_framework.test import APIClient

        user = User.objects.create_user(username="normal", password="password123")
        admin = User.objects.create_user(username="admin", password="password123", is_staff=True)
        client = APIClient()

        with override_settings(CV_TEMPLATE_LIBRARY_DIR=self.tmpdir):
            client.force_authenticate(user=user)
            response = client.post("/api/templates/sync-library/")
            self.assertEqual(response.status_code, 403)

            (self.tmpdir / "modele_admin.docx").write_bytes(b"docx-test")
            client.force_authenticate(user=admin)
            response = client.post("/api/templates/sync-library/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["added"], ["modele_admin.docx"])


class PublicTemplateListTest(TestCase):
    def test_public_list_exposes_active_templates(self):
        from rest_framework.test import APIClient

        active = CVTemplate.objects.create(name="Modele actif", slug="modele-actif", category="modern", is_active=True)
        inactive = CVTemplate.objects.create(name="Modele cache", slug="modele-cache", category="modern", is_active=False)

        response = APIClient().get("/api/templates/")

        self.assertEqual(response.status_code, 200)
        slugs = {item["slug"] for item in response.data}
        self.assertIn(active.slug, slugs)
        self.assertNotIn(inactive.slug, slugs)
