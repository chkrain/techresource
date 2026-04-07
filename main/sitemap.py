# main/sitemap.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, ServicePage, Category

class StaticSitemap(Sitemap):
    protocol = 'https'
    
    def items(self):
        return [
            'index',
            'about',
            'contacts',
            'privacy',
            'services',
            'products',
            'service_design',
            'service_electrical',
            'service_software',
            'service_equipment',
            'service_support',
            'service_maintenance',
            'support',
        ] 
    
    def location(self, item):
        return reverse(item)
    
    def changefreq(self, item):
        if item == 'index':
            return 'daily'
        elif item in ['services', 'products']:
            return 'weekly'
        else:
            return 'monthly'
    
    def priority(self, item):
        if item == 'index':
            return '1.0'
        elif item in ['about', 'contacts', 'services', 'products']:
            return '0.9'
        elif item.startswith('service_'):
            return '0.8'
        else:
            return '0.5'

class CategorySitemap(Sitemap):
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.7
    
    def items(self):
        return Category.objects.filter(is_active=True)
    
    def location(self, obj):
        try:
            return reverse('products') + f'?category={obj.slug}'
        except:
            return f"/products/?category={obj.slug}"
    
    def lastmod(self, obj):
        latest_product = Product.objects.filter(
            category=obj, 
            is_active=True
        ).order_by('-updated_at').first()
        return latest_product.updated_at if latest_product else obj.updated_at

class ProductSitemap(Sitemap):
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.8
    
    def items(self):
        return Product.objects.filter(is_active=True)
    
    def location(self, obj):
        return f"/product/{obj.id}/"
    
    def lastmod(self, obj):
        return obj.updated_at

class ServicePageSitemap(Sitemap):
    protocol = 'https'
    changefreq = 'monthly'
    priority = 0.6
    
    def items(self):
        if 'ServicePage' not in globals():
            return []
        return ServicePage.objects.filter(is_active=True)
    
    def location(self, obj):
        try:
            return obj.get_absolute_url()
        except:
            return f"/services/dynamic/{obj.slug}/"
    
    def lastmod(self, obj):
        return obj.updated_at

sitemaps = {
    'static': StaticSitemap,
    'products': ProductSitemap,
    'categories': CategorySitemap, 
    'services': ServicePageSitemap,
}
