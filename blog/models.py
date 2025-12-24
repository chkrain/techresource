from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
import re
from django.core.exceptions import ValidationError
from django.utils.html import escape
import re
from datetime import datetime

class BlogCategory(models.Model):
    """Категории статей блога"""
    name = models.CharField(max_length=100, verbose_name="Название")
    slug = models.SlugField(unique=True, verbose_name="URL")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    order = models.IntegerField(default=0, verbose_name="Порядок")
    seo_title = models.CharField(max_length=200, blank=True, verbose_name="SEO Title")
    seo_description = models.TextField(blank=True, verbose_name="SEO Description")
    seo_keywords = models.TextField(blank=True, verbose_name="SEO Keywords")
    
    class Meta:
        verbose_name = "Категория блога"
        verbose_name_plural = "Категории блога"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('blog:blog_category', kwargs={'slug': self.slug}) 
    
    def get_article_count(self):
        return self.articles.count()

class BlogArticle(models.Model):
    """Статья блога"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('review', 'На проверке'),
        ('published', 'Опубликовано'),
        ('archived', 'В архиве'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    slug = models.SlugField(unique=True, verbose_name="URL")
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Автор")
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, 
                                null=True, blank=True, verbose_name="Категория",
                                related_name='articles')
    
    excerpt = models.TextField(verbose_name="Краткое описание", max_length=500)
    content = models.TextField(verbose_name="Содержание")
    
    meta_title = models.CharField(max_length=200, blank=True, verbose_name="Meta Title")
    meta_description = models.TextField(blank=True, verbose_name="Meta Description")
    meta_keywords = models.TextField(blank=True, verbose_name="Meta Keywords")
    
    featured_image = models.ImageField(upload_to='blog/featured/%Y/%m/', blank=True, null=True, 
                                      verbose_name="Главное изображение")
    thumbnail = models.ImageField(upload_to='blog/thumbnails/%Y/%m/', blank=True, null=True,
                                 verbose_name="Миниатюра")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', 
                             verbose_name="Статус")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата публикации")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    views = models.PositiveIntegerField(default=0, verbose_name="Просмотры")
    likes = models.PositiveIntegerField(default=0, verbose_name="Лайки")
    
    is_featured = models.BooleanField(default=False, verbose_name="Рекомендуемая")
    allow_comments = models.BooleanField(default=True, verbose_name="Разрешить комментарии")
    
    tags = models.CharField(max_length=500, blank=True, verbose_name="Теги", 
                           help_text="Через запятую")
    
    last_edited_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='edited_articles',
        verbose_name="Последний редактор"
    )
    edit_reason = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name="Причина редактирования"
    )
    is_verified = models.BooleanField(
        default=False, 
        verbose_name="Проверено модератором"
    )

    class Meta:
        verbose_name = "Статья блога"
        verbose_name_plural = "Статьи блога"
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['category', 'published_at']),
            models.Index(fields=['author', 'published_at']),
            models.Index(fields=['status', 'is_featured', 'published_at']),
            models.Index(fields=['slug', 'status']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()

        if self.excerpt:
            self.excerpt = escape(self.excerpt)

        if self.content:
            import bleach
            allowed_tags = ['p', 'br', 'b', 'i', 'strong', 'em', 'ul', 'ol', 'li', 'a']
            allowed_attributes = {'a': ['href', 'title']}
            self.content = bleach.clean(self.content, tags=allowed_tags, attributes=allowed_attributes)
        
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while BlogArticle.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('blog:blog_article', kwargs={'slug': self.slug})
    
    def get_tags_list(self):
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []
    
    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])

    def clean(self):
        """Валидация перед сохранением"""
        if '<script>' in self.content.lower():
            raise ValidationError('Контент содержит опасные теги')
        
        if len(self.title.strip()) < 5:
            raise ValidationError('Заголовок слишком короткий')
        
        if self.tags:
            tags_list = self.get_tags_list()
            if len(tags_list) > 10:
                raise ValidationError('Не более 10 тегов')
            for tag in tags_list:
                if len(tag) > 50:
                    raise ValidationError(f'Тег "{tag}" слишком длинный')

    def get_author_profile_url(self):
        """Получить URL профиля автора"""
        if hasattr(self.author, 'userprofile'):
            return self.author.userprofile.get_absolute_url()
        return None
    
    def get_author_avatar(self):
        """Получить аватар автора"""
        if hasattr(self.author, 'userprofile') and self.author.userprofile.avatar_small:
            return self.author.userprofile.avatar_small.url
        return None

class BlogComment(models.Model):
    """Комментарии к статьям блога"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает модерации'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонен'),  
        ('spam', 'Спам'),
        ('deleted', 'Удален'),
    ]
    
    article = models.ForeignKey(BlogArticle, on_delete=models.CASCADE, 
                               related_name='comments', verbose_name="Статья")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='replies', verbose_name="Родительский комментарий")
    
    content = models.TextField(verbose_name="Комментарий", max_length=2000)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending',
                             verbose_name="Статус")
    is_edited = models.BooleanField(default=False, verbose_name="Редактировался")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес", null=True)
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    
    likes = models.PositiveIntegerField(default=0, verbose_name="Лайки")

    edited_at = models.DateTimeField(null=True, blank=True, verbose_name="Время редактирования")
    edit_count = models.PositiveIntegerField(default=0, verbose_name="Количество правок")
    is_highlighted = models.BooleanField(default=False, verbose_name="Выделенный комментарий")
    moderation_notes = models.TextField(blank=True, verbose_name="Заметки модератора")
    moderated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='moderated_blog_comments',
        verbose_name="Модератор"
    )
    moderated_at = models.DateTimeField(null=True, blank=True, verbose_name="Время модерации")
    
    def can_edit(self, user):
        """Проверка возможности редактирования"""
        if user.is_superuser:
            return True
        if user == self.user:
            time_limit = timezone.now() - datetime.timedelta(minutes=30)
            return self.created_at > time_limit and self.edit_count < 3
        return False

    class Meta:
        verbose_name = "Комментарий блога"
        verbose_name_plural = "Комментарии блога"
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['article', 'status', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"Комментарий от {self.user.username} к {self.article.title}"

    def get_user_profile_url(self):
        """Получить URL профиля пользователя"""
        if hasattr(self.user, 'userprofile'):
            return self.user.userprofile.get_absolute_url()
        return None
    
    def get_user_avatar(self):
        """Получить аватар пользователя"""
        if hasattr(self.user, 'userprofile') and self.user.userprofile.avatar_small:
            return self.user.userprofile.avatar_small.url
        return None