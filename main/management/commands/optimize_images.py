"""
Django management command для оптимизации изображений.
Конвертирует JPG/PNG в WebP, оптимизирует размеры, удаляет метаданные.
Исключает критически важные изображения (печати, подписи, логотипы в документах).
"""

import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from PIL import Image, UnidentifiedImageError
import subprocess
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Оптимизирует изображения: конвертация в WebP, сжатие, удаление метаданных'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            default='main/static/images',
            help='Путь к папке с изображениями (относительно BASE_DIR)'
        )
        
        parser.add_argument(
            '--quality',
            type=int,
            default=85,
            help='Качество WebP (1-100, по умолчанию 85)'
        )
        
        parser.add_argument(
            '--max-width',
            type=int,
            default=1920,
            help='Максимальная ширина изображения (по умолчанию 1920)'
        )
        
        parser.add_argument(
            '--keep-original',
            action='store_true',
            help='Сохранять оригиналы (в папку originals/)'
        )
        
        parser.add_argument(
            '--skip-webp',
            action='store_true',
            help='Пропустить конвертацию в WebP'
        )
        
        parser.add_argument(
            '--only-webp',
            action='store_true',
            help='Только конвертировать в WebP (без оптимизации оригиналов)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Пробный запуск без фактических изменений'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод'
        )
    
    def is_excluded(self, file_path):
        """Проверяет, нужно ли исключить файл из конвертации"""
        excluded_names = [
            'pechat',      # печать
            'stamp',       # печать (англ)
            'kaz',         # подпись
            'signature',   # подпись (англ)
            'inv.svg',     # логотип в инвойсе
            'favicon',     # иконки
        ]
        
        file_lower = str(file_path).lower()
        
        for excluded in excluded_names:
            if excluded.lower() in file_lower:
                return True
        return False
    
    def handle(self, *args, **options):
        self.verbose = options['verbose']
        self.dry_run = options['dry_run']
        self.quality = options['quality']
        self.max_width = options['max_width']
        self.keep_original = options['keep_original']
        self.images_path = Path(settings.BASE_DIR) / options['path']
        
        if not self.images_path.exists():
            raise CommandError(f'Папка не найдена: {self.images_path}')
        
        self.stdout.write(self.style.SUCCESS(f'\n🚀 Начинаем оптимизацию изображений'))
        self.stdout.write(f'📁 Папка: {self.images_path}')
        self.stdout.write(f'🎨 Качество: {self.quality}%')
        self.stdout.write(f'📏 Макс. ширина: {self.max_width}px')
        self.stdout.write(self.style.WARNING('⚠️ Исключаемые файлы: печати, подписи, логотипы документов\n'))
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('⚠️ РЕЖИМ DRY RUN - изменения не будут применены\n'))
        
        self.images = self.collect_images()
        
        if not self.images:
            self.stdout.write(self.style.WARNING('⚠️ Изображения не найдены'))
            return
        
        self.stdout.write(f'📸 Найдено изображений: {len(self.images)}')
        
        excluded_count = sum(1 for img in self.images if self.is_excluded(img))
        self.stdout.write(f'🔒 Исключено (печати/подписи): {excluded_count}\n')
        
        if self.keep_original and not self.dry_run:
            self.originals_dir = self.images_path / 'originals'
            self.originals_dir.mkdir(exist_ok=True)
            self.stdout.write(f'💾 Оригиналы будут сохранены в: {self.originals_dir}\n')
        
        self.stats = {
            'converted': 0,
            'optimized': 0,
            'skipped': 0,
            'errors': 0,
            'original_size': 0,
            'new_size': 0,
        }
        
        if not options['skip_webp']:
            self.convert_to_webp()
        
        if not options['only_webp']:
            self.optimize_originals()
        
        self.print_summary()
    
    def collect_images(self):
        """Собирает все изображения для обработки"""
        extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        images = []
        
        for ext in extensions:
            images.extend(self.images_path.rglob(f'*{ext}'))
            images.extend(self.images_path.rglob(f'*{ext.upper()}'))
        
        images = [img for img in images if 'originals' not in str(img) and '.webp' not in str(img).lower()]
        
        return images
    
    def convert_to_webp(self):
        """Конвертирует изображения в WebP (кроме исключённых)"""
        self.stdout.write('🔄 Конвертация в WebP...\n')
        
        to_convert = [
            img for img in self.images 
            if img.suffix.lower() in ['.jpg', '.jpeg', '.png']
            and not self.is_excluded(img)
        ]
        
        skipped_excluded = [
            img for img in self.images 
            if img.suffix.lower() in ['.jpg', '.jpeg', '.png']
            and self.is_excluded(img)
        ]
        
        if skipped_excluded:
            self.stdout.write(self.style.WARNING('🔒 Исключено из конвертации:'))
            for img in skipped_excluded:
                self.stdout.write(f'   - {img.name}')
            self.stdout.write('')
        
        if not to_convert:
            self.stdout.write(self.style.WARNING('  Нет изображений для конвертации\n'))
            return
        
        for i, img_path in enumerate(to_convert, 1):
            self.stdout.write(f'  [{i}/{len(to_convert)}] Обработка: {img_path.name}', ending='')
            
            try:
                result = self.process_webp(img_path)
                if result:
                    self.stats['converted'] += 1
                    if self.verbose:
                        self.stdout.write(f'\r  ✅ {result}')
                    else:
                        self.stdout.write(f'\r  ✅ {img_path.name} -> {img_path.stem}.webp')
                else:
                    self.stdout.write(f'\r  ⏭️  {img_path.name} - пропущен')
            except Exception as e:
                self.stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'\r  ❌ {img_path.name}: {str(e)}'))
        
        self.stdout.write(f'\n📊 Конвертировано: {self.stats["converted"]} файлов\n')
    
    def process_webp(self, img_path):
        """Обрабатывает одно изображение для конвертации в WebP"""
        output_path = img_path.with_suffix('.webp')
        
        if output_path.exists() and output_path.stat().st_size > 0:
            self.stats['skipped'] += 1
            return None
        
        if self.dry_run:
            return f"{img_path.name} -> {output_path.name}"
        
        try:
            if self.keep_original:
                original_backup = self.originals_dir / img_path.name
                if not original_backup.exists():
                    shutil.copy2(img_path, original_backup)
            
            with Image.open(img_path) as img:
                if img.mode == 'RGBA' and img_path.suffix.lower() != '.png':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode not in ['RGB', 'RGBA']:
                    img = img.convert('RGB')
                
                if img.width > self.max_width:
                    ratio = self.max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
                
                img.save(output_path, 'WEBP', quality=self.quality, method=6, optimize=True)
                
                original_size = img_path.stat().st_size
                new_size = output_path.stat().st_size
                self.stats['original_size'] += original_size
                self.stats['new_size'] += new_size
                
                return True
                
        except (UnidentifiedImageError, OSError) as e:
            raise Exception(f"Ошибка обработки: {e}")
    
    def optimize_originals(self):
        """Оптимизирует оригинальные JPG/PNG (кроме исключённых)"""
        self.stdout.write('🔧 Оптимизация оригиналов...\n')
        
        has_jpegoptim = shutil.which('jpegoptim') is not None
        has_optipng = shutil.which('optipng') is not None
        
        if not has_jpegoptim and not has_optipng:
            self.stdout.write(self.style.WARNING(
                '  ⚠️ Утилиты не найдены. Установите: sudo apt install jpegoptim optipng\n'
            ))
            return
        
        to_optimize = []
        
        if has_jpegoptim:
            jpegs = [img for img in self.images if img.suffix.lower() in ['.jpg', '.jpeg'] and not self.is_excluded(img)]
            to_optimize.extend([(img, 'jpeg') for img in jpegs])
        
        if has_optipng:
            pngs = [img for img in self.images if img.suffix.lower() == '.png' and not self.is_excluded(img)]
            to_optimize.extend([(img, 'png') for img in pngs])
        
        skipped_excluded = [
            img for img in self.images 
            if (img.suffix.lower() in ['.jpg', '.jpeg', '.png'] and self.is_excluded(img))
        ]
        
        if skipped_excluded and self.verbose:
            self.stdout.write(self.style.WARNING('🔒 Исключено из оптимизации:'))
            for img in skipped_excluded:
                self.stdout.write(f'   - {img.name}')
            self.stdout.write('')
        
        if not to_optimize:
            self.stdout.write('  Нет изображений для оптимизации\n')
            return
        
        for i, (img_path, img_type) in enumerate(to_optimize, 1):
            self.stdout.write(f'  [{i}/{len(to_optimize)}] {img_path.name}', ending='')
            
            if img_type == 'jpeg':
                if self.optimize_jpeg(img_path):
                    self.stats['optimized'] += 1
                    self.stdout.write(f'\r  ✅ {img_path.name}')
                else:
                    self.stdout.write(f'\r  ⚠️ {img_path.name} - пропущен')
            else:
                if self.optimize_png(img_path):
                    self.stats['optimized'] += 1
                    self.stdout.write(f'\r  ✅ {img_path.name}')
                else:
                    self.stdout.write(f'\r  ⚠️ {img_path.name} - пропущен')
        
        self.stdout.write(f'\n📊 Оптимизировано: {self.stats["optimized"]} файлов\n')
    
    def optimize_jpeg(self, img_path):
        """Оптимизирует JPEG изображение"""
        if self.dry_run:
            return True
        
        try:
            original_size = img_path.stat().st_size
            
            cmd = [
                'jpegoptim', '--strip-all', '--all-progressive',
                '-m', str(self.quality), str(img_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                new_size = img_path.stat().st_size
                self.stats['original_size'] += original_size
                self.stats['new_size'] += new_size
                return True
            else:
                if self.verbose:
                    self.stdout.write(self.style.WARNING(f' {result.stderr}'))
                return False
                
        except Exception as e:
            if self.verbose:
                self.stdout.write(self.style.ERROR(f' {e}'))
            return False
    
    def optimize_png(self, img_path):
        """Оптимизирует PNG изображение"""
        if self.dry_run:
            return True
        
        try:
            original_size = img_path.stat().st_size
            
            cmd = ['optipng', '-o7', '-strip', 'all', str(img_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                new_size = img_path.stat().st_size
                self.stats['original_size'] += original_size
                self.stats['new_size'] += new_size
                return True
                
        except Exception as e:
            if self.verbose:
                self.stdout.write(self.style.ERROR(f' {e}'))
            return False
    
    def print_summary(self):
        """Выводит итоговую статистику"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 ИТОГИ ОПТИМИЗАЦИИ'))
        self.stdout.write('='*60)
        
        self.stdout.write(f'✅ Конвертировано в WebP: {self.stats["converted"]}')
        self.stdout.write(f'🔧 Оптимизировано оригиналов: {self.stats["optimized"]}')
        self.stdout.write(f'⏭️  Пропущено: {self.stats["skipped"]}')
        
        if self.stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'❌ Ошибок: {self.stats["errors"]}'))
        
        if self.stats['original_size'] > 0:
            original_mb = self.stats['original_size'] / (1024 * 1024)
            new_mb = self.stats['new_size'] / (1024 * 1024)
            savings = (1 - self.stats['new_size'] / self.stats['original_size']) * 100
            
            self.stdout.write('\n📦 Экономия места:')
            self.stdout.write(f'   До: {original_mb:.2f} MB')
            self.stdout.write(f'   После: {new_mb:.2f} MB')
            self.stdout.write(self.style.SUCCESS(f'   Экономия: {savings:.1f}% ({original_mb - new_mb:.2f} MB)'))
        
        self.stdout.write(self.style.WARNING('\n🔒 Критические файлы сохранены в исходном формате:'))
        self.stdout.write('   - pechat.webp (печать)')
        self.stdout.write('   - kaz.webp (подпись)')
        self.stdout.write('   - inv.svg (логотип счёта)')
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️ Это был пробный запуск. Никакие изменения не применены.'))
            self.stdout.write('   Для применения изменений запустите без флага --dry-run')
        
        self.stdout.write('='*60 + '\n')