from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import os

class Command(BaseCommand):
    help = 'Находит все папки с изображениями в проекте'
    
    def handle(self, *args, **options):
        self.stdout.write('\n🔍 Поиск папок с изображениями...\n')
        
        found = []
        
        search_dirs = [
            settings.BASE_DIR / 'main/static',
            settings.BASE_DIR / 'static',
            settings.BASE_DIR / 'media',
        ]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            for root, dirs, files in os.walk(search_dir):
                if '__pycache__' in root or '.git' in root:
                    continue
                
                images = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))]
                
                if images:
                    rel_path = Path(root).relative_to(settings.BASE_DIR)
                    found.append({
                        'path': rel_path,
                        'count': len(images),
                        'full_path': root
                    })
        
        if found:
            self.stdout.write(self.style.SUCCESS('✅ Найденные папки с изображениями:\n'))
            for item in found:
                self.stdout.write(f'  📁 {item["path"]}')
                self.stdout.write(f'     📸 {item["count"]} изображений')
                self.stdout.write(f'     💡 python manage.py optimize_images --path {item["path"]}\n')
        else:
            self.stdout.write(self.style.WARNING('❌ Папки с изображениями не найдены'))