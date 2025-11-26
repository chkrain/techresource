from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Вычитает arg из value"""
    return value - arg