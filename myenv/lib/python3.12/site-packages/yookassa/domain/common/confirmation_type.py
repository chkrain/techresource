# -*- coding: utf-8 -*-


class ConfirmationType:
    """
    Константы, представляющие тип пользовательского процесса подтверждения платежа. Возможные значения:

    * yookassa.domain.common.ConfirmationType.EXTERNAL
    * yookassa.domain.common.ConfirmationType.REDIRECT
    * yookassa.domain.common.ConfirmationType.EMBEDDED
    * yookassa.domain.common.ConfirmationType.QR
    * yookassa.domain.common.ConfirmationType.MOBILE_APPLICATION
    """  # noqa: E501

    """
    Список допустимых значений
    """
    EMBEDDED = 'embedded'
    """Необходимо получить одноразовый код от плательщика для подтверждения платежа"""
    EXTERNAL = 'external'
    """Для подтверждения платежа пользователю необходимо совершить действия во внешней системе (например, ответить на смс)"""
    REDIRECT = 'redirect'
    """Необходимо направить плательщика на страницу партнера"""
    QR = 'qr'
    """Необходимо получить QR-код"""
    MOBILE_APPLICATION = 'mobile_application'
    """Необходимо совершить действия в мобильном приложении"""
