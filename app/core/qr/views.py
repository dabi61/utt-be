from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, F, Q, Sum, Case, When, IntegerField
from django.utils import timezone
from ..models import Schedule, Attendance, Student
from .serializers import ScheduleQRSerializer, QRAttendanceSerializer

class ScheduleQRViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleQRSerializer

    @action(detail=True, methods=['post'])
    def generate_qr(self, request, pk=None):
        schedule = self.get_object()
        try:
            qr_code_url = schedule.generate_qr_code()
            return Response({
                'status': 'success',
                'message': 'QR code generated successfully',
                'qr_code_url': qr_code_url
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='attendance')
    def qr_attendance(self, request):
        serializer = QRAttendanceSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            
            # Kiểm tra nếu user có student profile
            try:
                student = Student.objects.get(user=user)
            except Student.DoesNotExist:
                return Response({
                    "status": "error",
                    "message": "Bạn không có quyền điểm danh"
                }, status=status.HTTP_403_FORBIDDEN)
            
            schedule = serializer.validated_data['schedule']
            is_late = serializer.validated_data.get('is_late', False)
            distance = serializer.validated_data.get('distance')
            
            # Kiểm tra xem sinh viên có thuộc lớp của schedule này không
            if not schedule.class_name.students.filter(id=student.id).exists():
                return Response({
                    "status": "error",
                    "message": "Bạn không phải là sinh viên trong lớp học này"
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Tính số phút trễ (nếu trễ)
            minutes_late = None
            if is_late:
                time_diff = timezone.now() - schedule.start_time
                minutes_late = int(time_diff.total_seconds() / 60)
            
            # Kiểm tra xem đã điểm danh cho lịch học này chưa
            # và cập nhật hoặc tạo mới
            attendance, created = Attendance.objects.get_or_create(
                student=student,
                schedule=schedule,
                defaults={
                    'is_present': True,
                    'is_late': is_late,
                    'minutes_late': minutes_late
                }
            )
            
            if not created:
                # Nếu bản ghi đã tồn tại, cập nhật trạng thái
                attendance.is_present = True
                
                # Chỉ cập nhật is_late nếu chưa điểm danh hoặc cập nhật điểm danh sớm hơn
                if attendance.is_late and not is_late:
                    attendance.is_late = False
                    attendance.minutes_late = None
                elif not attendance.is_late and is_late:
                    attendance.is_late = True
                    attendance.minutes_late = minutes_late
                    
                attendance.save()
                message = "Bạn đã cập nhật điểm danh thành công"
            else:
                message = "Bạn đã điểm danh thành công"
            
            # Lấy thống kê điểm danh của sinh viên cho lớp này
            attendance_stats = Attendance.objects.filter(
                student=student,
                schedule__class_name=schedule.class_name
            ).aggregate(
                total=Count('id'),
                present=Sum(Case(When(is_present=True, then=1), default=0, output_field=IntegerField())),
                late=Sum(Case(When(is_late=True, then=1), default=0, output_field=IntegerField()))
            )
            
            # Tính tỷ lệ điểm danh
            total_schedules = attendance_stats.get('total', 0)
            present_count = attendance_stats.get('present', 0)
            late_count = attendance_stats.get('late', 0)
            
            attendance_rate = 0
            if total_schedules > 0:
                attendance_rate = (present_count / total_schedules) * 100
            
            late_status = "Đúng giờ"
            if is_late:
                late_status = f"Trễ {minutes_late} phút"
            
            return Response({
                "status": "success",
                "message": message,
                "data": {
                    "attendance_id": attendance.id,
                    "schedule_id": schedule.id,
                    "course_name": schedule.course_name.object_name,
                    "teacher": schedule.teacher.user.name,
                    "classroom": schedule.room.classroom_code,
                    "timestamp": attendance.timestamp,
                    "is_present": attendance.is_present,
                    "attendance_status": late_status,
                    "distance_to_classroom": f"{distance:.1f}m" if distance else "Không xác định",
                    "attendance_time": timezone.now().strftime("%H:%M:%S %d/%m/%Y")
                },
                "statistics": {
                    "total_lectures": total_schedules,
                    "present_count": present_count,
                    "late_count": late_count,
                    "attendance_rate": f"{attendance_rate:.1f}%",
                    "course_name": schedule.course_name.object_name,
                    "class_name": schedule.class_name.class_name
                }
            })
        
        return Response({
            "status": "error",
            "message": "Dữ liệu không hợp lệ",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=['get'], url_path='attendance-stats')
    def attendance_stats(self, request):
        """Lấy thống kê điểm danh của sinh viên"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Bạn không phải là sinh viên"
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Lấy thống kê điểm danh theo từng lớp học
        class_stats = []
        
        for class_obj in student.student_classes.all():
            # Lấy thống kê điểm danh cho lớp này
            class_attendance = Attendance.objects.filter(
                student=student, 
                schedule__class_name=class_obj
            ).aggregate(
                total=Count('id'),
                present=Sum(Case(When(is_present=True, then=1), default=0, output_field=IntegerField())),
                late=Sum(Case(When(is_late=True, then=1), default=0, output_field=IntegerField()))
            )
            
            total = class_attendance.get('total', 0)
            present = class_attendance.get('present', 0)
            late = class_attendance.get('late', 0)
            
            attendance_rate = 0
            if total > 0:
                attendance_rate = (present / total) * 100
                
            # Lấy thông tin tất cả các buổi học của lớp
            schedules = Schedule.objects.filter(class_name=class_obj)
            
            # Lấy thông tin điểm danh cho mỗi buổi học
            schedule_details = []
            for schedule in schedules:
                try:
                    attendance = Attendance.objects.get(student=student, schedule=schedule)
                    status = "Vắng mặt"
                    if attendance.is_present:
                        status = "Trễ" if attendance.is_late else "Có mặt"
                        
                    schedule_details.append({
                        "schedule_id": schedule.id,
                        "course_name": schedule.course_name.object_name,
                        "date": schedule.start_time.strftime("%d/%m/%Y"),
                        "time": f"{schedule.start_time.strftime('%H:%M')} - {schedule.end_time.strftime('%H:%M')}",
                        "status": status,
                        "minutes_late": attendance.minutes_late if attendance.minutes_late else 0
                    })
                except Attendance.DoesNotExist:
                    schedule_details.append({
                        "schedule_id": schedule.id,
                        "course_name": schedule.course_name.object_name,
                        "date": schedule.start_time.strftime("%d/%m/%Y"),
                        "time": f"{schedule.start_time.strftime('%H:%M')} - {schedule.end_time.strftime('%H:%M')}",
                        "status": "Chưa điểm danh",
                        "minutes_late": 0
                    })
            
            class_stats.append({
                "class_id": class_obj.id,
                "class_name": class_obj.class_name,
                "total_schedules": total,
                "present_count": present,
                "late_count": late,
                "attendance_rate": f"{attendance_rate:.1f}%",
                "schedules": schedule_details
            })
        
        return Response({
            "status": "success",
            "student_name": student.user.name,
            "student_code": student.student_code,
            "class_statistics": class_stats
        }) 