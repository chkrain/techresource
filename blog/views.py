from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse_lazy
from .models import BlogArticle, BlogCategory, BlogComment
from main.models import SecurityLog
import datetime
import re
import bleach
from django.utils.html import strip_tags
from urllib.parse import urlparse
from django.core.cache import cache

class BlogHomeView(ListView):
    """Главная страница блога"""
    model = BlogArticle
    template_name = 'blog/home.html'
    context_object_name = 'articles'
    paginate_by = 10
    
    def get_queryset(self):
        return BlogArticle.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related('author', 'category').order_by('-published_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = BlogCategory.objects.filter(is_active=True)
        context['featured_articles'] = BlogArticle.objects.filter(
            status='published',
            is_featured=True,
            published_at__lte=timezone.now()
        ).order_by('-published_at')[:3]
        return context

class ArticleDetailView(DetailView):
    """Детальная страница статьи"""
    model = BlogArticle
    template_name = 'blog/article_detail.html'
    context_object_name = 'article'
    
    def get_queryset(self):
        return BlogArticle.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related('author', 'category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['categories'] = BlogCategory.objects.filter(is_active=True)
        
        context['previous_article'] = BlogArticle.objects.filter(
            status='published',
            published_at__lt=self.object.published_at,
            published_at__lte=timezone.now()
        ).order_by('-published_at').first()
        
        context['next_article'] = BlogArticle.objects.filter(
            status='published',
            published_at__gt=self.object.published_at,
            published_at__lte=timezone.now()
        ).order_by('published_at').first()
        
        word_count = len(self.object.content.split())
        reading_minutes = max(1, word_count // 200) 
        context['reading_time'] = f"{reading_minutes} мин. чтения"
        
        return context

class CategoryView(ListView):
    """Статьи по категории"""
    model = BlogArticle
    template_name = 'blog/category.html'
    context_object_name = 'articles'
    paginate_by = 10
    
    def get_queryset(self):
        category = get_object_or_404(BlogCategory, slug=self.kwargs['slug'], is_active=True)
        return BlogArticle.objects.filter(
            category=category,
            status='published',
            published_at__lte=timezone.now()
        ).select_related('author', 'category').order_by('-published_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(BlogCategory, slug=self.kwargs['slug'])
        context['categories'] = BlogCategory.objects.filter(is_active=True)
        return context

class AddCommentView(LoginRequiredMixin, CreateView):
    """Добавление комментария"""
    model = BlogComment
    fields = ['content']
    template_name = 'blog/add_comment.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.article = get_object_or_404(BlogArticle, slug=self.kwargs['slug'])
        
        if not self.article.allow_comments:
            messages.error(request, 'Комментарии к этой статье закрыты.')
            return redirect(self.article.get_absolute_url())
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        last_hour = timezone.now() - datetime.timedelta(hours=1)
        recent_comments = BlogComment.objects.filter(
            user=self.request.user,
            created_at__gte=last_hour
        ).count()
        
        if recent_comments >= 5:
            messages.error(self.request, 'Слишком много комментариев за последний час.')
            return redirect(self.article.get_absolute_url())
        
        raw_content = form.cleaned_data['content']
        
        clean_content = strip_tags(raw_content)
        
        words = clean_content.split()
        filtered_words = []
        for word in words:
            try:
                result = urlparse(word)
                if result.scheme or ('.' in word and len(word.split('.')[-1]) <= 4):
                    continue
                filtered_words.append(word)
            except:
                filtered_words.append(word)
        
        clean_content = ' '.join(filtered_words)
        
        if len(clean_content) < 10:
            messages.error(self.request, 'Комментарий слишком короткий.')
            return self.form_invalid(form)
        
        if len(clean_content) > 2000:
            clean_content = clean_content[:2000]
        
        if re.search(r'(.)\1{5,}', clean_content):
            status = 'spam'
            messages.warning(self.request, 'Комментарий помечен как спам.')
        else:
            status = 'pending'
        
        # Простая анти-спам проверка
        content_lower = clean_content.lower()
        spam_indicators = ['http://', 'https://', 'www.', '.ru', 'купить', 'цена', 'дешево']
        spam_score = sum(1 for indicator in spam_indicators if indicator in content_lower)
        
        if spam_score > 2 or len(clean_content.split()) < 3:
            status = 'spam'
            messages.warning(self.request, 'Ваш комментарий помечен как спам.')
        
        comment = form.save(commit=False)
        comment.article = self.article
        comment.user = self.request.user
        comment.ip_address = self.request.META.get('REMOTE_ADDR')
        comment.user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        comment.status = status
        comment.content = clean_content
        
        if status == 'pending':
            messages.success(self.request, 'Комментарий отправлен на модерацию.')
        
        comment.save()
        
        SecurityLog.objects.create(
            user=self.request.user,
            action='comment_added',
            ip_address=comment.ip_address,
            user_agent=comment.user_agent,
            details={
                'article_id': self.article.id,
                'comment_id': comment.id,
            },
            success=True,
            risk_level='low'
        )
        
        return redirect(self.article.get_absolute_url() + '#comments')

class EditCommentView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Редактирование комментария"""
    model = BlogComment
    fields = ['content']
    template_name = 'blog/edit_comment.html'
    
    def test_func(self):
        """Проверка прав доступа"""
        comment = self.get_object()
        return self.request.user == comment.user or self.request.user.is_superuser
    
    def handle_no_permission(self):
        messages.error(self.request, 'У вас нет прав для редактирования этого комментария.')
        article = self.get_object().article
        return redirect(article.get_absolute_url())
    
    def form_valid(self, form):
        comment = form.save(commit=False)
        
        time_limit = timezone.now() - datetime.timedelta(minutes=30)
        if comment.created_at < time_limit and not self.request.user.is_superuser:
            messages.error(self.request, 'Время для редактирования истекло (30 минут).')
            return redirect(comment.article.get_absolute_url())
        
        raw_content = form.cleaned_data['content']
        clean_content = strip_tags(raw_content)
        clean_content = bleach.clean(clean_content, tags=[], attributes={}, strip=True)
        
        if len(clean_content) < 10:
            messages.error(self.request, 'Комментарий слишком короткий.')
            return self.form_invalid(form)
        
        if len(clean_content) > 2000:
            clean_content = clean_content[:2000]
        
        comment.content = clean_content
        comment.is_edited = True
        comment.edit_count = getattr(comment, 'edit_count', 0) + 1
        comment.edited_at = timezone.now()
        comment.save()
        
        messages.success(self.request, 'Комментарий отредактирован.')
        return redirect(comment.article.get_absolute_url() + '#comments')

class DeleteCommentView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление комментария"""
    model = BlogComment
    template_name = 'blog/delete_comment.html'
    
    def test_func(self):
        """Проверка прав доступа"""
        comment = self.get_object()
        return self.request.user == comment.user or self.request.user.is_superuser
    
    def handle_no_permission(self):
        messages.error(self.request, 'У вас нет прав для удаления этого комментария.')
        article = self.get_object().article
        return redirect(article.get_absolute_url())
    
    def get_success_url(self):
        messages.success(self.request, 'Комментарий удален.')
        return reverse_lazy('blog:blog_article', kwargs={'slug': self.object.article.slug})

class BlogSearchView(ListView):
    """Поиск по блогу"""
    model = BlogArticle
    template_name = 'blog/search.html'
    context_object_name = 'articles'
    paginate_by = 10
    
    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if query:
            if len(query) > 100:
                query = query[:100]
            
            return BlogArticle.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(excerpt__icontains=query) |
                Q(tags__icontains=query),
                status='published',
                published_at__lte=timezone.now()
            ).distinct().select_related('author', 'category').order_by('-published_at')
        
        return BlogArticle.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['categories'] = BlogCategory.objects.filter(is_active=True)
        return context