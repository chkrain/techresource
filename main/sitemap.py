# main/sitemap.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from datetime import datetime

class StaticSitemap(Sitemap):
    changefreq = "weekly"
    priority = 1.0
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
            'register',
            'login',
            'anonymous_order_page',
        ]

    def location(self, item):
        return reverse(item)

sitemaps = {
    'static': StaticSitemap,
}