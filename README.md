# UTT BE - Hệ thống quản lý trường học (Backend)

Dự án backend cho hệ thống quản lý trường học UTT, được xây dựng bằng Django.

## Tính năng

- **Xác thực**: Đăng nhập, đăng ký, phân quyền người dùng.
- **Quản lý điểm danh**: Điểm danh sinh viên, xem báo cáo điểm danh.
- **Quản lý lớp học**: Quản lý thông tin lớp học, sinh viên và giáo viên.
- **Quản lý lịch học**: Xem và quản lý lịch học theo lớp, giáo viên, sinh viên.

## Cài đặt và chạy dự án

### Yêu cầu

- Python (3.8+)
- Django (5.2+)
- Django REST Framework
- Các thư viện khác được liệt kê trong `requirements.txt`

### Hướng dẫn cài đặt

1. Di chuyển vào thư mục backend:
   ```bash
   cd utt-be
   ```

2. Tạo và kích hoạt môi trường ảo:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Cài đặt dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Chạy migrations:
   ```bash
   cd app
   python manage.py migrate
   ```

5. Khởi động server:
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Xác thực

- `POST /auth/jwt/create/`: Đăng nhập và tạo token
- `POST /auth/users/`: Đăng ký người dùng mới
- `POST /auth/jwt/refresh/`: Làm mới token
- `GET /auth/users/me/`: Lấy thông tin người dùng hiện tại

### Quản lý trường học

- `GET /api/school/classes/`: Lấy danh sách lớp học
- `GET /api/school/classes/{id}/`: Lấy chi tiết lớp học
- `GET /api/core/schedules/`: Lấy danh sách lịch học
- `GET /api/attendance/`: Lấy danh sách điểm danh
- `POST /api/attendance/`: Tạo điểm danh mới
- `PATCH /api/attendance/{id}/`: Cập nhật điểm danh

## Liên hệ

Nếu có vấn đề hoặc đề xuất cải thiện, vui lòng tạo issue trên repo này.