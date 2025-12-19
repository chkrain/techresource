from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.BlogHomeView.as_view(), name='blog_home'),
    path('category/<slug:slug>/', views.CategoryView.as_view(), name='blog_category'),
    path('article/<slug:slug>/', views.ArticleDetailView.as_view(), name='blog_article'),
    path('article/<slug:slug>/comment/', views.AddCommentView.as_view(), name='add_comment'),
    path('comment/<int:pk>/edit/', views.EditCommentView.as_view(), name='edit_comment'),
    path('comment/<int:pk>/delete/', views.DeleteCommentView.as_view(), name='delete_comment'),
    path('search/', views.BlogSearchView.as_view(), name='blog_search'),
]