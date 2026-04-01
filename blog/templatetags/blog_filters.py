from django import template
from urllib.parse import urlparse

register = template.Library()

@register.filter
def divide(value, arg):
    """Делит value на arg"""
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def replace(value, arg):
    """Замена строки в строке"""
    old, new = arg.split(',')
    return value.replace(old, new)

@register.filter
def reading_time(text):
    """Вычисление времени чтения"""
    words = len(text.split())
    minutes = max(1, words // 80)
    return f"{minutes} мин. чтения"