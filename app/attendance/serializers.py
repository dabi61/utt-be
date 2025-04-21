from rest_framework import serializers
from core.models import Attendance, Schedule
from django.utils import timezone
from datetime import datetime, timedelta
import json
import math

class ScheduleDetailSerializer(serializers.ModelSerializer):
    course_name = serializers.StringRelatedField(source='course_name.object_name')
    teacher_name = serializers.StringRelatedField(source='teacher.user.name')
    room = serializers.StringRelatedField(source='room.classroom_code')
    class_name = serializers.StringRelatedField(source='class_name.class_name')

    class Meta:
        model = Schedule
        fields = ['id', 'course_name', 'teacher_name', 'room', 'class_name', 'start_time', 'end_time']

class AttendanceSerializer(serializers.ModelSerializer):
    schedule_detail = ScheduleDetailSerializer(source='schedule', read_only=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    device_info = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    attendance_status = serializers.SerializerMethodField(read_only=True)
    location = serializers.SerializerMethodField(read_only=True)
    timestamp_vn = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'schedule', 'schedule_detail', 'timestamp', 'timestamp_vn',
            'is_present', 'is_late', 'minutes_late', 
            'latitude', 'longitude', 'device_info',
            'attendance_status', 'location'
        ]
        read_only_fields = ['id', 'timestamp', 'is_present', 'is_late', 'minutes_late']
    
    def get_attendance_status(self, obj):
        if not obj.is_present:
            return "Vắng mặt"
        elif obj.is_late:
            return f"Trễ {obj.minutes_late} phút"
        else:
            return "Có mặt"
    
    def get_location(self, obj):
        if obj.latitude and obj.longitude:
            return f"{obj.latitude}, {obj.longitude}"
        return None
    
    def get_timestamp_vn(self, obj):
        if obj.timestamp:
            return timezone.localtime(obj.timestamp).strftime('%H:%M:%S %d/%m/%Y')
        return None

class QRCodeAttendanceSerializer(serializers.Serializer):
    qr_data = serializers.CharField(required=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    device_info = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    def validate(self, attrs):
        qr_data = attrs.get('qr_data')
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')
        
        # Parse QR data
        try:
            qr_json = qr_data.replace("'", '"')
            qr_info = json.loads(qr_json)
            schedule_id = qr_info.get('schedule_id')
        except (json.JSONDecodeError, AttributeError):
            raise serializers.ValidationError("Mã QR không hợp lệ")
        
        # Kiểm tra schedule tồn tại
        try:
            schedule = Schedule.objects.get(id=schedule_id)
        except Schedule.DoesNotExist:
            raise serializers.ValidationError("Lịch học không tồn tại")
        
        # Kiểm tra thời gian
        now = timezone.now()
        if now > schedule.end_time:
            raise serializers.ValidationError("Đã hết thời gian điểm danh cho buổi học này")
        
        # Kiểm tra thời gian bắt đầu (có thể điểm danh trước 15 phút)
        if now < schedule.start_time - timedelta(minutes=15):
            raise serializers.ValidationError(f"Chưa đến thời gian điểm danh. Bạn có thể điểm danh 15 phút trước giờ học bắt đầu ({timezone.localtime(schedule.start_time).strftime('%H:%M:%S %d/%m/%Y')})")
        
        # Kiểm tra ngày trong tuần
        weekday_map = {
            0: 'MON',  # Thứ 2
            1: 'TUE',  # Thứ 3
            2: 'WED',  # Thứ 4
            3: 'THU',  # Thứ 5
            4: 'FRI',  # Thứ 6
            5: 'SAT',  # Thứ 7
            6: 'SUN',  # Chủ nhật
        }
        current_weekday = weekday_map.get(now.weekday())
        if not schedule.weekdays.filter(day=current_weekday).exists():
            raise serializers.ValidationError(f"Hôm nay không phải là ngày học của lịch này")
        
        # Kiểm tra vị trí (nếu có tọa độ và phòng học có tọa độ)
        classroom = schedule.room
        location_message = None
        
        if latitude is None or longitude is None:
            location_message = "Không nhận được tọa độ vị trí từ thiết bị. Hệ thống sẽ sử dụng vị trí dựa trên IP."
        elif classroom.latitude is None or classroom.longitude is None:
            location_message = "Phòng học chưa được cài đặt tọa độ. Không thể xác minh vị trí điểm danh."
        else:
            # Tính khoảng cách sử dụng công thức Haversine
            max_distance = 100  # mét
            
            def calculate_distance(lat1, lon1, lat2, lon2):
                # Bán kính trái đất (mét)
                R = 6371000
                
                # Chuyển đổi độ sang radian
                lat1_rad = math.radians(lat1)
                lon1_rad = math.radians(lon1)
                lat2_rad = math.radians(lat2)
                lon2_rad = math.radians(lon2)
                
                # Hiệu số giữa các tọa độ
                dlat = lat2_rad - lat1_rad
                dlon = lon2_rad - lon1_rad
                
                # Công thức Haversine
                a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                distance = R * c
                
                return distance
            
            distance = calculate_distance(latitude, longitude, classroom.latitude, classroom.longitude)
            
            if distance > max_distance:
                raise serializers.ValidationError(f"Bạn cần ở gần phòng học để điểm danh (khoảng cách hiện tại: {int(distance)} mét, tối đa cho phép: {max_distance} mét)")
            else:
                location_message = f"Vị trí hợp lệ, cách phòng học {int(distance)} mét."
        
        # Lưu lại schedule và thông báo vị trí để sử dụng sau này
        attrs['schedule'] = schedule
        attrs['location_message'] = location_message
        return attrs