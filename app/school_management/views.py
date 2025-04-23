from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from core.models import Class, Teacher, Student
from .serializers import ClassSerializer, TeacherSerializer, StudentSerializer

class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def add_student(self, request, pk=None):
        class_obj = self.get_object()
        student_id = request.data.get('student_id')
        
        try:
            student = Student.objects.get(id=student_id)
            class_obj.students.add(student)
            return Response({'status': 'success', 'message': 'Đã thêm sinh viên vào lớp'})
        except Student.DoesNotExist:
            return Response({'error': 'Không tìm thấy sinh viên'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def add_teacher(self, request, pk=None):
        class_obj = self.get_object()
        teacher_id = request.data.get('teacher_id')
        
        try:
            teacher = Teacher.objects.get(id=teacher_id)
            class_obj.teachers.add(teacher)
            return Response({'status': 'success', 'message': 'Đã thêm giáo viên vào lớp'})
        except Teacher.DoesNotExist:
            return Response({'error': 'Không tìm thấy giáo viên'}, status=status.HTTP_404_NOT_FOUND)

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def my_classes(self, request):
        teacher = request.user.teacher
        classes = teacher.teaching_classes.all()
        serializer = ClassSerializer(classes, many=True)
        return Response(serializer.data)

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def my_classes(self, request):
        student = request.user.student
        classes = student.student_classes.all()
        serializer = ClassSerializer(classes, many=True)
        return Response(serializer.data) 