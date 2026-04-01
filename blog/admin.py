from django import forms
from django.contrib import admin
from .models import BlogCategory, BlogArticle, BlogComment, ArticleContentBlock
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.forms import ModelForm

# Добавляем кастомную форму для статьи
class BlogArticleForm(ModelForm):
    class Meta:
        model = BlogArticle
        fields = '__all__'
    
    def clean(self):
        """Убираем валидацию content, так как оно скрыто"""
        cleaned_data = super().clean()
        # Не проверяем content, так как он не используется
        return cleaned_data

class ArticleContentBlockForm(ModelForm):
    """Форма для блоков контента с правильной обработкой изображений"""
    class Meta:
        model = ArticleContentBlock
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        block_type = cleaned_data.get('block_type')
        
        if block_type == 'text':
            if not cleaned_data.get('text_content'):
                raise ValidationError('Текстовый блок не может быть пустым')
        elif block_type == 'image':
            # Не проверяем image здесь, так как оно может быть загружено позже
            pass
        
        return cleaned_data

class ArticleContentBlockInline(admin.TabularInline):
    """Исправленный inline для блоков контента"""
    model = ArticleContentBlock
    form = ArticleContentBlockForm
    extra = 1
    
    fields = ('order', 'block_type', 'title', 'text_content', 'image', 'caption')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        
        # Делаем поля необязательными
        formset.form.base_fields['text_content'].required = False
        formset.form.base_fields['image'].required = False
        
        return formset
    
    class Media:
        css = {
            'all': ('admin/css/blog_blocks.css',)
        }
        js = ('admin/js/blog_content_blocks.js',)

@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'order', 'article_count']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    
    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = 'Статей'

@admin.register(BlogArticle)
class BlogArticleAdmin(admin.ModelAdmin):
    form = BlogArticleForm  # Используем кастомную форму
    list_display = ['title', 'author', 'category', 'status', 'published_at', 
                   'views', 'is_featured', 'thumbnail_preview']
    list_filter = ['status', 'category', 'author', 'published_at', 'is_featured']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['status', 'is_featured']
    readonly_fields = ['views', 'likes', 'created_at', 'updated_at', 'thumbnail_preview']
    date_hierarchy = 'published_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'slug', 'author', 'category', 'tags')
        }),
        ('Аннотация и миниатюра', {
            'fields': ('excerpt', 'featured_image', 'thumbnail')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Статус и настройки', {
            'fields': ('status', 'published_at', 'is_featured', 'allow_comments')
        }),
        ('Статистика', {
            'fields': ('views', 'likes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ArticleContentBlockInline]
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 5px;" />', 
                obj.thumbnail.url
            )
        return "—"
    thumbnail_preview.short_description = 'Миниатюра'
    
    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        
        # Сохраняем статью
        super().save_model(request, obj, form, change)
        
        # Принудительно сохраняем все связанные блоки
        if hasattr(obj, 'content_blocks'):
            for block in obj.content_blocks.all():
                if block.block_type == 'image' and block.image:
                    # Проверяем, что изображение действительно сохранилось
                    try:
                        if block.image and block.image.url:
                            block.save()
                    except Exception as e:
                        print(f"Error saving image block: {e}")
    
    def save_related(self, request, form, formsets, change):
        """Переопределяем сохранение связанных объектов"""
        try:
            # Сначала сохраняем формы
            super().save_related(request, form, formsets, change)
            
            # Затем обрабатываем каждый блок контента
            for formset in formsets:
                if formset.model == ArticleContentBlock:
                    for block_form in formset.forms:
                        if not block_form.cleaned_data.get('DELETE', False):
                            instance = block_form.instance
                            if instance.block_type == 'image' and instance.image:
                                # Дополнительная проверка изображения
                                try:
                                    if instance.image and not instance.image.closed:
                                        instance.save()
                                except Exception as e:
                                    print(f"Error processing image: {e}")
        except Exception as e:
            print(f"Error in save_related: {e}")
            raise
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(author=request.user)
    
    def get_readonly_fields(self, request, obj=None):
        if obj and not request.user.is_superuser:
            return self.readonly_fields + ['author', 'category']
        return self.readonly_fields
    
    def has_delete_permission(self, request, obj=None):
        if obj and not request.user.is_superuser:
            return obj.author == request.user
        return super().has_delete_permission(request, obj)

@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ['truncated_content', 'article', 'user', 'status', 
                   'created_at', 'ip_address', 'is_edited']
    list_filter = ['status', 'created_at', 'article', 'is_edited']
    search_fields = ['content', 'user__username', 'article__title', 'ip_address']
    readonly_fields = ['ip_address', 'user_agent', 'created_at', 'updated_at', 
                       'moderated_by', 'moderated_at', 'is_edited', 'edit_count']
    actions = ['approve_comments', 'reject_comments', 'mark_as_spam', 
               'mark_as_pending', 'delete_spam_comments']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('article', 'user', 'content', 'status')
        }),
        ('Техническая информация', {
            'fields': ('ip_address', 'user_agent', 'is_edited', 'edit_count'),
            'classes': ('collapse',)
        }),
        ('Модерация', {
            'fields': ('moderation_notes', 'moderated_by', 'moderated_at'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    def truncated_content(self, obj):
        return Truncator(obj.content).chars(100)
    truncated_content.short_description = 'Комментарий'
    
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            obj.moderated_by = request.user
            obj.moderated_at = timezone.now()
        super().save_model(request, obj, form, change)
    
    @admin.action(description='Одобрить выбранные комментарии')
    def approve_comments(self, request, queryset):
        updated = queryset.update(status='approved', moderated_by=request.user, 
                                  moderated_at=timezone.now())
        self.message_user(request, f'{updated} комментариев одобрено.')
    
    @admin.action(description='Отклонить выбранные комментарии')
    def reject_comments(self, request, queryset):
        updated = queryset.update(status='rejected', moderated_by=request.user, 
                                  moderated_at=timezone.now())
        self.message_user(request, f'{updated} комментариев отклонено.')
    
    @admin.action(description='Пометить как спам')
    def mark_as_spam(self, request, queryset):
        updated = queryset.update(status='spam', moderated_by=request.user, 
                                  moderated_at=timezone.now())
        self.message_user(request, f'{updated} комментариев помечено как спам.')
    
    @admin.action(description='Вернуть на модерацию')
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='pending', moderated_by=None, 
                                  moderated_at=None)
        self.message_user(request, f'{updated} комментариев возвращено на модерацию.')
    
    @admin.action(description='Удалить спам-комментарии')
    def delete_spam_comments(self, request, queryset):
        spam_comments = queryset.filter(status='spam')
        count = spam_comments.count()
        spam_comments.delete()
        self.message_user(request, f'{count} спам-комментариев удалено.')