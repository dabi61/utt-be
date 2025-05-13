from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from core.models import Attendance, Student, Schedule
from rest_framework.permissions import IsAuthenticated
from .serializers import AttendanceSerializer, QRCodeAttendanceSerializer
from django.utils import timezone
from datetime import timedelta
import requests
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Lấy địa chỉ IP của người dùng mà không sử dụng IP giả lập"""
    print(f"AttendanceViewSet: Đang lấy IP của người dùng từ request")

    # Kiểm tra xem middleware FakeIPMiddleware đã được áp dụng chưa
    if hasattr(request, 'original_ip'):
        print(f"AttendanceViewSet: Sử dụng IP giả lập: {request.META.get('REMOTE_ADDR')}")
        print(f"AttendanceViewSet: IP gốc: {request.original_ip}")
        return request.META.get('REMOTE_ADDR')

    # Lấy IP thực từ header 'X-Forwarded-For' nếu có, nếu không lấy từ 'REMOTE_ADDR'
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    print(f"AttendanceViewSet: IP của người dùng: {ip}")
    return ip


def get_location_from_ip(ip):
    """Lấy vị trí dựa trên địa chỉ IP"""
    print(f"AttendanceViewSet: Đang lấy vị trí từ IP: {ip}")
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        if response.status_code == 200:
            data = response.json()
            print(f"AttendanceViewSet: Dữ liệu từ ipinfo.io: {data}")
            if 'loc' in data:
                lat, lon = data['loc'].split(',')
                return float(lat), float(lon)
        print("AttendanceViewSet: Không thể lấy vị trí từ IP")
        return None, None
    except Exception as e:
        print(f"AttendanceViewSet: Lỗi khi lấy vị trí từ IP: {str(e)}")
        return None, None

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Kiểm tra nếu user có student profile
        try:
            student = Student.objects.get(user=user)
            return Attendance.objects.filter(student=student)
        except Student.DoesNotExist:
            # Nếu không phải student, trả về danh sách rỗng
            return Attendance.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        # Kiểm tra nếu user có student profile
        try:
            student = Student.objects.get(user=user)
            # Kiểm tra xem sinh viên có thuộc lớp của schedule này không
            schedule = serializer.validated_data['schedule']
            if not schedule.class_name.students.filter(id=student.id).exists():
                raise serializers.ValidationError("Bạn không phải là sinh viên trong lớp học này")

            # Nếu đã tồn tại bản ghi điểm danh, không cho phép tạo mới
            if Attendance.objects.filter(student=student, schedule=schedule).exists():
                raise serializers.ValidationError("Bạn đã điểm danh cho lịch học này rồi")

            # Kiểm tra thời gian và tính toán số phút trễ
            now = timezone.now()
            is_late = False
            minutes_late = None

            if now > schedule.start_time:
                # Tính số phút trễ (làm tròn lên)
                delta = now - schedule.start_time
                minutes_late = int(delta.total_seconds() / 60)
                is_late = minutes_late > 0

            # Lấy thông tin vị trí từ request data
            latitude = serializer.validated_data.get('latitude')
            longitude = serializer.validated_data.get('longitude')
            device_info = serializer.validated_data.get('device_info')

            # Nếu không có tọa độ từ client, thử lấy từ IP
            if not latitude or not longitude:
                client_ip = get_client_ip(self.request)
                location_data = get_location_from_ip(client_ip)
                if location_data:
                    latitude, longitude = location_data
                    if not device_info:
                        device_info = f"IP: {client_ip}, Vị trí: {latitude}, {longitude}"

            serializer.save(
                student=student,
                is_present=True,
                is_late=is_late,
                minutes_late=minutes_late,
                latitude=latitude,
                longitude=longitude,
                device_info=device_info,
                is_in_location=True
            )
        except Student.DoesNotExist:
            raise serializers.ValidationError("Bạn không có quyền điểm danh")

    @action(detail=False, methods=['post'], url_path='qr-attendance')
    def qr_attendance(self, request):
        serializer = QRCodeAttendanceSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user

            # Kiểm tra nếu user có student profile
            try:
                student = Student.objects.get(user=user)
            except Student.DoesNotExist:
                return Response(
                    {"error": "Bạn không có quyền điểm danh"},
                    status=status.HTTP_403_FORBIDDEN
                )

            schedule = serializer.validated_data['schedule']
            location_message = serializer.validated_data.get('location_message')

            # Kiểm tra xem sinh viên có thuộc lớp của schedule này không
            if not schedule.class_name.students.filter(id=student.id).exists():
                return Response(
                    {"error": "Bạn không phải là sinh viên trong lớp học này"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Kiểm tra thời gian và tính toán số phút trễ
            now = timezone.now()
            is_late = False
            minutes_late = None

            if now > schedule.start_time:
                # Tính số phút trễ (làm tròn lên)
                delta = now - schedule.start_time
                minutes_late = int(delta.total_seconds() / 60)
                is_late = minutes_late > 0

            # Lấy thông tin vị trí từ request data
            latitude = serializer.validated_data.get('latitude')
            longitude = serializer.validated_data.get('longitude')
            device_info = serializer.validated_data.get('device_info', '')

            # Thông tin về nguồn gốc vị trí
            location_source = "GPS thiết bị"

            # Nếu không có tọa độ từ client, thử lấy từ IP
            if not latitude or not longitude:
                client_ip = get_client_ip(request)
                location_data = get_location_from_ip(client_ip)
                if location_data and len(location_data) == 2:
                    latitude, longitude = location_data
                    location_source = "IP"

                    # Thêm thông tin vị trí vào device_info
                    location_info = f"IP: {client_ip}, Vị trí: {latitude}, {longitude}"
                    if device_info:
                        device_info = f"{device_info}, {location_info}"
                    else:
                        device_info = location_info

            # Kiểm tra xem đã điểm danh cho lịch học này chưa
            attendance, created = Attendance.objects.get_or_create(
                student=student,
                schedule=schedule,
                defaults={
                    'is_present': True,
                    'is_late': is_late,
                    'minutes_late': minutes_late,
                    'latitude': latitude,
                    'longitude': longitude,
                    'device_info': device_info,
                    'is_in_location': True
                }
            )

            if not created:
                # Nếu bản ghi đã tồn tại, cập nhật trạng thái
                attendance.is_present = True
                attendance.is_late = is_late
                attendance.minutes_late = minutes_late
                attendance.latitude = latitude
                attendance.longitude = longitude
                attendance.device_info = device_info
                attendance.is_in_location = True
                attendance.save()
                message = "Bạn đã cập nhật điểm danh thành công"
            else:
                message = "Bạn đã điểm danh thành công"

            attendance_status = "Có mặt"
            if is_late:
                attendance_status = f"Trễ {minutes_late} phút"

            # Format thời gian theo múi giờ Việt Nam
            timestamp_vn = timezone.localtime(attendance.timestamp).strftime('%H:%M:%S %d/%m/%Y')

            return Response({
                "status": "success",
                "message": message,
                "attendance": {
                    "id": attendance.id,
                    "schedule_id": schedule.id,
                    "course_name": schedule.course_name.object_name,
                    "teacher": schedule.teacher.user.name,
                    "classroom": schedule.room.classroom_code,
                    "timestamp": attendance.timestamp,
                    "timestamp_vn": timestamp_vn,
                    "is_present": attendance.is_present,
                    "is_late": attendance.is_late,
                    "minutes_late": attendance.minutes_late,
                    "attendance_status": attendance_status,
                    "location": f"{latitude}, {longitude}" if latitude and longitude else None,
                    "location_source": location_source,
                    "location_message": location_message
                }
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)