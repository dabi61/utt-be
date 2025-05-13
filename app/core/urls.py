from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.views import (
    ClassViewSet, ScheduleViewSet, index_view, StatisticsAPIView,
    UserViewSet, StudentViewSet, TeacherViewSet, ClassroomViewSet, ScheduleDetailAPIView
)
from core.admin import student_admin_site

router = DefaultRouter()
router.register('classes', ClassViewSet)
router.register('schedules', ScheduleViewSet)
router.register('users', UserViewSet)
router.register('students', StudentViewSet)
router.register('teachers', TeacherViewSet)
router.register('classrooms', ClassroomViewSet)

# API riêng để lấy thông tin người dùng với vai trò
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    """Lấy thông tin người dùng mở rộng, bao gồm vai trò"""
    user = request.user
    avatar_url = None
    if user.avatar and hasattr(user.avatar, 'url'):
        avatar_url = request.build_absolute_uri(user.avatar.url)

    data = {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'phone_number': user.phone_number,
        'address': user.address,
        'date_of_birth': user.date_of_birth,
        'gender': user.gender,
        'avatar_url': avatar_url,
        'bio': user.bio,
    }

    # Xác định vai trò người dùng
    if user.is_superuser:
        data['role'] = 'admin'
    else:
        # Kiểm tra nếu là sinh viên
        try:
            student = user.student
            data['role'] = 'student'
            data['student_info'] = {
                'student_code': student.student_code,
                'classes_count': student.student_classes.count()
            }
        except Exception:
            # Kiểm tra nếu là giáo viên
            try:
                teacher = user.teacher
                data['role'] = 'teacher'
                data['teacher_info'] = {
                    'teacher_code': teacher.teacher_code,
                    'classes_count': teacher.teacher_classes.count()
                }
            except Exception:
                data['role'] = 'user'

    return Response(data)

# URLs cho StudentAdminSite và API endpoints
urlpatterns = [
    # URLs student admin
    path('student-admin/', student_admin_site.urls),
    # API endpoints
    path('api/', include(router.urls)),
    path('api/statistics/', StatisticsAPIView.as_view(), name='statistics'),
    path('api/user-info/', user_info, name='user-info'),  # Endpoint cho thông tin người dùng
    path('', index_view, name='index'),
]
