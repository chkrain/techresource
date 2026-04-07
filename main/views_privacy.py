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
from .forms import ConsentForm

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
                    recipient=user,
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

def process_detailed_consent(request):
    """
    Обработка подробного согласия на обработку персональных данных
    с использованием формы ConsentForm
    """
    if request.method == 'POST':
        form = ConsentForm(request.POST)
        
        if form.is_valid():
            try:
                cleaned_data = form.cleaned_data
                
                ip_address = get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
                
                email = cleaned_data['email']
                
                from django.contrib.auth.models import User
                user = None
                
                if request.user.is_authenticated:
                    user = request.user
                else:
                    try:
                        user = User.objects.get(email=email)
                    except User.DoesNotExist:
                        user = None
                
                existing_consent = None
                if user:
                    existing_consent = PrivacyConsent.objects.filter(
                        user=user,
                        consent_type='detailed_consent',
                        version='1.0'  
                    ).first()
                
                data_categories = [
                    "Фамилия, имя, отчество",
                    "Контактные данные (email, телефон)",
                    "Адрес доставки/юридический адрес", 
                    "Реквизиты организации (ИНН, КПП, наименование)",
                    "Прикрепляемые файлы (технические задания, реквизиты)"
                ]
                
                third_parties = []
                
                if cleaned_data['transfer_unlimited'] == 'not_prohibited':
                    third_parties.append({
                        'type': 'unlimited_circle',
                        'name': 'Неограниченный круг лиц',
                        'purpose': 'Публикация отзывов, реклама, партнерские программы',
                        'legal_basis': 'Согласие субъекта ПД'
                    })
                
                processing_option = cleaned_data['processing_unlimited']
                if processing_option != 'prohibited':
                    restrictions = []
                    
                    if processing_option == 'not_prohibited_with_conditions':
                        prohibited_actions = cleaned_data.get('prohibited_actions', [])
                        if prohibited_actions:
                            restrictions.append(f"Запрещенные действия: {', '.join(prohibited_actions)}")
                    
                    third_parties.append({
                        'type': 'processing_unlimited',
                        'name': 'Неограниченный круг лиц для обработки',
                        'restrictions': restrictions,
                        'legal_basis': 'Согласие субъекта ПД'
                    })
                
                network_transfer = cleaned_data['network_transfer']
                
                purposes = [
                    "Обработка персональных данных для предоставления услуг компании",
                    "Идентификация пользователя при обращении в службу поддержки",
                    "Выполнение обязательств по договорам и соглашениям",
                    "Соблюдение требований законодательства РФ"
                ]
                
                if cleaned_data.get('marketing_consent'):
                    purposes.append("Отправка маркетинговых и информационных сообщений")
                
                if cleaned_data['transfer_unlimited'] == 'not_prohibited':
                    purposes.append("Передача данных неограниченному кругу лиц для публичных целей")
                
                purpose = "\n".join(purposes)
                
                if existing_consent:
                    existing_consent.ip_address = ip_address
                    existing_consent.user_agent = user_agent
                    existing_consent.purpose = purpose
                    existing_consent.data_categories = data_categories
                    existing_consent.third_parties = third_parties
                    existing_consent.is_active = True
                    existing_consent.revoked_at = None  # Снимаем отзыв если был
                    existing_consent.save()
                    consent = existing_consent
                    
                    action_type = 'updated'
                else:
                    consent = PrivacyConsent.objects.create(
                        user=user,
                        consent_type='detailed_consent',
                        version='1.0',
                        ip_address=ip_address,
                        user_agent=user_agent,
                        is_active=True,
                        granted_at=timezone.now(),
                        purpose=purpose,
                        data_categories=data_categories,
                        third_parties=third_parties,
                        storage_period='5 лет (требования законодательства РФ)',
                        document_url='/privacy/detailed-consent/'
                    )
                    action_type = 'created'
                
                consent_details = {
                    'transfer_unlimited': cleaned_data['transfer_unlimited'],
                    'processing_unlimited': cleaned_data['processing_unlimited'],
                    'prohibited_actions': cleaned_data.get('prohibited_actions', []),
                    'network_transfer': network_transfer,
                    'marketing_consent': cleaned_data.get('marketing_consent', False),
                    'phone': cleaned_data.get('phone', ''),
                    'submitted_email': email,
                    'form_type': 'detailed_consent_v1',
                    'action': action_type
                }
                
                PrivacyConsentLog.objects.create(
                    consent=consent,
                    action=action_type,
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details=consent_details
                )
                
                if cleaned_data.get('marketing_consent'):
                    marketing_consent, created = PrivacyConsent.objects.get_or_create(
                        user=user,
                        consent_type='marketing',
                        version='1.0',
                        defaults={
                            'ip_address': ip_address,
                            'user_agent': user_agent,
                            'is_active': True,
                            'purpose': 'Отправка маркетинговых и информационных сообщений',
                            'data_categories': ['Адрес электронной почты', 'Имя', 'Телефон'],
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
                        marketing_consent.is_active = True
                        marketing_consent.revoked_at = None
                        marketing_consent.save()
                
                try:
                    SecurityLog.objects.create(
                        user=user,
                        action=f'detailed_consent_{action_type}',
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=True,
                        details={
                            'consent_id': str(consent.id),
                            'email': email,
                            'action': action_type
                        },
                        risk_level='low'
                    )
                except Exception as log_error:
                    logger.warning(f"Ошибка при создании SecurityLog: {str(log_error)}")
                
                messages.success(request, f'Ваше подробное согласие успешно {action_type}.')
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Подробное согласие успешно {action_type}',
                        'consent_id': consent.id,
                        'redirect_url': reverse_lazy('consent_success_detailed')
                    })
                
                return redirect('consent_success_detailed')
                
            except Exception as e:
                logger.error(f'Ошибка при сохранении подробного согласия: {str(e)}')
                logger.debug(traceback.format_exc())
                
                error_message = f'Произошла ошибка при сохранении данных: {str(e)}'
                form.add_error(None, error_message)
                
                try:
                    SecurityLog.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        action='detailed_consent_error',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        success=False,
                        details={'error': str(e)},
                        risk_level='high'
                    )
                except Exception as log_error:
                    logger.warning(f"Ошибка при создании SecurityLog для ошибки: {str(log_error)}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_message
                    }, status=500)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
    else:
        form = ConsentForm()
        
        if request.user.is_authenticated:
            form.fields['email'].initial = request.user.email
    
    return render(request, 'main/privacy_documents.html', {
        'form': form,
        'title': 'Подробное согласие на обработку ПД'
    })


def russian_ending(action_type):
    """Вспомогательная функция для русских окончаний"""
    if action_type == 'created':
        return 'создано'
    elif action_type == 'updated':
        return 'обновлено'
    return action_type

def get_detailed_consent_purpose(form_data):
    """Формирование цели обработки на основе выбранных параметров"""
    purposes = [
        "Обработка персональных данных для предоставления услуг компании",
        "Идентификация пользователя при обращении в службу поддержки",
        "Выполнение обязательств по договорам и соглашениям",
        "Соблюдение требований законодательства РФ"
    ]
    
    if form_data.get('marketing_consent'):
        purposes.append("Отправка маркетинговых и информационных сообщений")
    
    if form_data['transfer_unlimited'] == 'not_prohibited':
        purposes.append("Передача данных неограниченному кругу лиц для публичных целей")
    
    return "\n".join(purposes)


def create_detailed_marketing_consent(user, email, ip_address, user_agent, form_data):
    """Создание маркетингового согласия из подробной формы"""
    try:
        from django.contrib.auth.models import User
        consent_user = user
        
        if not consent_user and email:
            try:
                consent_user = User.objects.get(email=email)
            except User.DoesNotExist:
                consent_user = None
        
        marketing_consent_data = {
            'version': '3.0',
            'purpose': 'Отправка маркетинговых и информационных сообщений',
            'data_categories': ['Адрес электронной почты', 'Имя', 'Телефон'],
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
        
        existing_marketing_consent = None
        if consent_user:
            existing_marketing_consent = PrivacyConsent.objects.filter(
                user=consent_user,
                consent_type='marketing',
                is_active=True
            ).first()
        
        if existing_marketing_consent:
            existing_marketing_consent.version = marketing_consent_data['version']
            existing_marketing_consent.purpose = marketing_consent_data['purpose']
            existing_marketing_consent.save()
            
            PrivacyConsentLog.objects.create(
                consent=existing_marketing_consent,
                action='updated_from_detailed',
                user=consent_user,
                ip_address=ip_address,
                user_agent=user_agent,
                details={'source': 'detailed_consent_form'}
            )
            
            return existing_marketing_consent
        else:
            # Создаем новое согласие
            marketing_consent = PrivacyConsent.objects.create(
                user=consent_user,
                consent_type='marketing',
                version=marketing_consent_data['version'],
                ip_address=ip_address,
                user_agent=user_agent,
                is_active=True,
                granted_at=timezone.now(),
                purpose=marketing_consent_data['purpose'],
                data_categories=marketing_consent_data['data_categories'],
                third_parties=marketing_consent_data['third_parties'],
                storage_period=marketing_consent_data['storage_period'],
                document_url=marketing_consent_data['document_url']
            )
            
            PrivacyConsentLog.objects.create(
                consent=marketing_consent,
                action='created',
                user=consent_user,
                ip_address=ip_address,
                user_agent=user_agent,
                details={'source': 'detailed_consent_form'}
            )
            
            return marketing_consent
            
    except Exception as e:
        logger.error(f'Ошибка при создании маркетингового согласия: {str(e)}')
        return None


class ConsentSuccessDetailedView(TemplateView):
    """Страница успешного сохранения подробного согласия"""
    template_name = 'main/consent_success_detailed.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем последнее согласие пользователя
        if self.request.user.is_authenticated:
            latest_consent = PrivacyConsent.objects.filter(
                user=self.request.user,
                consent_type='detailed_consent'
            ).order_by('-granted_at').first()
            
            if latest_consent:
                context['latest_consent'] = latest_consent
                context['consent_date'] = latest_consent.granted_at.strftime('%d.%m.%Y %H:%M')
        
        return context


@login_required
def detailed_consents_list(request):
    """Список подробных согласий пользователя"""
    consents = PrivacyConsent.objects.filter(
        user=request.user,
        consent_type='detailed_consent'
    ).order_by('-granted_at')
    
    return render(request, 'main/detailed_consents_list.html', {
        'consents': consents,
        'title': 'Мои подробные согласия'
    })


@login_required
def get_detailed_consent_info(request, consent_id):
    """Получение детальной информации о подробном согласии"""
    try:
        consent = get_object_or_404(
            PrivacyConsent,
            id=consent_id,
            user=request.user,
            consent_type='detailed_consent'
        )
        
        form_details = {}
        try:
            consent_log = PrivacyConsentLog.objects.filter(
                consent=consent,
                action='created'
            ).first()
            
            if consent_log and consent_log.details:
                form_details = consent_log.details
        except:
            pass
        
        data = {
            'id': consent.id,
            'consent_type': 'Подробное согласие',
            'version': consent.version,
            'purpose': consent.purpose or '',
            'data_categories': consent.data_categories if isinstance(consent.data_categories, list) else [],
            'third_parties': consent.third_parties if isinstance(consent.third_parties, list) else [],
            'storage_period': consent.storage_period or '',
            'granted_at': consent.granted_at.strftime('%d.%m.%Y %H:%M'),
            'is_active': consent.is_active,
            'document_url': consent.document_url or '',
            'form_details': form_details
        }
        
        return JsonResponse({'success': True, 'consent': data})
        
    except Exception as e:
        logger.error(f'Ошибка получения деталей подробного согласия: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def create_detailed_privacy_consent(user, request=None, context_data=None):
    """Создание подробного согласия на обработку персональных данных"""
    try:
        existing_consent = PrivacyConsent.objects.filter(
            user=user,
            consent_type='detailed_consent',
            is_active=True
        ).first()
        
        if existing_consent:
            return existing_consent
        
        config = {
            'version': '3.0',
            'purpose': 'Комплексная обработка персональных данных с учетом пользовательских предпочтений',
            'data_categories': [
                'ФИО', 'Email', 'Телефон', 'Адрес',
                'Данные организации', 'Файлы и документы'
            ],
            'third_parties': [],
            'storage_period': '5 лет (требования законодательства РФ)',
            'document_url': '/privacy/detailed-consent/'
        }
        
        ip_address = ''
        user_agent = ''
        
        if request:
            ip_address = get_client_ip(request) or ''
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        elif context_data:
            ip_address = context_data.get('ip_address', '')
            user_agent = context_data.get('user_agent', '')
        
        consent = PrivacyConsent.objects.create(
            user=user,
            consent_type='detailed_consent',
            version=config.get('version', '3.0'),
            purpose=config.get('purpose', ''),
            data_categories=config.get('data_categories', []),
            third_parties=config.get('third_parties', []),
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
                'consent_type': 'detailed_consent',
                'context': context_data or {},
                'config': config
            }
        )
        
        try:
            profile = UserProfile.objects.get(user=user)
            profile.last_privacy_update = timezone.now()
            profile.has_detailed_consent = True
            profile.detailed_consent_date = timezone.now()
            profile.save()
        except UserProfile.DoesNotExist:
            pass
        
        return consent
    
    except Exception as e:
        logger.error(f"Ошибка при создании подробного согласия: {str(e)}")
        logger.debug(traceback.format_exc())
        raise