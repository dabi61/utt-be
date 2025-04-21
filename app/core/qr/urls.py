from rest_framework.routers import DefaultRouter
from .views import ScheduleQRViewSet

router = DefaultRouter()
router.register(r'schedules', ScheduleQRViewSet, basename='schedule-qr') 