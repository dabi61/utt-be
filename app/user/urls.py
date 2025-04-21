"""
URLs for the user API.
"""

from django.urls import path

from user import views

app_name = 'user'

urlpatterns = [
    path('create/', views.CreateUserView.as_view(), name='create'),
    path('token/', views.CreateTokenView.as_view(), name='token'),
    path('me/', views.ManageUserView.as_view(), name='me'),
    path('update-profile/', views.UpdateProfileView.as_view(), name='update-profile'),
    path('user-info/', views.UserInfoView.as_view(), name='user-info'),
    path('upload-avatar/', views.UploadAvatarView.as_view(), name='upload-avatar'),
    path('remove-avatar/', views.RemoveAvatarView.as_view(), name='remove-avatar'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
]
