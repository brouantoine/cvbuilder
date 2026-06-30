from django.urls import path

from .views import (
    CVAIImproveView,
    CVContextUploadView,
    CVDetailView,
    CVDownloadView,
    CVDuplicateView,
    CVGenerateView,
    CVListCreateView,
    CVCorrectView,
    CVPlansView,
    CVPreviewView,
    CVProfileView,
    CVRewriteView,
    PaymentInitializeView,
    PaymentVerifyView,
    PaystackWebhookView,
)

urlpatterns = [
    path("", CVListCreateView.as_view(), name="cv-list-create"),
    path("preview/", CVPreviewView.as_view(), name="cv-preview"),
    path("rewrite/", CVRewriteView.as_view(), name="cv-rewrite"),
    path("profile/", CVProfileView.as_view(), name="cv-profile"),
    path("correct/", CVCorrectView.as_view(), name="cv-correct"),
    path("plans/", CVPlansView.as_view(), name="cv-plans"),
    path("payments/initialize/", PaymentInitializeView.as_view(), name="payment-initialize"),
    path("payments/verify/", PaymentVerifyView.as_view(), name="payment-verify"),
    path("payments/paystack-webhook/", PaystackWebhookView.as_view(), name="paystack-webhook"),
    path("<int:pk>/", CVDetailView.as_view(), name="cv-detail"),
    path("<int:pk>/context/", CVContextUploadView.as_view(), name="cv-context"),
    path("<int:pk>/ai/improve/", CVAIImproveView.as_view(), name="cv-ai-improve"),
    path("<int:pk>/generate/", CVGenerateView.as_view(), name="cv-generate"),
    path("<int:pk>/duplicate/", CVDuplicateView.as_view(), name="cv-duplicate"),
    path("<int:pk>/download/", CVDownloadView.as_view(), name="cv-download"),
]
