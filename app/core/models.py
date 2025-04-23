"""
Database models.
"""
import uuid
import os
import qrcode
from io import BytesIO
from django.core.files import File
from django.conf import settings
from django.db import models
# from django.contrib.auth.models import User
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
    Group,
    Permission,
)
from django.utils import timezone
from rest_framework import serializers
from datetime import datetime
from django.core.exceptions import ValidationError

def generate_student_code():
    return f"SV{uuid.uuid4().hex[:6].upper()}"

def generate_teacher_code():
    return f"GV{uuid.uuid4().hex[:6].upper()}"

def generate_class_code():
    return f"C{uuid.uuid4().hex[:6].upper()}"

def generate_classroom_code():
    return f"CR{uuid.uuid4().hex[:6].upper()}"

def generate_object_code():
    return f"O{uuid.uuid4().hex[:6].upper()}"

class UserManager(BaseUserManager):
    """Manager for users."""

    def create_user(self, email, password=None, **extra_fields):
        """Create, save and return a new user."""
        if not email:
            raise ValueError('User must have an email address.')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """Create, save and return a new superuser."""
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

def validate_avatar_file(value):
    """
    Kiểm tra kích thước và định dạng của avatar
    - Kích thước tối đa: 2MB
    - Định dạng: jpg, jpeg, png, gif
    """
    # Kích thước tối đa (2MB)
    max_size = 2 * 1024 * 1024  # 2MB in bytes
    
    if value.size > max_size:
        raise ValidationError(f"Kích thước file không được vượt quá 2MB. File hiện tại: {value.size / 1024 / 1024:.2f}MB")
    
    # Kiểm tra định dạng file
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    
    if ext not in valid_extensions:
        raise ValidationError(f"Chỉ hỗ trợ định dạng {', '.join(valid_extensions)}")
    
    return value

class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model."""
    app_label = 'core'
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Số điện thoại")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Địa chỉ")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Ngày sinh")
    GENDER_CHOICES = [
        ('M', 'Nam'),
        ('F', 'Nữ'),
        ('O', 'Khác'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True, verbose_name="Giới tính")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Ảnh đại diện", validators=[validate_avatar_file])
    bio = models.TextField(blank=True, null=True, verbose_name="Giới thiệu")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tham gia")

    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return f"{self.name} ({self.email})" if self.name else self.email
        
    def get_full_name(self):
        return self.name
        
    def get_short_name(self):
        # Lấy tên ngắn (thường là tên sau cùng)
        name_parts = self.name.split() if self.name else []
        return name_parts[-1] if name_parts else self.email

# models.py
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_code = models.CharField(max_length=100, unique=True, default=generate_student_code)

    def __str__(self):
        return self.user.email

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    teacher_code = models.CharField(max_length=100, unique=True, default=generate_teacher_code)
    teaching_classes = models.ManyToManyField('Class', related_name='teaching_teachers')

    def __str__(self):
        return self.user.email

class Class(models.Model):
    class_code = models.CharField(max_length=100, unique=True, default=generate_class_code)
    class_name = models.CharField(max_length=100)
    students = models.ManyToManyField(Student, related_name='student_classes')
    teachers = models.ManyToManyField(Teacher, related_name='teacher_classes')

    def __str__(self):
        return f"{self.class_code} - {self.class_name}"


class Classroom(models.Model):
    classroom_code = models.CharField(max_length=100, unique=True, default=generate_classroom_code)
    class_name = models.CharField(max_length=20)
    latitude = models.FloatField(null=True, blank=True, help_text="Vĩ độ của phòng học")
    longitude = models.FloatField(null=True, blank=True, help_text="Kinh độ của phòng học")

    def __str__(self):
        return f"{self.class_name} ({self.classroom_code})"
    
class Object(models.Model):
    object_code = models.CharField(max_length=100, unique=True, default=generate_object_code)
    object_name = models.CharField(max_length=30)

    def __str__(self):
        return f"{self.object_name} ({self.object_code})"

def generate_qr_code_path(instance, filename):
    # Tạo đường dẫn lưu trữ QR code theo cấu trúc: qr_codes/YYYY/MM/DD/schedule_id.png
    date = instance.start_time.date()
    return f'qr_codes/{date.year}/{date.month}/{date.day}/{instance.id}.png'

class Weekday(models.Model):
    DAY_CHOICES = [
        ('MON', 'Thứ 2'),
        ('TUE', 'Thứ 3'),
        ('WED', 'Thứ 4'),
        ('THU', 'Thứ 5'),
        ('FRI', 'Thứ 6'),
        ('SAT', 'Thứ 7'),
        ('SUN', 'Chủ nhật'),
    ]
    
    day = models.CharField(max_length=3, choices=DAY_CHOICES, unique=True)
    
    def __str__(self):
        return dict(self.DAY_CHOICES)[self.day]

class Schedule(models.Model):
    LESSON_CHOICES = [
        (1, 'Tiết 1 (07:00 - 07:45)'),
        (2, 'Tiết 2 (07:50 - 08:35)'),
        (3, 'Tiết 3 (08:40 - 09:25)'),
        (4, 'Tiết 4 (09:30 - 10:15)'),
        (5, 'Tiết 5 (10:20 - 11:05)'),
        (6, 'Tiết 6 (12:45 - 13:30)'),
        (7, 'Tiết 7 (13:35 - 14:20)'),
        (8, 'Tiết 8 (14:25 - 15:10)'),
        (9, 'Tiết 9 (15:15 - 16:00)'),
        (10, 'Tiết 10 (16:05 - 16:50)'),
        (11, 'Tiết 11 (16:55 - 17:40)'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    course_name = models.ForeignKey(Object, on_delete=models.CASCADE)
    room = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE)
    lesson_start = models.PositiveSmallIntegerField(choices=LESSON_CHOICES, verbose_name="Tiết bắt đầu", default=1)
    lesson_count = models.PositiveSmallIntegerField(default=1, verbose_name="Số tiết")
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    weekdays = models.ManyToManyField(Weekday)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=False)
    qr_code = models.ImageField(upload_to=generate_qr_code_path, blank=True, null=True)
    qr_code_data = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.course_name} by {self.teacher.user.name}"

    def calculate_time(self, date, lesson_number):
        """Tính thời gian bắt đầu và kết thúc của một tiết học"""
        lesson_times = {
            1: {'start': (7, 0), 'end': (7, 45)},
            2: {'start': (7, 50), 'end': (8, 35)},
            3: {'start': (8, 40), 'end': (9, 25)},
            4: {'start': (9, 30), 'end': (10, 15)},
            5: {'start': (10, 20), 'end': (11, 5)},
            6: {'start': (12, 45), 'end': (13, 30)},
            7: {'start': (13, 35), 'end': (14, 20)},
            8: {'start': (14, 25), 'end': (15, 10)},
            9: {'start': (15, 15), 'end': (16, 0)},
            10: {'start': (16, 5), 'end': (16, 50)},
            11: {'start': (16, 55), 'end': (17, 40)},
        }
        
        if lesson_number not in lesson_times:
            raise ValueError(f"Số tiết {lesson_number} không hợp lệ")
            
        lesson_time = lesson_times[lesson_number]
        start_hour, start_minute = lesson_time['start']
        end_hour, end_minute = lesson_time['end']
        
        start_datetime = timezone.make_aware(datetime(
            date.year, date.month, date.day, 
            start_hour, start_minute
        ))
        
        end_datetime = timezone.make_aware(datetime(
            date.year, date.month, date.day, 
            end_hour, end_minute
        ))
        
        return start_datetime, end_datetime

    def calculate_times(self):
        """Tính thời gian bắt đầu và kết thúc dựa vào tiết bắt đầu và số tiết"""
        if not self.start_date:
            return None, None
            
        # Tính thời gian bắt đầu (tiết đầu tiên)
        start_datetime, _ = self.calculate_time(self.start_date, self.lesson_start)
        
        # Tính thời gian kết thúc (tiết cuối cùng)
        end_lesson = self.lesson_start + self.lesson_count - 1
        if end_lesson > 11:
            end_lesson = 11  # Giới hạn ở tiết 11
            
        _, end_datetime = self.calculate_time(self.start_date, end_lesson)
        
        return start_datetime, end_datetime

    def update_active_status(self):
        today = timezone.now().date()
        self.is_active = self.start_date <= today <= self.end_date

    def save(self, *args, **kwargs):
        # Tính thời gian bắt đầu và kết thúc dựa trên tiết học
        self.start_time, self.end_time = self.calculate_times()
        
        # Cập nhật trạng thái trước khi lưu
        today = timezone.now().date()
        self.is_active = self.start_date <= today <= self.end_date
        
        super().save(*args, **kwargs)

    def generate_qr_code(self):
        if not self.qr_code_data:
            # Tạo dữ liệu cho QR code
            data = {
                'schedule_id': self.id,
                'course_name': self.course_name.object_name,
                'teacher': self.teacher.user.name,
                'class_name': self.class_name.class_name,
                'room': self.room.classroom_code,
                'lesson_start': self.lesson_start,
                'lesson_count': self.lesson_count,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None
            }
            self.qr_code_data = str(data)
            self.save()

        # Tạo QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_code_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        # Lưu QR code vào file
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        # Lưu file vào trường qr_code
        self.qr_code.save(f'{self.id}.png', File(buffer), save=True)
        return self.qr_code.url

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_present = models.BooleanField(default=False)
    is_late = models.BooleanField(default=False)  # Đánh dấu điểm danh trễ
    minutes_late = models.PositiveIntegerField(null=True, blank=True)  # Số phút trễ
    latitude = models.FloatField(null=True, blank=True)  # Vị trí điểm danh
    longitude = models.FloatField(null=True, blank=True)  # Vị trí điểm danh
    device_info = models.TextField(blank=True, null=True)  # Thông tin thiết bị
    is_in_location = models.BooleanField(default=True)  # Có đang ở đúng vị trí phòng học hay không

    def __str__(self):
        status = "Vắng mặt"
        if self.is_present:
            status = f"Trễ {self.minutes_late} phút" if self.is_late else "Có mặt"
        return f"{self.student.user} - {self.schedule.course_name} - {status}"

    class Meta:
        unique_together = ('student', 'schedule')  # Đảm bảo mỗi sinh viên chỉ có một bản ghi điểm danh cho mỗi lịch

class QRCode(models.Model):
    schedule = models.OneToOneField(Schedule, on_delete=models.CASCADE)
    qr_code_data = models.TextField()

    def __str__(self):
        return f"QR Code for {self.schedule.course_name}"

class ScheduleSerializer(serializers.ModelSerializer):
    course_name = serializers.StringRelatedField()
    teacher = serializers.StringRelatedField()
    room = serializers.StringRelatedField()
    class_name = serializers.StringRelatedField()

    class Meta:
        model = Schedule
        fields = ['id', 'course_name', 'teacher', 'room', 'class_name', 'start_time', 'end_time']

class AttendanceSerializer(serializers.ModelSerializer):
    schedule = ScheduleSerializer(read_only=True)
    schedule_id = serializers.PrimaryKeyRelatedField(
        queryset=Schedule.objects.all(),
        source='schedule',
        write_only=True
    )
    student_name = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    attendance_status = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            'id', 'schedule', 'schedule_id', 'student_name', 
            'timestamp', 'is_present', 'is_late', 'minutes_late',
            'latitude', 'longitude', 'location', 'attendance_status',
            'device_info'
        ]
        read_only_fields = ['id', 'timestamp', 'is_present', 'is_late', 'minutes_late']

    def get_student_name(self, obj):
        return obj.student.user.name if obj.student and obj.student.user else None

    def get_location(self, obj):
        if obj.latitude and obj.longitude:
            return f"{obj.latitude}, {obj.longitude}"
        return None

    def get_attendance_status(self, obj):
        if not obj.is_present:
            return "Vắng mặt"
        elif obj.is_late:
            return f"Trễ {obj.minutes_late} phút"
        else:
            return "Có mặt"