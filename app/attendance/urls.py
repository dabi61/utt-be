from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AttendanceViewSet

router = DefaultRouter()
router.register(r'', AttendanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('qr-attendance/', AttendanceViewSet.as_view({'post': 'qr_attendance'})),
]