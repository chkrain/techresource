# main/middleware.py
import time
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
import logging

logger = logging.getLogger('django.security')

class AdminSecurityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/secure-admin/'):
            # Проверка IP-адреса для админки
            allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])
            if allowed_ips:
                client_ip = self.get_client_ip(request)
                if not self.is_ip_allowed(client_ip, allowed_ips):
                    logger.warning(f"Admin access denied for IP: {client_ip}")
                    return HttpResponseRedirect(reverse('index'))
            
            # Логирование доступа к админке
            if request.user.is_authenticated and request.user.is_staff:
                logger.info(f"Admin access: {request.user.username} from {self.get_client_ip(request)} to {request.path}")
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_ip_allowed(self, ip, allowed_ips):
        # Простая проверка IP (можно расширить для подсетей)
        return ip in allowed_ips

class Admin2FAMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if (request.path.startswith('/secure-admin/') and 
            request.user.is_authenticated and 
            request.user.is_staff and
            not request.path in ['/secure-admin/2fa/verify/', '/secure-admin/logout/']):
            
            try:
                from .models import Admin2FA
                admin_2fa = Admin2FA.objects.get(user=request.user)
                if admin_2fa.is_enabled and not request.session.get('admin_2fa_verified'):
                    return HttpResponseRedirect(reverse('admin_2fa_verify'))
            except Admin2FA.DoesNotExist:
                pass