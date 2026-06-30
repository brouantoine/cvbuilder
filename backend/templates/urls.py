from django.urls import path
from .views import TemplateListView, TemplateDetailView, TemplateLibrarySyncView

urlpatterns = [
    path("sync-library/", TemplateLibrarySyncView.as_view(), name="template-library-sync"),
    path("", TemplateListView.as_view(), name="template-list"),
    path("<int:pk>/", TemplateDetailView.as_view(), name="template-detail"),
]
