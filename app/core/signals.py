# core/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from core.models import Student, Schedule
import uuid

@receiver(post_save, sender=User)
def create_student_for_user(sender, instance, created, **kwargs):
    if created and not instance.is_staff:
        # tránh tạo trùng student nếu đã có
        if not hasattr(instance, 'student'):
            Student.objects.create(
                user=instance,
                student_code=str(uuid.uuid4())[:8]  # mã ngẫu nhiên
            )

@receiver(post_save, sender=Schedule)
def update_qr_code_on_schedule_save(sender, instance, **kwargs):
    """
    Tự động cập nhật mã QR code khi Schedule được lưu
    """
    # Sử dụng một cờ để tránh đệ quy vô hạn do generate_qr_code() cũng gọi save()
    # Chi tiết: Kiểm tra xem QR code đã thay đổi hay chưa bằng cách so sánh
    # qr_code_data hiện tại và qr_code_data mới
    
    # Tạo dữ liệu cho QR code
    data = {
        'schedule_id': instance.id,
        'course_name': instance.course_name.object_name,
        'teacher': instance.teacher.user.name,
        'class_name': instance.class_name.class_name,
        'room': instance.room.classroom_code,
        'lesson_start': instance.lesson_start,
        'lesson_count': instance.lesson_count,
        'start_time': instance.start_time.isoformat() if instance.start_time else None,
        'end_time': instance.end_time.isoformat() if instance.end_time else None
    }
    
    new_qr_data = str(data)
    
    # Chỉ tạo QR code mới nếu dữ liệu đã thay đổi
    if instance.qr_code_data != new_qr_data:
        # Lưu dữ liệu QR mới và tránh gọi lại signal này
        instance.qr_code_data = new_qr_data
        
        # Ngắt kết nối signal tạm thời để tránh đệ quy
        post_save.disconnect(update_qr_code_on_schedule_save, sender=Schedule)
        
        # Tạo QR code
        instance.generate_qr_code()
        
        # Kết nối lại signal
        post_save.connect(update_qr_code_on_schedule_save, sender=Schedule)
