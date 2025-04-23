from django.utils.deprecation import MiddlewareMixin

class FakeIPMiddleware:
    """
    Middleware giả lập địa chỉ IP.
    Cho phép sử dụng tham số fake_ip trong URL để giả lập địa chỉ IP người dùng.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        fake_ip = request.GET.get('fake_ip')
        if fake_ip:
            # Lưu địa chỉ IP gốc
            request._original_ip = request.META.get('REMOTE_ADDR', '')
            # Đánh dấu đã sử dụng fake IP
            request._fake_ip_used = True
            # Lưu giá trị fake_ip
            request._fake_ip = fake_ip
            # Ghi đè địa chỉ IP trong META
            request.META['REMOTE_ADDR'] = fake_ip
            request.META['HTTP_X_FORWARDED_FOR'] = fake_ip
        else:
            request._fake_ip_used = False

        return self.get_response(request)

    def get_original_ip(self, request):
        """
        Lấy địa chỉ IP gốc từ request.
        """
        return getattr(request, '_original_ip', request.META.get('REMOTE_ADDR', '')) 