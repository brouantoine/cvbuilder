from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient


class MeAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="assanvo",
            email="assanvo@example.com",
            password="password123",
        )
        self.client = APIClient()

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)

    def test_me_returns_authenticated_user(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "assanvo")
        self.assertEqual(response.data["email"], "assanvo@example.com")
