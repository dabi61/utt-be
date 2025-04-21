from celery import shared_task
from django.utils import timezone
from .models import Schedule
from datetime import timedelta

@shared_task
def generate_qr_codes_for_upcoming_classes():
    # Lấy thời gian hiện tại
    now = timezone.now()
    
    # Tìm các lớp học sắp diễn ra trong vòng 30 phút tới
    upcoming_classes = Schedule.objects.filter(
        start_time__gte=now,
        start_time__lte=now + timedelta(minutes=30),
        qr_code__isnull=True  # Chỉ tạo QR code cho những lớp chưa có
    )
    
    for schedule in upcoming_classes:
        schedule.generate_qr_code()
        print(f"Generated QR code for schedule {schedule.id}") 