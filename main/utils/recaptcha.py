import requests
from django.conf import settings
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

def verify_recaptcha_v2(recaptcha_response, remote_ip=None):
    """
    Проверка reCAPTCHA v2 (флажок)
    
    Args:
        recaptcha_response: Токен из формы
        remote_ip: IP пользователя (опционально)
    
    Returns:
        bool: True если проверка пройдена
    Raises:
        ValidationError: Если проверка не пройдена
    """
    if not recaptcha_response:
        raise ValidationError('Пожалуйста, подтвердите, что вы не робот')
    
    if settings.DEBUG and recaptcha_response == 'TEST_TOKEN':
        logger.debug("Используется тестовый токен reCAPTCHA")
        return True
    
    data = {
        'secret': settings.RECAPTCHA_PRIVATE_KEY,
        'response': recaptcha_response,
    }
    
    if remote_ip:
        data['remoteip'] = remote_ip
    
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data=data,
            timeout=10
        )
        result = response.json()
        
        logger.debug(f"reCAPTCHA response: {result}")
        
        if not result.get('success'):
            error_codes = result.get('error-codes', [])
            error_map = {
                'missing-input-secret': 'Отсутствует секретный ключ',
                'invalid-input-secret': 'Неверный секретный ключ',
                'missing-input-response': 'Не получен ответ от reCAPTCHA',
                'invalid-input-response': 'Неверный ответ reCAPTCHA',
                'bad-request': 'Неверный запрос',
                'timeout-or-duplicate': 'Истекло время или повторный запрос',
            }
            error_message = '; '.join([error_map.get(code, code) for code in error_codes])
            raise ValidationError(f'Ошибка проверки безопасности: {error_message}')
        
        return True
        
    except requests.Timeout:
        logger.error("Таймаут при проверке reCAPTCHA")
        raise ValidationError('Таймаут при проверке. Попробуйте ещё раз.')
    except requests.RequestException as e:
        logger.error(f"Ошибка сети при проверке reCAPTCHA: {e}")
        raise ValidationError('Ошибка сети. Попробуйте позже.')