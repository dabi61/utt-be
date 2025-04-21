"""
Serializers for the user API view.
"""

from django.contrib.auth import (
    get_user_model,
    authenticate
)
from django.utils.translation import gettext as _

from rest_framework import serializers

# ModelSerializer cung cấp
# Tự động tạo các field dựa trên model
# Tự động tạo các validators
# Tự động tạo các phương thức create và update mặc định
# Các tính năng được kế thừa
#   Validate tự động cho các trường
#   Chuyển đổi giữa model instance và python primitives
#   Xử lý các relationships
#   Nested serialization

# VD: auto validate field email (email = serializers.EmailFields())


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the user object."""
    avatar_url = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    student_info = serializers.SerializerMethodField(read_only=True)
    teacher_info = serializers.SerializerMethodField(read_only=True)

    # Xử lý các relationships
    class Meta:
        model = get_user_model()  # Tự động fields
        # Tự động map với các model fields
        fields = [
            'id', 'email', 'password', 'name', 'phone_number', 'address', 
            'date_of_birth', 'gender', 'bio', 'avatar', 'avatar_url', 
            'role', 'student_info', 'teacher_info'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 5, 'required': False},
            'avatar': {'write_only': True, 'required': False},
        }

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def get_role(self, obj):
        # Giả định đơn giản về vai trò dựa trên email
        if obj.is_superuser:
            return 'admin'
        if obj.email and 'teacher' in obj.email:
            return 'teacher'
        return 'student'
    
    def get_student_info(self, obj):
        # Kiểm tra xem người dùng có thông tin sinh viên không
        try:
            if hasattr(obj, 'student'):
                return {
                    'student_code': obj.student.student_code,
                    'classes_count': obj.student.student_classes.count()
                }
        except:
            pass
        return None
    
    def get_teacher_info(self, obj):
        # Kiểm tra xem người dùng có thông tin giáo viên không
        try:
            if hasattr(obj, 'teacher'):
                return {
                    'teacher_code': obj.teacher.teacher_code,
                    'classes_count': obj.teacher.teacher_classes.count()
                }
        except:
            pass
        return None

    # override lại các phương thức
    def create(self, validated_data):
        """Create and return a user with encrypted password."""
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        """Update and return user."""
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user

# Serializer là lớp cơ bản
# Kiểm soát hoàn toàn quá trình serialization
# Không ràng buộc với model
# Phải tự định nhĩa các phương thứ chính
# Các tính năng kế thừa
#   Cơ chế validation cơ bản
#   Convert data
#   Error handling
#   Context handling


class AuthTokenSerializer(serializers.Serializer):
    """Serializer for the user authentication object."""
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        """Validate and authenticate the user."""
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )

        if not user:
            msg = _('Unable to authenticate with provided credentials.')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs

