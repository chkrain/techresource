"""
Обновляет пути к изображениям в шаблонах на .webp
Исключает шаблон счёта-оферты (invoice_email.html)
"""

import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Обновляет ссылки на изображения в шаблонах на .webp'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Пробный запуск без изменений'
        )
        
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Создать бэкапы перед изменениями'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Включить обработку шаблона счёта (не рекомендуется)'
        )
    
    def handle(self, *args, **options):
        templates_dir = Path(settings.BASE_DIR) / 'main' / 'templates'
        
        if not templates_dir.exists():
            self.stdout.write(self.style.ERROR('Папка с шаблонами не найдена'))
            return
        
        excluded_templates = [
            'invoice_email.html',
            'invoice_email',
        ]
        
        extensions = ['.jpg', '.jpeg', '.png']
        
        html_files = list(templates_dir.rglob('*.html'))
        
        filtered_files = []
        for html_file in html_files:
            if not options['force']:
                if any(excluded in str(html_file) for excluded in excluded_templates):
                    self.stdout.write(self.style.WARNING(f'🔒 Исключён (шаблон счёта): {html_file.name}'))
                    continue
            filtered_files.append(html_file)
        
        self.stdout.write(f'📁 Найдено HTML файлов: {len(html_files)}')
        self.stdout.write(f'📝 Будет обработано: {len(filtered_files)}\n')
        
        updated_count = 0
        
        for html_file in filtered_files:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            for ext in extensions:
                content = content.replace(f'{ext}', '.webp')
            
            if content != original_content:
                updated_count += 1
                
                if options['backup'] and not options['dry_run']:
                    backup_file = html_file.with_suffix('.html.bak')
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        f.write(original_content)
                    self.stdout.write(f'💾 Бэкап: {backup_file.name}')
                
                if not options['dry_run']:
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.stdout.write(f'✅ {html_file.relative_to(templates_dir)}')
                else:
                    self.stdout.write(f'🔍 [DRY RUN] {html_file.relative_to(templates_dir)}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✨ Обновлено файлов: {updated_count}'))
        
        if not options['force']:
            self.stdout.write(self.style.WARNING(
                '\n⚠️ Шаблон invoice_email.html НЕ был обработан (сохранены оригинальные пути)'
            ))
            self.stdout.write('   Печать, подпись и логотип остались в исходном формате.')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                '\n⚠️ Это был пробный запуск. Для применения изменений запустите без --dry-run'
            ))