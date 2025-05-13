from rest_framework import serializers
from .models import User, Student, Teacher, Class, Classroom, Object, Schedule, Attendance, Weekday
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

class UserSerializer(serializers.ModelSerializer):
    """Serializer cho model User với đầy đủ thông tin cá nhân"""
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'phone_number', 'address',
            'date_of_birth', 'gender', 'avatar', 'avatar_url', 'bio',
            'is_active', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']

    def get_avatar_url(self, obj):
        if obj.avatar and hasattr(obj.avatar, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer cho việc tạo User mới"""
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = [
            'email', 'name', 'password', 'confirm_password',
            'phone_number', 'address', 'date_of_birth', 'gender'
        ]

    def validate(self, attrs):
        # Xác thực mật khẩu
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'Mật khẩu không khớp'})

        try:
            validate_password(attrs.get('password'))
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})

        return attrs

    def create(self, validated_data):
        # Loại bỏ confirm_password khỏi dữ liệu
        validated_data.pop('confirm_password', None)

        # Tạo user mới
        user = User.objects.create_user(
            email=validated_data.pop('email'),
            password=validated_data.pop('password'),
            **validated_data
        )

        return user

class ChangePasswordSerializer(serializers.Serializer):
    """Serializer cho việc thay đổi mật khẩu"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value


class StudentSerializer(serializers.ModelSerializer):
    """Serializer cho Student"""
    user = UserSerializer(read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'user', 'student_code']
        read_only_fields = ['id', 'student_code']


class TeacherSerializer(serializers.ModelSerializer):
    """Serializer cho Teacher"""
    user = UserSerializer(read_only=True)

    class Meta:
        model = Teacher
        fields = ['id', 'user', 'teacher_code']
        read_only_fields = ['id', 'teacher_code']


class ClassSerializer(serializers.ModelSerializer):
    """Serializer cho Class"""
    student_count = serializers.SerializerMethodField()
    teacher_count = serializers.SerializerMethodField()

    class Meta:
        model = Class
        fields = ['id', 'class_code', 'class_name', 'student_count', 'teacher_count']
        read_only_fields = ['id', 'class_code']

    def get_student_count(self, obj):
        return obj.students.count()

    def get_teacher_count(self, obj):
        return obj.teachers.count()


class ClassroomSerializer(serializers.ModelSerializer):
    """Serializer cho Classroom"""
    class Meta:
        model = Classroom
        fields = ['id', 'classroom_code', 'class_name', 'latitude', 'longitude']
        read_only_fields = ['id', 'classroom_code']


class ObjectSerializer(serializers.ModelSerializer):
    """Serializer cho Object"""
    class Meta:
        model = Object
        fields = ['id', 'object_code', 'object_name']
        read_only_fields = ['id', 'object_code']


class WeekdaySerializer(serializers.ModelSerializer):
    """Serializer cho Weekday"""
    day_display = serializers.SerializerMethodField()

    class Meta:
        model = Weekday
        fields = ['id', 'day', 'day_display']

    def get_day_display(self, obj):
        return obj.__str__()


class ScheduleSerializer(serializers.ModelSerializer):
    """Serializer cho Schedule"""
    teacher_name = serializers.CharField(source='teacher.user.name', read_only=True)
    course_name = serializers.CharField(source='course_name.object_name', read_only=True)
    room_name = serializers.CharField(source='room.class_name', read_only=True)
    class_name = serializers.CharField(source='class_name.class_name', read_only=True)
    weekdays = WeekdaySerializer(many=True, read_only=True)

    class Meta:
        model = Schedule
        fields = [
            'id', 'teacher', 'teacher_name', 'course_name', 'room_name', 'class_name',
            'lesson_start', 'lesson_count', 'start_time', 'end_time',
            'weekdays', 'start_date', 'end_date'
        ]
        read_only_fields = ['id', 'start_time', 'end_time', 'is_active']


class AttendanceSerializer(serializers.ModelSerializer):
    """Serializer cho Attendance"""
    student_name = serializers.CharField(source='student.user.name', read_only=True)
    schedule_info = ScheduleSerializer(source='schedule', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id', 'student', 'student_name', 'schedule', 'schedule_info',
            'timestamp', 'is_present', 'is_late', 'minutes_late',
            'latitude', 'longitude', 'device_info', 'is_in_location'
        ]
        read_only_fields = ['id', 'timestamp']

class StudentScheduleSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.user.name', read_only=True)
    course_name = serializers.CharField(source='course_name.object_name', read_only=True)
    room_name = serializers.CharField(source='room.classroom_code', read_only=True)
    class_name = serializers.CharField(source='class_name.class_name', read_only=True)
    is_present = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [
            'id', 'teacher_name', 'course_name', 'room_name',
            'class_name', 'start_time', 'end_time', 'is_present'
        ]

    def get_is_present(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            student = request.user.student
            attendance = Attendance.objects.filter(
                student=student,
                schedule=obj
            ).first()
            return attendance.is_present if attendance else None
        return None

class ScheduleSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.user.name', read_only=True)
    course_name = serializers.CharField(source='course_name.object_name', read_only=True)
    room_name = serializers.CharField(source='room.classroom_code', read_only=True)
    class_name = serializers.CharField(source='class_name.class_name', read_only=True)

    class Meta:
        model = Schedule
        fields = [
            'id', 'teacher', 'course_name', 'room', 'class_name',
            'lesson_start', 'lesson_count', 'start_time', 'end_time',
            'weekdays', 'start_date', 'end_date', 'is_active',
            'teacher_name', 'course_name', 'room_name', 'class_name',
        ]

    def validate(self, attrs):
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError("Thời gian kết thúc phải sau thời gian bắt đầu.")

            if start_time < timezone.now():
                raise serializers.ValidationError("Không thể tạo lịch học trong quá khứ.")

            # Kiểm tra xung đột lịch học
            conflicting_schedules = Schedule.objects.filter(
                room=attrs.get('room'),
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exclude(id=self.instance.id if self.instance else None)

            if conflicting_schedules.exists():
                raise serializers.ValidationError("Phòng học đã được sử dụng trong khoảng thời gian này.")

        return attrs

    def create(self, validated_data):
        schedule = super().create(validated_data)

        # Tạo bản ghi điểm danh cho tất cả sinh viên trong lớp
        students = schedule.class_name.students.all()
        for student in students:
            Attendance.objects.create(
                student=student,
                schedule=schedule,
                is_present=False
            )

        return schedule

class AvatarSerializer(serializers.Serializer):
    """Serializer cho việc tải lên avatar"""
    avatar = serializers.ImageField(required=True)

    def validate_avatar(self, value):
        # Kích thước tối đa (2MB)
        max_size = 2 * 1024 * 1024  # 2MB in bytes

        if value.size > max_size:
            raise serializers.ValidationError(
                f"Kích thước file không được vượt quá 2MB. File hiện tại: {value.size / 1024 / 1024:.2f}MB"
            )

        # Kiểm tra định dạng file
        import os
        ext = os.path.splitext(value.name)[1].lower()
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']

        if ext not in valid_extensions:
            raise serializers.ValidationError(
                f"Chỉ hỗ trợ định dạng {', '.join(valid_extensions)}"
            )

        return value
