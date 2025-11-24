"""
Настройка логирования для VTTv2
Формат: ts level service msg meta
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Настройка логирования для приложения
    
    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Формат логов (по умолчанию: ts level service msg)
        log_file: Путь к файлу логов (None = только консоль)
    
    Returns:
        Настроенный logger
    """
    if format_string is None:
        format_string = "%(asctime)s %(levelname)s %(name)s %(message)s"
    
    # Конвертация строки уровня в константу
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Создание handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    # Настройка базового логирования
    logging.basicConfig(
        level=numeric_level,
        format=format_string,
        handlers=handlers,
        force=True  # Перезаписываем существующую конфигурацию
    )
    
    logger = logging.getLogger("vtt2")
    logger.info(f"Логирование инициализировано (уровень: {level})")
    
    return logger

