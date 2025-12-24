# main/validators.py
from django.core.exceptions import ValidationError
from PIL import Image
import os

def validate_avatar(value):
    """Валидатор для аватара"""
    max_size = 5 * 1024 * 1024  
    if value.size > max_size:
        raise ValidationError(f'Размер файла не должен превышать 5MB')
    
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(f'Недопустимый формат файла. Допустимы: {", ".join(valid_extensions)}')
    
    try:
        img = Image.open(value)
        
        min_size = 100
        max_size = 2000
        if img.width < min_size or img.height < min_size:
            raise ValidationError(f'Минимальный размер изображения: {min_size}x{min_size}px')
        
        if img.width > max_size or img.height > max_size:
            raise ValidationError(f'Максимальный размер изображения: {max_size}x{max_size}px')
        
        if ext == '.gif':
            try:
                img.seek(1)
                raise ValidationError('Анимированные GIF не поддерживаются')
            except EOFError:
                pass  
        
        if img.mode in ('RGBA', 'LA') and ext in ('.jpg', '.jpeg'):
            raise ValidationError('JPEG не поддерживает прозрачность')
    
    except Exception as e:
        raise ValidationError(f'Ошибка при обработке изображения: {str(e)}')

def validate_profile_background(value):
    """Валидатор для фона профиля"""
    max_size = 10 * 1024 * 1024  # 10MB
    if value.size > max_size:
        raise ValidationError(f'Размер файла не должен превышать 10MB')
    
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(f'Недопустимый формат файла. Допустимы: {", ".join(valid_extensions)}')
    
    try:
        img = Image.open(value)
        
        if img.width / img.height < 1.5:  
            raise ValidationError('Рекомендуемое соотношение сторон для фона: 16:9')
        
        if img.width < 800 or img.height < 400:
            raise ValidationError('Минимальный размер фона: 800x400px')
    
    except Exception as e:
        raise ValidationError(f'Ошибка при обработке фона: {str(e)}')