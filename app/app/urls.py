"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from core.qr import qr_router
from core.urls import router as core_router
from core.admin import student_admin_site
from core.views import index_view
from django.views.generic import TemplateView
from user.views import UserInfoView

urlpatterns = [
    # Đường dẫn root cho trang chủ
    path('', index_view, name='index'),
    # Đường dẫn cho trang thông tin
    path('index/html/', TemplateView.as_view(template_name='index/html.html'), name='index-html'),
    
    path('admin/', admin.site.urls),
    path('student/', student_admin_site.urls, name='student-admin'),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='api-schema'),
        name='api-docs'
    ),
    path('api/attendance/', include('attendance.urls')),
    path('api/qr/', include(qr_router.urls)),
    path('api/core/', include(core_router.urls)),
    path('api/school/', include('school_management.urls')),
    path('api/users/', include('user.urls')),
    path('api/user-info/', UserInfoView.as_view(), name='user-info-direct'),
]

# Thêm cấu hình để phục vụ file media trong môi trường phát triển
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
