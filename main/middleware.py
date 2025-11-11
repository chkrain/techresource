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
        if request.path.startswith('/admin/'):
            if any(path in request.path for path in [
                '/admin/login/',
                '/admin/logout/', 
                '/admin/password_reset/',
                '/admin/2fa/',
                '/static/',
                '/media/'
            ]):
                return None
            
            allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])
            if allowed_ips:
                client_ip = self.get_client_ip(request)
                if not self.is_ip_allowed(client_ip, allowed_ips):
                    logger.warning(f"Admin access denied for IP: {client_ip}")
                    from django.contrib import messages
                    messages.error(request, 'Доступ к админке с вашего IP-адреса запрещен.')
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
        return ip in allowed_ips

class Admin2FAMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.path.startswith('/admin/'):
            return None
            
        print(f"🔐 2FA Middleware triggered for: {request.path}")
        
        excluded_paths = [
            '/admin/login/',
            '/admin/logout/', 
            '/admin/password_reset/',
            '/admin-2fa/verify/',
            '/admin-2fa/setup/',
            '/static/',
            '/media/',
            '/admin/jsi18n/',
        ]
        
        if any(request.path.startswith(excluded) for excluded in excluded_paths):
            print(f"✅ Path {request.path} excluded from 2FA")
            return None
        
        if request.user.is_authenticated and request.user.is_staff:
            print(f"👤 User {request.user.username} is staff, checking 2FA...")
            
            try:
                from .models import Admin2FA
                admin_2fa = Admin2FA.objects.get(user=request.user)
                
                if not admin_2fa.is_enabled:
                    print("⚙️ 2FA not enabled - access granted")
                    return None
                
                if not request.session.get('admin_2fa_verified'):
                    print("🚨 2FA enabled but not verified - REDIRECTING to verify")
                    return HttpResponseRedirect(reverse('admin_2fa_verify'))
                
                print("✅ 2FA verified - access granted")
                return None  
                    
            except Admin2FA.DoesNotExist:
                print("🆕 No 2FA record - creating and allowing access")
                Admin2FA.objects.create(user=request.user)
                return None
        
        return None