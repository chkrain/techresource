# main/views_privacy.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.db.models import Q
import json
import logging
from django.views.decorators.csrf import csrf_exempt 
import traceback
from django.core.exceptions import ValidationError

from .models import PrivacyConsent, PrivacyRequest, UserProfile, SecurityLog, PrivacyConsentLog

logger = logging.getLogger(__name__)

class PrivacyDashboardView(LoginRequiredMixin, TemplateView):
    """Личный кабинет для управления персональными данными"""
    template_name = 'main/privacy_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        active_consents = PrivacyConsent.objects.filter(
            user=user,
            is_active=True
        ).order_by('-granted_at')
        
        revoked_consents = PrivacyConsent.objects.filter(
            user=user,
            is_active=False
        ).order_by('-revoked_at')
        
        privacy_requests = PrivacyRequest.objects.filter(
            Q(user=user) | Q(email=user.email)
        ).order_by('-created_at')
        
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            profile = None
        
        context.update({
            'active_consents': active_consents,
            'revoked_consents': revoked_consents,
            'privacy_requests': privacy_requests,
            'profile': profile,
            'user_data': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined,
                'last_login': user.last_login,
            }
        })
        
        return context

@login_required
@require_POST
@csrf_exempt
def revoke_consent(request, consent_id):
    """Отзыв конкретного согласия"""
    try:
        consent = get_object_or_404(
            PrivacyConsent,
            id=consent_id,
            user=request.user,
            is_active=True
        )
        
        consent.revoke(
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        try:
            SecurityLog.objects.create(
                user=request.user,
                action='consent_revoked',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True,
                details={
                    'consent_type': consent.consent_type,
                    'consent_version': consent.version,
                    'consent_id': str(consent.id)
                },
                risk_level='low'
            )
        except Exception as log_error:
            logger.warning(f"Ошибка при создании SecurityLog: {str(log_error)}")
        
        messages.success(
            request, 
            f'Согласие "{consent.get_consent_type_display()}" успешно отозвано.'
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Согласие отозвано',
                'consent_id': consent_id
            })
            
        return redirect('privacy_dashboard')
        
    except Exception as e:
        logger.error(f'Ошибка отзыва согласия: {str(e)}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
            
        messages.error(request, f'Ошибка при отзыве согласия: {str(e)}')
        return redirect('privacy_dashboard')

@login_required
@require_POST
@csrf_exempt
def bulk_revoke_consents(request):
    """Массовый отзыв согласий"""
    try:
        data = json.loads(request.body)
        consent_ids = data.get('consent_ids', [])
        
        if not consent_ids:
            return JsonResponse({'success': False, 'error': 'Не выбраны согласия'}, status=400)
        
        revoked_count = 0
        for consent_id in consent_ids:
            try:
                consent = PrivacyConsent.objects.get(
                    id=consent_id,
                    user=request.user,
                    is_active=True
                )
                consent.revoke(
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                revoked_count += 1
            except PrivacyConsent.DoesNotExist:
                continue
        
        SecurityLog.objects.create(
            user=request.user,
            action='bulk_consent_revoked',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True,
            details={
                'revoked_count': revoked_count,
                'consent_ids': consent_ids
            },
            risk_level='low'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Отозвано {revoked_count} согласий',
            'revoked_count': revoked_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        logger.error(f'Ошибка массового отзыва согласий: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def get_consent_details(request, consent_id):
    """Получение детальной информации о согласии"""
    try:
        consent = get_object_or_404(
            PrivacyConsent,
            id=consent_id,
            user=request.user
        )
        
        if consent.data_categories:
            if isinstance(consent.data_categories, str):
                try:
                    data_categories = json.loads(consent.data_categories)
                except json.JSONDecodeError:
                    data_categories = consent.data_categories.split(',')
            else:
                data_categories = consent.data_categories
        else:
            data_categories = []
        
        if consent.third_parties:
            if isinstance(consent.third_parties, str):
                try:
                    third_parties = json.loads(consent.third_parties)
                except json.JSONDecodeError:
                    third_parties = [{"name": consent.third_parties}]
            else:
                third_parties = consent.third_parties
        else:
            third_parties = []
        
        if not isinstance(data_categories, list):
            data_categories = [str(data_categories)]
        
        if not isinstance(third_parties, list):
            third_parties = [str(third_parties)]
        
        expiration_date = None
        if hasattr(consent, 'get_expiration_date'):
            exp_date = consent.get_expiration_date()
            if exp_date:
                expiration_date = exp_date.strftime('%d.%m.%Y')
        
        data = {
            'id': consent.id,
            'consent_type': consent.get_consent_type_display(),
            'version': consent.version,
            'purpose': consent.purpose or '',
            'data_categories': data_categories,
            'third_parties': third_parties,
            'storage_period': consent.storage_period or '',
            'granted_at': consent.granted_at.strftime('%d.%m.%Y %H:%M'),
            'is_active': consent.is_active,
            'document_url': consent.document_url or '',
            'expiration_date': expiration_date or 'Не ограничен'
        }
        
        if consent.revoked_at:
            data['revoked_at'] = consent.revoked_at.strftime('%d.%m.%Y %H:%M')
        
        return JsonResponse({'success': True, 'consent': data})
        
    except Exception as e:
        logger.error(f'Ошибка получения деталей согласия: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

class DataPortabilityView(LoginRequiredMixin, TemplateView):
    """Экспорт персональных данных пользователя"""
    template_name = 'main/data_portability.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        user_data = {
            'account': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined,
                'last_login': user.last_login,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
            },
            'profile': {},
            'orders': [],
            'consents': [],
            'addresses': []
        }
        
        try:
            profile = UserProfile.objects.get(user=user)
            user_data['profile'] = {
                'phone': profile.phone,
                'company': profile.company,
                'position': profile.position,
                'date_of_birth': profile.date_of_birth,
                'privacy_mode': profile.privacy_mode,
                'email_verified': profile.email_verified,
                'phone_verified': profile.phone_verified,
            }
        except UserProfile.DoesNotExist:
            pass
        
        # Согласия
        consents = PrivacyConsent.objects.filter(user=user)
        user_data['consents'] = list(consents.values(
            'consent_type', 'version', 'is_active', 
            'granted_at', 'revoked_at', 'purpose'
        ))
        
        context['user_data'] = user_data
        context['export_date'] = timezone.now()
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Генерация JSON файла с данными"""
        import json
        from django.http import HttpResponse
        
        context = self.get_context_data()
        user_data = context['user_data']
        
        user_data['export_info'] = {
            'exported_at': timezone.now().isoformat(),
            'exported_by': request.user.username,
            'export_ip': request.META.get('REMOTE_ADDR'),
            'format': 'json'
        }
        
        json_data = json.dumps(user_data, default=str, indent=2, ensure_ascii=False)
        
        response = HttpResponse(json_data, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="personal_data_{request.user.username}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        SecurityLog.objects.create(
            user=request.user,
            action='data_export',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True,
            details={'format': 'json'},
            risk_level='low'
        )
        
        return response
    
@login_required
@require_POST
def toggle_newsletter_consent(request):
    """Включение/выключение согласия на рассылку"""
    try:
        consent, created = PrivacyConsent.objects.get_or_create(
            user=request.user,
            consent_type='newsletter',
            defaults={
                'version': '1.0',
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'is_active': True,
                'purpose': 'Отправка информационных и маркетинговых сообщений',
                'data_categories': ['Адрес электронной почты', 'Имя'],
                'third_parties': [
                    {
                        'name': 'Email-сервис',
                        'purpose': 'Отправка email-сообщений',
                        'country': 'Россия',
                        'legal_basis': 'Договор на оказание услуг'
                    }
                ],
                'storage_period': 'До отзыва согласия',
                'document_url': '/privacy/#marketing'
            }
        )
        
        if not created:
            consent.is_active = not consent.is_active
            if consent.is_active:
                consent.revoked_at = None
                action = 'activated'
            else:
                consent.revoked_at = timezone.now()
                action = 'deactivated'
            consent.save()
        else:
            action = 'created'
        
        # Логирование
        PrivacyConsentLog.objects.create(
            consent=consent,
            action=action,
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'previous_status': not consent.is_active if not created else None}
        )
        
        return JsonResponse({
            'success': True,
            'is_active': consent.is_active,
            'message': f'Рассылка {"включена" if consent.is_active else "отключена"}'
        })
        
    except Exception as e:
        logger.error(f'Ошибка переключения рассылки: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
def create_privacy_consent(user, consent_type, request=None, context_data=None):
    """Создание согласия на обработку персональных данных"""
    try:
        consent_configs = {
            'registration': {
                'version': '2.0',
                'purpose': 'Создание учетной записи и предоставление доступа к услугам',
                'data_categories': ['Email', 'Имя пользователя', 'Телефон', 'ФИО', 'Адрес'],
                'third_parties': [],
                'storage_period': 'Пока активна учетная запись + 5 лет после удаления',
                'document_url': '/privacy/#account'
            },
            'order': {
                'version': '2.0',
                'purpose': 'Оформление и обработка заказа, выставление счетов, доставка',
                'data_categories': ['ФИО', 'Email', 'Телефон', 'Адрес доставки', 'ИНН', 'КПП'],
                'third_parties': [
                    {
                        'name': 'Служба доставки',
                        'purpose': 'Доставка товаров',
                        'country': 'Россия',
                        'legal_basis': 'Договор на оказание услуг'
                    }
                ],
                'storage_period': '7 лет (требования налогового законодательства)',
                'document_url': '/privacy/#orders'
            },
            'marketing': {
                'version': '2.0',
                'purpose': 'Отправка маркетинговых материалов, новостей и специальных предложений',
                'data_categories': ['Email', 'Имя'],
                'third_parties': [
                    {
                        'name': 'Email-сервис',
                        'purpose': 'Отправка email-сообщений',
                        'country': 'Россия',
                        'legal_basis': 'Договор на оказание услуг'
                    }
                ],
                'storage_period': 'До отзыва согласия',
                'document_url': '/privacy/#marketing'
            },
            'support': {
                'version': '2.0',
                'purpose': 'Обработка обращений в службу поддержки',
                'data_categories': ['Email', 'ФИО', 'Телефон', 'Информация о проблеме'],
                'third_parties': [],
                'storage_period': '3 года с момента обращения',
                'document_url': '/privacy/#support'
            },
            'contact': {
                'version': '2.0',
                'purpose': 'Обработка обращений через форму контактов',
                'data_categories': ['Имя', 'Email', 'Телефон', 'Сообщение'],
                'third_parties': [],
                'storage_period': '3 года с момента обращения',
                'document_url': '/privacy/#contact'
            }
        }
        
        config = consent_configs.get(consent_type, {})
        
        ip_address = ''
        user_agent = ''
        
        if request:
            from .views import get_client_ip
            ip_address = get_client_ip(request) or ''
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        elif context_data:
            ip_address = context_data.get('ip_address', '')
            user_agent = context_data.get('user_agent', '')
        
        existing_consent = PrivacyConsent.objects.filter(
            user=user,
            consent_type=consent_type,
            is_active=True
        ).first()
        
        if existing_consent:
            return existing_consent
        
        consent = PrivacyConsent.objects.create(
            user=user,
            consent_type=consent_type,
            version=config.get('version', '1.0'),
            purpose=config.get('purpose', ''),
            data_categories=json.dumps(config.get('data_categories', [])),
            third_parties=json.dumps(config.get('third_parties', [])),
            storage_period=config.get('storage_period', ''),
            document_url=config.get('document_url', ''),
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            granted_at=timezone.now()
        )
        
        PrivacyConsentLog.objects.create(
            consent=consent,
            action='created',
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                'consent_type': consent_type,
                'context': context_data or {},
                'config': config
            }
        )
        
        try:
            profile = UserProfile.objects.get(user=user)
            profile.last_privacy_update = timezone.now()
            profile.save()
        except UserProfile.DoesNotExist:
            pass
        
        return consent
    
    except Exception as e:
        logger.error(f"Ошибка при создании согласия {consent_type}: {str(e)}")
        logger.debug(traceback.format_exc())
        raise  

def get_client_ip(request):
    """Получение IP-адреса клиента"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    if ip and ip != '' and ip != 'unknown':
        if '.' in ip or ':' in ip:
            return ip
    
    return None

def handle_privacy_request_error(request, error_message, template_name='main/privacy_request_error.html', context=None):
    """Обработчик ошибок для запросов по персональным данным"""
    if context is None:
        context = {}
    
    logger.error(f"Privacy request error: {error_message}")
    
    context['error'] = error_message
    context['company_email'] = 'info@tech-re.ru'
    
    try:
        SecurityLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action='privacy_request_error',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=False,
            details={'error': error_message},
            risk_level='medium'
        )
    except Exception as log_error:
        logger.warning(f"Не удалось создать SecurityLog: {str(log_error)}")
    
    return render(request, template_name, context, status=500)

def safe_log_notification(user, action, details=None):
    """Безопасное логирование уведомлений без вызова NotificationLog"""
    try:
        from django.apps import apps
        if apps.is_installed('main') and hasattr(apps.get_model('main', 'NotificationLog'), 'objects'):
            NotificationLog = apps.get_model('main', 'NotificationLog')
            if hasattr(NotificationLog, 'user'):
                NotificationLog.objects.create(
                    user=user,
                    action=action,
                    details=details or {}
                )
            else:
                NotificationLog.objects.create(
                    recipient=user,  # или другое поле
                    action=action,
                    details=details or {}
                )
        else:
            SecurityLog.objects.create(
                user=user,
                action=f'notification_{action}',
                ip_address='',
                user_agent='',
                success=True,
                details=details or {},
                risk_level='low'
            )
    except Exception as e:
        logger.warning(f"Не удалось залогировать уведомление: {str(e)}")