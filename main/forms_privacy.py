# main/forms_privacy.py
from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe

class PrivacyConsentCheckbox(forms.CheckboxInput):
    def __init__(self, consent_type='general', *args, **kwargs):
        self.consent_type = consent_type
        super().__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.update({
            'class': 'form-check-input privacy-consent',
            'data-consent-type': self.consent_type,
            'required': 'required'
        })
        return super().render(name, value, attrs, renderer)

class PrivacyConsentField(forms.BooleanField):
    """Поле для чекбокса согласия на обработку персональных данных"""
    
    CONSENT_TEXTS = {
        'registration': mark_safe('''
            <div class="privacy-consent-text">
                <strong>Согласие на обработку персональных данных</strong>
                <small class="text-muted d-block mt-1">
                    Нажимая на кнопку "Зарегистрироваться", я даю согласие на обработку моих персональных данных 
                    в соответствии с <a href="/privacy/" target="_blank" class="privacy-link">Политикой конфиденциальности</a>.<br>
                    Обрабатываемые данные: имя пользователя, email, телефон, ФИО. 
                    Цель обработки: создание учетной записи и предоставление услуг.
                    Срок хранения: пока активна учетная запись + 5 лет после удаления.
                </small>
            </div>
        '''),
        'order': mark_safe('''
            <div class="privacy-consent-text">
                <strong>Согласие на обработку персональных данных для оформления заказа</strong>
                <small class="text-muted d-block mt-1">
                    Я даю согласие на обработку моих персональных данных для оформления и обработки заказа.<br>
                    Обрабатываемые данные: ФИО, email, телефон, адрес доставки, ИНН/КПП.
                    Цель: оформление заказа, выставление счетов, доставка.
                    Срок хранения: 7 лет (требования налогового законодательства).
                    <a href="/privacy/" target="_blank" class="privacy-link">Подробнее в Политике конфиденциальности</a>
                </small>
            </div>
        '''),
        'support': mark_safe('''
            <div class="privacy-consent-text">
                <strong>Согласие на обработку персональных данных для обращения в поддержку</strong>
                <small class="text-muted d-block mt-1">
                    Я даю согласие на обработку моих персональных данных для обработки обращения в службу поддержки.<br>
                    Обрабатываемые данные: имя, email, телефон, информация о проблеме.
                    Цель: обработка обращения в службу поддержки.
                    Срок хранения: 3 года с момента обращения.
                </small>
            </div>
        '''),
        'contact': mark_safe('''
            <div class="privacy-consent-text">
                <strong>Согласие на обработку персональных данных для обратной связи</strong>
                <small class="text-muted d-block mt-1">
                    Я даю согласие на обработку моих персональных данных для обратной связи.<br>
                    Обрабатываемые данные: имя, email, телефон, сообщение.
                    Цель: обработка обратной связи.
                    Срок хранения: 3 года с момента обращения.
                </small>
            </div>
        '''),
        'newsletter': mark_safe('''
            <div class="privacy-consent-text">
                <strong>Согласие на получение рассылки</strong>
                <small class="text-muted d-block mt-1">
                    Я даю согласие на получение информационных и маркетинговых материалов по email.<br>
                    Обрабатываемые данные: email, имя.
                    Цель: отправка новостей, акций и специальных предложений.
                    Срок хранения: до отзыва согласия.
                </small>
            </div>
        ''')
    }
    
    def __init__(self, consent_type='registration', *args, **kwargs):
        self.consent_type = consent_type
        label = self.CONSENT_TEXTS.get(consent_type, self.CONSENT_TEXTS['registration'])
        
        kwargs.update({
            'required': True,
            'label': label,
            'widget': PrivacyConsentCheckbox(consent_type=consent_type),
            'error_messages': {
                'required': 'Вы должны дать согласие на обработку персональных данных'
            }
        })
        super().__init__(*args, **kwargs)

class RegistrationPrivacyField(PrivacyConsentField):
    def __init__(self, *args, **kwargs):
        super().__init__(consent_type='registration', *args, **kwargs)

class OrderPrivacyField(PrivacyConsentField):
    def __init__(self, *args, **kwargs):
        super().__init__(consent_type='order', *args, **kwargs)

class SupportPrivacyField(PrivacyConsentField):
    def __init__(self, *args, **kwargs):
        super().__init__(consent_type='support', *args, **kwargs)

class ContactPrivacyField(PrivacyConsentField):
    def __init__(self, *args, **kwargs):
        super().__init__(consent_type='contact', *args, **kwargs)

class NewsletterPrivacyField(PrivacyConsentField):
    def __init__(self, *args, **kwargs):
        kwargs['required'] = False 
        super().__init__(consent_type='newsletter', *args, **kwargs)