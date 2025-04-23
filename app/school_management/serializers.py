from rest_framework import serializers
from core.models import Class, Teacher, Student

class ClassSerializer(serializers.ModelSerializer):
    students = serializers.SerializerMethodField()
    teachers = serializers.SerializerMethodField()

    class Meta:
        model = Class
        fields = ['id', 'class_code', 'class_name', 'students', 'teachers']

    def get_students(self, obj):
        return [{
            'id': student.id,
            'student_code': student.student_code,
            'name': student.user.name,
            'email': student.user.email
        } for student in obj.students.all()]

    def get_teachers(self, obj):
        return [{
            'id': teacher.id,
            'teacher_code': teacher.teacher_code,
            'name': teacher.user.name,
            'email': teacher.user.email
        } for teacher in obj.teachers.all()]

class TeacherSerializer(serializers.ModelSerializer):
    teaching_classes = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ['id', 'teacher_code', 'name', 'email', 'teaching_classes']

    def get_name(self, obj):
        return obj.user.name

    def get_email(self, obj):
        return obj.user.email

    def get_teaching_classes(self, obj):
        return [{
            'id': cls.id,
            'class_code': cls.class_code,
            'class_name': cls.class_name
        } for cls in obj.teaching_classes.all()]

class StudentSerializer(serializers.ModelSerializer):
    student_classes = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['id', 'student_code', 'name', 'email', 'student_classes']

    def get_name(self, obj):
        return obj.user.name

    def get_email(self, obj):
        return obj.user.email

    def get_student_classes(self, obj):
        return [{
            'id': cls.id,
            'class_code': cls.class_code,
            'class_name': cls.class_name
        } for cls in obj.student_classes.all()] 