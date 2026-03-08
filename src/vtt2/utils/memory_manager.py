"""
Управление памятью и очистка кэша для долгой работы приложения
"""
import logging
import gc
import psutil
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryManager:
    """Управление памятью и очистка для долгой работы"""
    
    def __init__(self, memory_limit_mb: int = 16384, cleanup_threshold_mb: int = 12288):
        """
        Инициализация менеджера памяти
        
        Args:
            memory_limit_mb: Лимит памяти в MB (по умолчанию 16GB)
            cleanup_threshold_mb: Порог для запуска очистки (по умолчанию 12GB = 75% от лимита)
        """
        self.memory_limit_mb = memory_limit_mb
        self.cleanup_threshold_mb = cleanup_threshold_mb
        self.process = psutil.Process(os.getpid())
        
        logger.info(f"MemoryManager инициализирован: лимит={memory_limit_mb}MB, порог очистки={cleanup_threshold_mb}MB")
    
    def get_memory_usage(self) -> dict:
        """
        Получение информации об использовании памяти
        
        Returns:
            Словарь с информацией о памяти
        """
        try:
            mem_info = self.process.memory_info()
            system_mem = psutil.virtual_memory()
            
            return {
                'rss_mb': mem_info.rss / (1024 * 1024),  # Resident Set Size
                'vms_mb': mem_info.vms / (1024 * 1024),  # Virtual Memory Size
                'system_total_gb': system_mem.total / (1024 * 1024 * 1024),
                'system_available_gb': system_mem.available / (1024 * 1024 * 1024),
                'system_percent': system_mem.percent,
            }
        except Exception as e:
            logger.warning(f"Не удалось получить информацию о памяти: {e}")
            return {}
    
    def log_memory_usage(self, context: str = ""):
        """
        Логирование использования памяти
        
        Args:
            context: Контекст для лога
        """
        mem_info = self.get_memory_usage()
        if mem_info:
            logger.info(
                f"💾 Память {context}: "
                f"RSS={mem_info['rss_mb']:.0f}MB, "
                f"Система={mem_info['system_percent']:.1f}% "
                f"({mem_info['system_available_gb']:.1f}GB свободно)"
            )
    
    def should_cleanup(self) -> bool:
        """
        Проверка, нужно ли запустить очистку памяти
        
        Returns:
            True если использование памяти превышает порог
        """
        mem_info = self.get_memory_usage()
        if not mem_info:
            return False
        
        rss_mb = mem_info.get('rss_mb', 0)
        return rss_mb > self.cleanup_threshold_mb
    
    def cleanup_memory(self, force_gc: bool = True) -> dict:
        """
        Очистка памяти
        
        Args:
            force_gc: Принудительный запуск garbage collector
        
        Returns:
            Информация о памяти до и после очистки
        """
        mem_before = self.get_memory_usage()
        
        logger.info("🧹 Запуск очистки памяти...")
        
        # Принудительный garbage collection
        if force_gc:
            collected = gc.collect()
            logger.debug(f"Garbage collector собрал {collected} объектов")
        
        mem_after = self.get_memory_usage()
        
        if mem_before and mem_after:
            freed_mb = mem_before.get('rss_mb', 0) - mem_after.get('rss_mb', 0)
            logger.info(f"✅ Очистка завершена: освобождено ~{freed_mb:.0f}MB")
        
        return {
            'before': mem_before,
            'after': mem_after,
        }
    
    def cleanup_temp_files(self, temp_dirs: Optional[list] = None):
        """
        Очистка временных файлов
        
        Args:
            temp_dirs: Список директорий для очистки (по умолчанию стандартные временные директории)
        """
        if temp_dirs is None:
            temp_dirs = [
                Path.home() / ".cache" / "vtt-mlx-m4",
            ]
        
        logger.info("🧹 Очистка временных файлов...")
        cleaned_count = 0
        
        for temp_dir in temp_dirs:
            if not temp_dir.exists():
                continue
            
            try:
                # Очищаем только файлы старше 1 часа
                import time
                current_time = time.time()
                one_hour_ago = current_time - 3600
                
                for file_path in temp_dir.rglob("*"):
                    if file_path.is_file():
                        try:
                            if file_path.stat().st_mtime < one_hour_ago:
                                file_path.unlink()
                                cleaned_count += 1
                        except Exception:
                            pass  # Игнорируем ошибки доступа
                
            except Exception as e:
                logger.debug(f"Не удалось очистить {temp_dir}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"✅ Очищено {cleaned_count} временных файлов")
    
    def light_cleanup(self):
        """
        Лёгкая очистка — принудительный gc.collect() без логирования.
        Вызывается после каждой транскрипции для предотвращения накопления памяти.
        """
        gc.collect()

    def monitor_and_cleanup_if_needed(self, context: str = ""):
        """
        Мониторинг памяти и автоматическая очистка при необходимости
        
        Args:
            context: Контекст для лога
        """
        if self.should_cleanup():
            logger.warning(f"⚠️ Использование памяти превышает порог ({self.cleanup_threshold_mb}MB)")
            self.log_memory_usage(f"до очистки ({context})")
            self.cleanup_memory()
            self.log_memory_usage(f"после очистки ({context})")
        else:
            self.log_memory_usage(context)

