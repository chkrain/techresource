# -*- coding: utf-8 -*-

class PaymentMethodType:
    """
    Константы, представляющие значения payment_method_data. Возможные значения:

    * yookassa.domain.common.PaymentMethodType.YOO_MONEY
    * yookassa.domain.common.PaymentMethodType.BANK_CARD
    * yookassa.domain.common.PaymentMethodType.SBERBANK
    * yookassa.domain.common.PaymentMethodType.CASH
    * yookassa.domain.common.PaymentMethodType.MOBILE_BALANCE
    * yookassa.domain.common.PaymentMethodType.PSB
    * yookassa.domain.common.PaymentMethodType.QIWI
    * yookassa.domain.common.PaymentMethodType.WEBMONEY
    * yookassa.domain.common.PaymentMethodType.ALFABANK
    * yookassa.domain.common.PaymentMethodType.APPLEPAY
    * yookassa.domain.common.PaymentMethodType.GOOGLE_PAY
    * yookassa.domain.common.PaymentMethodType.INSTALMENTS
    * yookassa.domain.common.PaymentMethodType.B2B_SBERBANK
    * yookassa.domain.common.PaymentMethodType.TINKOFF_BANK
    * yookassa.domain.common.PaymentMethodType.WECHAT
    * yookassa.domain.common.PaymentMethodType.SBP
    * yookassa.domain.common.PaymentMethodType.SBER_LOAN
    * yookassa.domain.common.PaymentMethodType.ELECTRONIC_CERTIFICATE
    * yookassa.domain.common.PaymentMethodType.SBER_BNPL
    * yookassa.domain.common.PaymentMethodType.UNKNOWN
    """  # noqa: E501

    """
    Список допустимых значений
    """
    YOO_MONEY = 'yoo_money'
    """Платеж из кошелька ЮMoney"""
    BANK_CARD = 'bank_card'
    """Платеж с произвольной банковской карты"""
    SBERBANK = 'sberbank'
    """Платеж СбербанкОнлайн"""
    CASH = 'cash'
    """Платеж наличными"""
    MOBILE_BALANCE = 'mobile_balance'
    """Платеж с баланса мобильного телефона"""
    PSB = 'psb'
    """ПромсвязьБанк"""
    QIWI = 'qiwi'
    """Платеж из кошелька Qiwi"""
    WEBMONEY = 'webmoney'
    """Платеж из кошелька Webmoney"""
    ALFABANK = 'alfabank'
    """Платеж через Альфа-Клик"""
    APPLEPAY = 'apple_pay'
    """Платеж ApplePay"""
    GOOGLE_PAY = 'google_pay'
    """Платеж Google Pay"""
    INSTALMENTS = 'installments'
    """Заплатить по частям"""
    B2B_SBERBANK = 'b2b_sberbank'
    """Сбербанк Бизнес Онлайн"""
    TINKOFF_BANK = 'tinkoff_bank'
    """T-Pay"""
    WECHAT = 'wechat'
    """Оплата через WeChat"""
    SBP = 'sbp'
    """Оплата через сервис быстрых платежей"""
    SBER_LOAN = 'sber_loan'
    """Прием оплаты с использованием Кредита от СберБанка"""
    ELECTRONIC_CERTIFICATE = 'electronic_certificate'
    """Прием платежей по электронному сертификату, привязанному к карте «Мир»"""
    SBER_BNPL = 'sber_bnpl'
    """Прием платежей через сервис «Плати частями»"""
    UNKNOWN = 'unknown'
    """Для неизвестных методов оплаты"""
