from django import template

register = template.Library()

@register.filter
def divide(value, arg):
    """Делит value на arg"""
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def reading_time(value):
    """Рассчитывает время чтения статьи"""
    try:
        words = len(value.split())
        minutes = max(1, words // 120)  # 120 слов в минуту
        return f"{minutes} мин. чтения"
    except:
        return "1 мин. чтения"