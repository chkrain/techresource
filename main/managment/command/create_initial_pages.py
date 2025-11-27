from django.core.management.base import BaseCommand
from main.models import Page

class Command(BaseCommand):
    help = 'Create initial pages for services'
    
    def handle(self, *args, **options):
        pages_data = [
            {
                'title': 'Электромонтажные работы',
                'slug': 'service_electrical',
                'meta_description': 'Профессиональные электромонтажные работы для промышленных предприятий'
            },
            {
                'title': 'Проектирование систем',
                'slug': 'service_design', 
                'meta_description': 'Проектирование систем автоматизации и технологических процессов'
            },
            {
                'title': 'Разработка ПО и SCADA',
                'slug': 'service_software',
                'meta_description': 'Разработка программного обеспечения и SCADA систем'
            },
            {
                'title': 'Поставка оборудования',
                'slug': 'service_equipment',
                'meta_description': 'Поставка промышленного оборудования и компонентов'
            },
            {
                'title': 'Техническая поддержка',
                'slug': 'service_support', 
                'meta_description': 'Техническая поддержка и консультации'
            },
            {
                'title': 'Сервисное обслуживание',
                'slug': 'service_maintenance',
                'meta_description': 'Сервисное обслуживание промышленного оборудования'
            },
        ]
        
        for page_data in pages_data:
            page, created = Page.objects.get_or_create(
                slug=page_data['slug'],
                defaults=page_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created page: {page.title}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Page already exists: {page.title}')
                )