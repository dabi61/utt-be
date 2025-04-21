from rest_framework import serializers
from ..models import Schedule, Attendance, Student
from django.utils import timezone
import json
from math import radians, cos, sin, asin, sqrt
from datetime import timedelta

class ScheduleQRSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.user.name', read_only=True)
    course_name = serializers.CharField(source='course_name.object_name', read_only=True)
    room_name = serializers.CharField(source='room.classroom_code', read_only=True)
    class_name = serializers.CharField(source='class_name.class_name', read_only=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [
            'id', 'teacher_name', 'course_name', 'room_name', 
            'class_name', 'start_time', 'end_time', 'qr_code_url'
        ]

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            return obj.qr_code.url
        return None

class QRAttendanceSerializer(serializers.Serializer):
    qr_data = serializers.CharField(required=True)
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Tính khoảng cách giữa hai tọa độ GPS 
        sử dụng công thức Haversine
        """
        # Chuyển đổi độ sang radian
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        
        # Công thức Haversine
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Bán kính trái đất tính bằng km
        
        # Chuyển đổi từ km sang mét
        return c * r * 1000
    
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
        
        # Kiểm tra thời gian hiện tại có nằm trong khoảng thời gian của buổi học
        now = timezone.now()
        
        # Thời gian trễ cho phép (mặc định 15 phút)
        late_threshold = getattr(schedule, 'late_threshold', 15)
        end_time_with_grace = schedule.end_time
        
        # Kiểm tra xem hiện tại có nằm trong thời gian buổi học (với thời gian gia hạn nếu có)
        if now > end_time_with_grace:
            raise serializers.ValidationError(
                f"Đã hết thời gian điểm danh cho buổi học này. Buổi học kết thúc lúc {schedule.end_time.strftime('%H:%M')}"
            )
        
        if now < schedule.start_time:
            raise serializers.ValidationError(
                f"Buổi học chưa bắt đầu. Buổi học bắt đầu lúc {schedule.start_time.strftime('%H:%M')}"
            )
        
        # Kiểm tra xem có điểm danh trễ không
        is_late = now > schedule.start_time + timedelta(minutes=late_threshold)
        attrs['is_late'] = is_late
        
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
        
        # Kiểm tra vị trí
        # Trong trường hợp thực tế, bạn cần thêm trường latitude và longitude cho Classroom
        # Ở đây tôi sẽ giả định là classroom có tọa độ (nếu có)
        classroom = schedule.room
        
        # Nếu classroom có tọa độ (giả định có trường latitude và longitude)
        # thì kiểm tra khoảng cách
        # Giả sử classroom có tọa độ (để sau này bạn có thể bổ sung)
        # Tạm thời cho giá trị cứng để minh họa:
        classroom_lat = getattr(classroom, 'latitude', None)
        classroom_lon = getattr(classroom, 'longitude', None)
        
        if classroom_lat and classroom_lon:
            # Tính khoảng cách
            distance = self.haversine_distance(
                latitude, longitude, 
                classroom_lat, classroom_lon
            )
            
            # Khoảng cách tối đa cho phép (ví dụ: 100m)
            max_distance = 100  # 100 mét
            
            if distance > max_distance:
                raise serializers.ValidationError(
                    f"Bạn đang ở cách phòng học quá xa ({distance:.0f}m). Vui lòng đến gần phòng học hơn."
                )
            
            # Lưu khoảng cách để sử dụng sau này
            attrs['distance'] = distance
        
        # Lưu schedule để sử dụng sau
        attrs['schedule'] = schedule
        return attrs 