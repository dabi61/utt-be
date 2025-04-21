from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClassViewSet,
    TeacherViewSet,
    StudentViewSet
)

router = DefaultRouter()
router.register(r'classes', ClassViewSet, basename='class')
router.register(r'teachers', TeacherViewSet, basename='teacher')
router.register(r'students', StudentViewSet, basename='student')

urlpatterns = [
    path('', include(router.urls)),
] 