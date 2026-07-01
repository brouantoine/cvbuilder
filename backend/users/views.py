"""
Vues d'authentification : inscription et login JWT.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import RegisterSerializer, UserSerializer


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Crée un compte et retourne les tokens JWT (access, refresh).
    """
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Essai gratuit de 7 jours offert dès l'inscription.
        trial_days = 7
        try:
            from django.conf import settings
            from cvs.services.access import grant_trial

            grant_trial(user)
            trial_days = settings.CV_TRIAL_DAYS
        except Exception:
            pass

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "trial_days": trial_days,
                "message": f"Bienvenue 🎉 Tu as un essai gratuit de {trial_days} jours.",
            },
            status=status.HTTP_201_CREATED,
        )


# Login = vue SimpleJWT standard (POST username + password → access + refresh)
# On réutilise TokenObtainPairView ; l'URL sera /api/auth/login/
LoginView = TokenObtainPairView


class MeView(APIView):
    """
    GET /api/auth/me/
    Retourne le profil de l'utilisateur connecté et valide le token JWT.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
