# main/templatetags/query_transform.py
from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def update_query(context, **kwargs):
    from django.http import QueryDict
    import urllib.parse
    
    request = context.get('request')
    if not request:
        return ''
    
    query_dict = request.GET.copy()
    
    for key, value in kwargs.items():
        if value is None:
            if key in query_dict:
                del query_dict[key]
        else:
            query_dict[key] = value
    
    return query_dict.urlencode()