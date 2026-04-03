# main/templatetags/number_filters.py
from django import template

register = template.Library()

@register.filter
def number_to_words(num):
    """Преобразует число в сумму прописью"""
    if not num:
        return 'Ноль рублей 00 копеек'
    
    rubles = int(num)
    kopecks = int(round((num - rubles) * 100))
    
    # Словари для склонения
    units = ['', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']
    units_female = ['', 'одна', 'две', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']
    tens = ['', 'десять', 'двадцать', 'тридцать', 'сорок', 'пятьдесят', 
            'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто']
    hundreds = ['', 'сто', 'двести', 'триста', 'четыреста', 'пятьсот',
                'шестьсот', 'семьсот', 'восемьсот', 'девятьсот']
    teens = ['десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать',
             'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать']
    
    def convert_group(n, is_female=False):
        if n == 0:
            return ''
        result = ''
        n_str = str(n).zfill(3)
        h = int(n_str[0])
        t = int(n_str[1])
        u = int(n_str[2])
        
        if h > 0:
            result += hundreds[h] + ' '
        
        if t == 1:
            result += teens[u] + ' '
        else:
            if t > 1:
                result += tens[t] + ' '
            if u > 0:
                if is_female:
                    result += units_female[u] + ' '
                else:
                    result += units[u] + ' '
        return result.strip()
    
    def get_ruble_word(n):
        last_digit = n % 10
        last_two = n % 100
        if 11 <= last_two <= 19:
            return 'рублей'
        if last_digit == 1:
            return 'рубль'
        if 2 <= last_digit <= 4:
            return 'рубля'
        return 'рублей'
    
    def get_kopeck_word(n):
        if n == 1:
            return 'копейка'
        if 2 <= n <= 4:
            return 'копейки'
        return 'копеек'
    
    # Миллионы
    millions = rubles // 1000000
    thousands = (rubles % 1000000) // 1000
    rest = rubles % 1000
    
    words = []
    
    if millions > 0:
        words.append(convert_group(millions, False))
        last_digit = millions % 10
        last_two = millions % 100
        if 11 <= last_two <= 19:
            words.append('миллионов')
        elif last_digit == 1:
            words.append('миллион')
        elif 2 <= last_digit <= 4:
            words.append('миллиона')
        else:
            words.append('миллионов')
    
    if thousands > 0:
        words.append(convert_group(thousands, True))
        last_digit = thousands % 10
        last_two = thousands % 100
        if 11 <= last_two <= 19:
            words.append('тысяч')
        elif last_digit == 1:
            words.append('тысяча')
        elif 2 <= last_digit <= 4:
            words.append('тысячи')
        else:
            words.append('тысяч')
    
    if rest > 0 or rubles == 0:
        if rest > 0:
            words.append(convert_group(rest, False))
        else:
            words.append('ноль')
    
    words.append(get_ruble_word(rubles))
    
    if kopecks > 0:
        words.append(f'{kopecks:02d}')
        words.append(get_kopeck_word(kopecks))
    else:
        words.append('00')
        words.append('копеек')
    
    result = ' '.join(words)
    return result[0].upper() + result[1:]