# techresource

## source myenv/bin/activate pip install -r requirenments.txt для установки зависимостей. 
### Для создания и применения миграций - python manage.py makemigrations, python manage.py migrate
### Для запуска сервера - python manage.py runserver

## БД либо переносится, либо создается снова. 

### Чистить кеш браузера при ошибках стилизации

### Переделать в вебп с сохранением качества в 85%
# python manage.py optimize_images --quality 85 --verbose 
### Обновить шаблоны на переделанные в вебп изображения
# python manage.py update_template_images