# techresource/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404, handler500, handler403, handler400
from django.conf import settings
from main import views

handler404 = 'main.views.handler404'
handler500 = 'main.views.handler500'
handler403 = 'main.views.handler403'
handler400 = 'main.views.handler400'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-2fa/verify/', views.admin_2fa_verify, name='admin_2fa_verify'),  
    path('admin-2fa/setup/', views.admin_2fa_setup, name='admin_2fa_setup'),
    path('', include('main.urls')),
]

# Только для разработки!
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)