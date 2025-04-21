from django.contrib import admin
from core.models import Attendance, Student

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['get_student_name', 'get_course_name', 'timestamp', 'is_present']
    list_filter = ['is_present', 'schedule__course_name', 'schedule__class_name']
    search_fields = ['student__user__name', 'schedule__course_name__object_name']
    
    def get_student_name(self, obj):
        return obj.student.user.name
    get_student_name.short_description = 'Sinh viên'
    
    def get_course_name(self, obj):
        return f"{obj.schedule.course_name} ({obj.schedule.class_name})"
    get_course_name.short_description = 'Lịch học'
    
    def get_fields(self, request, obj=None):
        # Nếu đang tạo mới (obj=None), chỉ hiển thị trường schedule và student
        if obj is None:
            return ['student', 'schedule', 'is_present']
        # Nếu đang xem/chỉnh sửa, hiển thị tất cả các trường
        return ['student', 'schedule', 'timestamp', 'is_present']
    
    def get_readonly_fields(self, request, obj=None):
        # Các trường chỉ đọc
        if obj:  # Nếu đang chỉnh sửa
            return ['timestamp']
        return ['timestamp']  # Nếu đang tạo mới
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "student":
            kwargs["queryset"] = Student.objects.all().order_by('user__name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        # Nếu là superuser, có thể thấy tất cả attendance
        # Còn không thì chỉ thấy của học sinh thuộc các lớp mà giáo viên dạy
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            teacher = request.user.teacher
            classes = teacher.teaching_classes.all()
            return qs.filter(schedule__class_name__in=classes)
        except:
            # Nếu không phải giáo viên, có thể là học sinh
            try:
                student = request.user.student
                return qs.filter(student=student)
            except:
                return qs.none() 