from rest_framework import viewsets, status, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


from .models import Schedule, Attendance, Class, Student, Teacher, User, Classroom
from .serializers import (
    ScheduleSerializer, StudentScheduleSerializer, UserSerializer,
    StudentSerializer, TeacherSerializer, ClassroomSerializer,
    ChangePasswordSerializer, AvatarSerializer
)
from django.shortcuts import render
from rest_framework.views import APIView
from django.db.models import Count, Avg, Sum, F, Q, Case, When, IntegerField, Value
from django.utils import timezone
from datetime import timedelta
import json
from rest_framework.parsers import MultiPartParser, FormParser

class ClassViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint cho xem thông tin lớp học
    Chỉ cung cấp chức năng đọc (không thêm/sửa/xóa)
    """
    queryset = Class.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        # Sử dụng serializer mặc định của DRF
        from rest_framework import serializers

        class ClassSerializer(serializers.ModelSerializer):
            students_count = serializers.SerializerMethodField()
            teachers_count = serializers.SerializerMethodField()

            class Meta:
                model = Class
                fields = ['id', 'class_code', 'class_name', 'students_count', 'teachers_count']

            def get_students_count(self, obj):
                return obj.students.count()

            def get_teachers_count(self, obj):
                return obj.teachers.count()

        return ClassSerializer

    def get_queryset(self):
        """
        Lọc dữ liệu dựa trên vai trò người dùng:
        - Sinh viên: chỉ thấy các lớp mình tham gia
        - Giáo viên: chỉ thấy các lớp mình dạy
        - Admin: thấy tất cả
        """
        user = self.request.user

        if user.is_superuser:
            return Class.objects.all()

        # Kiểm tra nếu là sinh viên
        try:
            student = user.student
            return Class.objects.filter(students=student)
        except:
            pass

        # Kiểm tra nếu là giáo viên
        try:
            teacher = user.teacher
            return Class.objects.filter(teachers=teacher)
        except:
            return Class.objects.none()

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]


    def get_serializer_class(self):
        if self.action in ['student_schedule', 'teacher_schedule']:
            return ScheduleSerializer  # Có thể dùng serializer riêng nếu cần
        return ScheduleSerializer

    @action(detail=False, methods=['get'])
    def student_schedule(self, request):
        student = request.user.student
        schedules = Schedule.objects.filter(class_name__students=student)
        schedules = schedules.order_by('start_time')
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def teacher_schedule(self, request):
        try:
            teacher = request.user.teacher
        except:
            return Response(
                {"error": "Bạn không phải là giáo viên."},
                status=status.HTTP_403_FORBIDDEN
            )

        schedules = Schedule.objects.filter(teacher=teacher).order_by('start_time')
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data)


    @action(detail=True, methods=['post'])
    def mark_attendance(self, request, pk=None):
        schedule = self.get_object()
        student = request.user.student

        if student not in schedule.class_name.students.all():
            return Response(
                {"error": "Bạn không phải là sinh viên của lớp này."},
                status=status.HTTP_403_FORBIDDEN
            )

        attendance, created = Attendance.objects.get_or_create(
            student=student,
            schedule=schedule,
            defaults={'is_present': True}
        )

        if not created:
            attendance.is_present = True
            attendance.save()

        return Response({"status": "success", "message": "Điểm danh thành công."})

def index_view(request):
    """
    Hiển thị trang chủ với các tùy chọn đăng nhập và thông tin người dùng (nếu đã đăng nhập)
    """
    context = {}

    # Nếu người dùng đã đăng nhập, thêm thông tin vào context
    if request.user.is_authenticated:
        # Thêm thông tin cơ bản từ User model
        user_data = {
            'id': request.user.id,
            'email': request.user.email,
            'name': request.user.name,
        }

        # Xác định vai trò người dùng
        if request.user.is_superuser:
            user_data['role'] = 'admin'
        else:
            # Kiểm tra nếu là sinh viên
            try:
                student = request.user.student
                user_data['role'] = 'student'
                user_data['student_info'] = {
                    'student_code': student.student_code,
                    'classes_count': student.student_classes.count()
                }
            except Exception:
                # Kiểm tra nếu là giáo viên
                try:
                    teacher = request.user.teacher
                    user_data['role'] = 'teacher'
                    user_data['teacher_info'] = {
                        'teacher_code': teacher.teacher_code,
                        'classes_count': teacher.teacher_classes.count()
                    }
                except Exception:
                    user_data['role'] = 'user'

        context['user_data'] = user_data

    return render(request, 'index.html', context)

class StatisticsAPIView(APIView):
    """
    API thống kê dữ liệu tùy theo vai trò người dùng
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Phân loại người dùng để trả về thống kê phù hợp
        if user.is_superuser:
            return self.get_admin_statistics()

        try:
            # Thống kê dành cho sinh viên
            student = user.student
            return self.get_student_statistics(student)
        except:
            pass

        try:
            # Thống kê dành cho giáo viên
            teacher = user.teacher
            return self.get_teacher_statistics(teacher)
        except:
            return Response({"error": "Không thể xác định vai trò của bạn"}, status=status.HTTP_403_FORBIDDEN)

    def get_admin_statistics(self):
        """Thống kê dành cho quản trị viên"""
        today = timezone.now().date()

        # Thống kê tổng quan
        total_students = Student.objects.count()
        total_teachers = Teacher.objects.count()
        total_classes = Class.objects.count()
        active_schedules = Schedule.objects.filter(is_active=True).count()

        # Thống kê điểm danh trong 30 ngày gần đây
        thirty_days_ago = today - timedelta(days=30)
        recent_attendance = Attendance.objects.filter(timestamp__date__gte=thirty_days_ago)
        total_attendance = recent_attendance.count()
        present_count = recent_attendance.filter(is_present=True).count()
        absent_count = total_attendance - present_count
        late_count = recent_attendance.filter(is_late=True).count()

        # Tỷ lệ điểm danh
        attendance_rate = 0
        if total_attendance > 0:
            attendance_rate = (present_count / total_attendance) * 100

        # Biểu đồ điểm danh theo ngày
        attendance_by_day = {}
        for i in range(30):
            day = today - timedelta(days=i)
            day_attendance = recent_attendance.filter(timestamp__date=day)
            attendance_by_day[day.strftime('%Y-%m-%d')] = {
                'total': day_attendance.count(),
                'present': day_attendance.filter(is_present=True).count(),
                'absent': day_attendance.filter(is_present=False).count(),
                'late': day_attendance.filter(is_late=True).count()
            }

        return Response({
            'role': 'admin',
            'overview': {
                'total_students': total_students,
                'total_teachers': total_teachers,
                'total_classes': total_classes,
                'active_schedules': active_schedules
            },
            'attendance': {
                'total': total_attendance,
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'attendance_rate': attendance_rate
            },
            'attendance_by_day': attendance_by_day,
        })

    def get_teacher_statistics(self, teacher):
        """Thống kê dành cho giáo viên"""
        today = timezone.now().date()

        # Lấy danh sách lớp giáo viên đang dạy
        classes = Class.objects.filter(teachers=teacher)

        # Lấy danh sách lịch dạy
        schedules = Schedule.objects.filter(teacher=teacher)
        active_schedules = schedules.filter(is_active=True)

        # Thống kê học sinh và tỷ lệ điểm danh
        students_count = 0
        classes_data = []

        for class_obj in classes:
            class_students = class_obj.students.count()
            students_count += class_students

            # Tính tỷ lệ điểm danh cho từng lớp
            class_schedules = schedules.filter(class_name=class_obj)
            class_attendance = Attendance.objects.filter(schedule__in=class_schedules)
            total_class_attendance = class_attendance.count()
            present_count = class_attendance.filter(is_present=True).count()
            attendance_rate = 0
            if total_class_attendance > 0:
                attendance_rate = (present_count / total_class_attendance) * 100

            classes_data.append({
                'id': class_obj.id,
                'name': class_obj.class_name,
                'code': class_obj.class_code,
                'students_count': class_students,
                'attendance_rate': attendance_rate
            })

        # Thống kê điểm danh 30 ngày gần đây
        thirty_days_ago = today - timedelta(days=30)
        recent_attendance = Attendance.objects.filter(
            schedule__in=schedules,
            timestamp__date__gte=thirty_days_ago
        )

        # Tỷ lệ điểm danh theo ngày
        attendance_by_day = {}
        for i in range(30):
            day = today - timedelta(days=i)
            day_attendance = recent_attendance.filter(timestamp__date=day)
            total = day_attendance.count()
            present = day_attendance.filter(is_present=True).count()

            if total > 0:
                rate = (present / total) * 100
            else:
                rate = 0

            attendance_by_day[day.strftime('%Y-%m-%d')] = {
                'total': total,
                'present': present,
                'absent': total - present,
                'rate': rate
            }

        # Lịch dạy sắp tới trong 7 ngày
        next_week = today + timedelta(days=7)
        upcoming_schedules = active_schedules.filter(
            start_date__gte=today,
            start_date__lte=next_week
        ).order_by('start_date')

        upcoming_data = []
        for schedule in upcoming_schedules:
            upcoming_data.append({
                'id': schedule.id,
                'course': schedule.course_name.object_name,
                'class_name': schedule.class_name.class_name,
                'date': schedule.start_date.strftime('%Y-%m-%d'),
                'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                'room': schedule.room.class_name
            })

        return Response({
            'role': 'teacher',
            'name': teacher.user.name,
            'code': teacher.teacher_code,
            'overview': {
                'classes_count': classes.count(),
                'students_count': students_count,
                'active_schedules': active_schedules.count()
            },
            'classes': classes_data,
            'attendance_by_day': attendance_by_day,
            'upcoming_schedules': upcoming_data
        })

    def get_student_statistics(self, student):
        """Thống kê dành cho sinh viên"""
        today = timezone.now().date()

        # Lấy các lớp học sinh đang học
        classes = Class.objects.filter(students=student)

        # Lấy tất cả lịch học
        schedules = Schedule.objects.filter(class_name__in=classes)
        active_schedules = schedules.filter(is_active=True)

        # Thống kê điểm danh
        all_attendance = Attendance.objects.filter(student=student)
        total_attendance = all_attendance.count()
        present_count = all_attendance.filter(is_present=True).count()
        absent_count = total_attendance - present_count
        late_count = all_attendance.filter(is_late=True).count()

        # Tỷ lệ điểm danh
        attendance_rate = 0
        if total_attendance > 0:
            attendance_rate = (present_count / total_attendance) * 100

        # Thống kê điểm danh theo môn học
        courses_attendance = {}
        for schedule in schedules:
            course_name = schedule.course_name.object_name

            if course_name not in courses_attendance:
                courses_attendance[course_name] = {
                    'total': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0
                }

            attendance = all_attendance.filter(schedule=schedule)
            courses_attendance[course_name]['total'] += attendance.count()
            courses_attendance[course_name]['present'] += attendance.filter(is_present=True).count()
            courses_attendance[course_name]['absent'] += attendance.filter(is_present=False).count()
            courses_attendance[course_name]['late'] += attendance.filter(is_late=True).count()

        # Lịch học sắp tới trong 7 ngày
        next_week = today + timedelta(days=7)
        upcoming_schedules = active_schedules.filter(
            start_date__gte=today,
            start_date__lte=next_week
        ).order_by('start_date')

        upcoming_data = []
        for schedule in upcoming_schedules:
            # Kiểm tra xem đã điểm danh chưa
            has_attendance = Attendance.objects.filter(
                student=student,
                schedule=schedule,
                is_present=True
            ).exists()

            upcoming_data.append({
                'id': schedule.id,
                'course': schedule.course_name.object_name,
                'date': schedule.start_date.strftime('%Y-%m-%d'),
                'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                'room': schedule.room.class_name,
                'teacher': schedule.teacher.user.name,
                'has_attendance': has_attendance
            })

        return Response({
            'role': 'student',
            'name': student.user.name,
            'code': student.student_code,
            'overview': {
                'classes_count': classes.count(),
                'total_schedules': schedules.count(),
                'active_schedules': active_schedules.count(),
            },
            'attendance': {
                'total': total_attendance,
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'attendance_rate': attendance_rate
            },
            'courses_attendance': courses_attendance,
            'upcoming_schedules': upcoming_data
        })

# Thêm UserViewSet cho quản lý thông tin người dùng
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint cho người dùng quản lý thông tin cá nhân của mình
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # Để xử lý multipart/form-data

    def get_queryset(self):
        """
        Người dùng chỉ có thể xem thông tin của chính mình
        Admin có thể xem tất cả
        """
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Trả về thông tin chi tiết của người dùng hiện tại"""
        serializer = self.get_serializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'], url_path='update-profile')
    def update_profile(self, request):
        """Cập nhật thông tin cá nhân của người dùng"""
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='upload-avatar')
    def upload_avatar(self, request):
        """Tải lên và cập nhật avatar cho người dùng"""
        user = request.user

        # Sử dụng serializer để xác thực dữ liệu đầu vào
        serializer = AvatarSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Xóa avatar cũ nếu có
        if user.avatar:
            user.avatar.delete(save=False)

        # Cập nhật avatar mới
        user.avatar = serializer.validated_data['avatar']
        user.save()

        # Trả về thông tin người dùng đã cập nhật
        response_serializer = self.get_serializer(user, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='remove-avatar')
    def remove_avatar(self, request):
        """Xóa avatar của người dùng"""
        user = request.user

        if not user.avatar:
            return Response(
                {"detail": "Người dùng không có avatar."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Xóa avatar
        user.avatar.delete()
        user.avatar = None
        user.save()

        return Response(
            {"detail": "Avatar đã được xóa thành công."},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """Thay đổi mật khẩu"""
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            # Kiểm tra mật khẩu cũ
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({"old_password": ["Mật khẩu hiện tại không đúng."]},
                                status=status.HTTP_400_BAD_REQUEST)

            # Đổi mật khẩu
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"detail": "Mật khẩu đã được thay đổi thành công."},
                           status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Thêm StudentViewSet
class StudentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint cho xem thông tin sinh viên
    """
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Sinh viên chỉ có thể xem thông tin của chính mình
        Giáo viên có thể xem thông tin của sinh viên trong lớp mình dạy
        Admin có thể xem tất cả
        """
        user = self.request.user

        if user.is_superuser:
            return Student.objects.all()

        # Nếu là giáo viên, xem thông tin sinh viên trong lớp dạy
        try:
            teacher = user.teacher
            teacher_classes = teacher.teacher_classes.all()
            student_ids = []
            for teacher_class in teacher_classes:
                student_ids.extend(teacher_class.students.values_list('id', flat=True))
            return Student.objects.filter(id__in=student_ids)
        except:
            pass

        # Nếu là sinh viên, chỉ xem thông tin của mình
        try:
            student = user.student
            return Student.objects.filter(id=student.id)
        except:
            return Student.objects.none()

# Thêm TeacherViewSet
class TeacherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint cho xem thông tin giáo viên
    """
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Giáo viên chỉ có thể xem thông tin của chính mình
        Sinh viên có thể xem thông tin của giáo viên dạy mình
        Admin có thể xem tất cả
        """
        user = self.request.user

        if user.is_superuser:
            return Teacher.objects.all()

        # Nếu là giáo viên, xem thông tin của mình
        try:
            teacher = user.teacher
            return Teacher.objects.filter(id=teacher.id)
        except:
            pass

        # Nếu là sinh viên, xem thông tin giáo viên dạy mình
        try:
            student = user.student
            student_classes = student.student_classes.all()
            teacher_ids = []
            for student_class in student_classes:
                teacher_ids.extend(student_class.teachers.values_list('id', flat=True))
            return Teacher.objects.filter(id__in=teacher_ids)
        except:
            return Teacher.objects.none()

# Thêm ClassroomViewSet
class ClassroomViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint cho xem thông tin phòng học
    """
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [permissions.IsAuthenticated]