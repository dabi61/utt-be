"""
Views for the user API.
"""

from rest_framework import generics, authentication, permissions, status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.serializers import UserSerializer, AuthTokenSerializer
from django.contrib.auth import get_user_model, authenticate

# CreateApiView:
#   POST để tạo object mới
#   auto xử lý serialization
#   auto validate
#   auto trả về response phù hợp


class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system."""
    serializer_class = UserSerializer

# ObtainAuthToken
#   Xử lý authentication
#   Tạo token cho user
#   Quản lý session
#   Các tính nagw kế thừa
#   post()
#   get_serializer_context: Context cho serializer
#   Token generation logic


class CreateTokenView(ObtainAuthToken):
    """Create a new auth token for user."""
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

# RetrieveUpdateAPIView
# GET: Lấy thông tin của object
# PUT/PATCH: cập nhật object
# Tự động xử lý serialization
# Các tính năng kế thừa
#   get(): xử lý get request
#   put(): xử lý Put request
#   patch(): xử lý patch request
#   get_object(): Lấy object cần xử lý


class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user."""
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    # Override get_object
    # Trả về user hiện tại
    # Không cần query database
    # Đơn giản hóa logic

    def get_object(self):
        """Retrieve and return the authenticated user."""
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Trả về dữ liệu người dùng đã cập nhật
        return Response(serializer.data)


class UserInfoView(generics.RetrieveAPIView):
    """Retrieve extended user information."""
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UpdateProfileView(generics.UpdateAPIView):
    """Update user profile information."""
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change user password."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        # Kiểm tra các tham số bắt buộc
        if not old_password or not new_password:
            return Response(
                {'error': 'Mật khẩu cũ và mới là bắt buộc'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Xác thực mật khẩu cũ
        if not authenticate(username=user.email, password=old_password):
            return Response(
                {'old_password': ['Mật khẩu hiện tại không chính xác']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Kiểm tra độ dài mật khẩu mới
        if len(new_password) < 5:
            return Response(
                {'new_password': ['Mật khẩu phải có ít nhất 5 ký tự']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Thiết lập mật khẩu mới
        user.set_password(new_password)
        user.save()
        
        return Response({'detail': 'Mật khẩu đã được thay đổi thành công'}, status=status.HTTP_200_OK)


class UploadAvatarView(APIView):
    """Upload user avatar."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        print("Received files:", request.FILES)
        print("Received data:", request.data)
        
        if 'avatar' not in request.FILES:
            return Response({'error': 'No avatar file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        avatar_file = request.FILES['avatar']
        print(f"Processing avatar: {avatar_file.name}, size: {avatar_file.size}, content type: {avatar_file.content_type}")
        
        try:
            user = request.user
            
            # Xóa avatar cũ nếu có
            if user.avatar:
                user.avatar.delete(save=False)
                
            # Gán avatar mới
            user.avatar = avatar_file
            user.save()
            
            # Trả về toàn bộ thông tin người dùng
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error uploading avatar: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RemoveAvatarView(APIView):
    """Remove user avatar."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, format=None):
        user = request.user
        if user.avatar:
            user.avatar = None
            user.save()
            
            # Trả về toàn bộ thông tin người dùng đã cập nhật
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        return Response({'message': 'No avatar to remove'}, status=status.HTTP_400_BAD_REQUEST)
