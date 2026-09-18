"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import re

from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from django.conf import settings

from config.admin_stats import admin_stats

urlpatterns = [
    # Admin volontairement hors du chemin par défaut /admin/ (moins de bots).
    path("moncvservices/stats.json", admin_stats, name="admin-stats"),
    path("moncvservices/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/templates/", include("templates.urls")),
    path("api/cvs/", include("cvs.urls")),
]

if settings.DEBUG or settings.SERVE_MEDIA:
    media_prefix = re.escape(settings.MEDIA_URL.lstrip("/"))
    urlpatterns += [
        re_path(rf"^{media_prefix}(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
