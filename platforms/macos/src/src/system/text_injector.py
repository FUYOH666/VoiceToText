"""
Вставка текста в место курсора через macOS API
"""
import logging
import time
import sys
import subprocess

try:
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSetFlags,
        kCGEventKeyDown,
        kCGEventKeyUp,
        kCGAnnotatedSessionEventTap,
        kCGSessionEventTap,
        kCGEventSourceStateHIDSystemState,
        kCGEventFlagMaskCommand,
    )
    from AppKit import NSPasteboard, NSStringPboardType, NSApplication
    import pyperclip
    PYOBJC_AVAILABLE = True
except ImportError:
    PYOBJC_AVAILABLE = False

logger = logging.getLogger(__name__)


class TextInjector:
    """Вставка текста в место курсора"""
    
    def __init__(self, config):
        """
        Инициализация вставки текста
        
        Args:
            config: Конфигурация приложения
        """
        self.config = config
        self.method = config.ui.auto_paste_method
        
        if not PYOBJC_AVAILABLE:
            logger.error("PyObjC недоступен - автовставка невозможна")
            sys.exit(1)
        
        logger.info(f"TextInjector инициализирован (метод: {self.method})")
    
    def paste_text(self, text: str) -> bool:
        """
        Вставка текста в место курсора
        
        Args:
            text: Текст для вставки
        
        Returns:
            True если успешно, False иначе
        """
        if not text or not text.strip():
            logger.warning("Пустой текст для вставки")
            return False
        
        logger.info(f"Вставка текста ({len(text)} символов) методом {self.method}")
        
        # Пробуем разные методы по очереди
        if self.method == "cgevent":
            # Сначала пробуем CGEvent
            if self._paste_via_cgevent(text):
                return True
            # Если не получилось, пробуем AppleScript
            logger.info("CGEvent не сработал, пробуем AppleScript")
            if self._paste_via_applescript(text):
                return True
            # Fallback на clipboard
            return self._paste_via_clipboard(text)
        elif self.method == "clipboard":
            return self._paste_via_clipboard(text)
        else:
            logger.error(f"Неизвестный метод: {self.method}")
            return False
    
    def _paste_via_cgevent(self, text: str) -> bool:
        """
        Вставка текста через CGEvent (эмуляция клавиатуры)
        
        Args:
            text: Текст для вставки
        
        Returns:
            True если успешно
        """
        try:
            # Сначала копируем в буфер обмена
            pyperclip.copy(text)
            logger.debug("Текст скопирован в буфер обмена")
            
            # Небольшая задержка для гарантии копирования
            time.sleep(0.2)
            
            # Эмуляция Cmd+V
            # Коды клавиш (macOS HID)
            cmd_key = 0x37  # Command (Left Command)
            v_key = 0x09    # V
            
            # Создаем события с правильными флагами
            # Cmd Down
            cmd_down = CGEventCreateKeyboardEvent(None, cmd_key, True)
            CGEventSetFlags(cmd_down, kCGEventFlagMaskCommand)
            
            # V Down (с флагом Command)
            v_down = CGEventCreateKeyboardEvent(None, v_key, True)
            CGEventSetFlags(v_down, kCGEventFlagMaskCommand)
            
            # V Up
            v_up = CGEventCreateKeyboardEvent(None, v_key, False)
            CGEventSetFlags(v_up, kCGEventFlagMaskCommand)
            
            # Cmd Up
            cmd_up = CGEventCreateKeyboardEvent(None, cmd_key, False)
            
            # Отправка событий в правильном порядке
            # Используем kCGSessionEventTap для глобальной вставки
            CGEventPost(kCGSessionEventTap, cmd_down)
            time.sleep(0.01)
            CGEventPost(kCGSessionEventTap, v_down)
            time.sleep(0.05)  # Задержка для обработки вставки
            CGEventPost(kCGSessionEventTap, v_up)
            time.sleep(0.01)
            CGEventPost(kCGSessionEventTap, cmd_up)
            
            logger.info("✅ Текст вставлен через CGEvent")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка вставки через CGEvent: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Fallback на clipboard
            logger.warning("Переключение на метод clipboard")
            return self._paste_via_clipboard(text)
    
    def _paste_via_clipboard(self, text: str) -> bool:
        """
        Вставка текста через буфер обмена (требует ручного Cmd+V)
        
        Args:
            text: Текст для вставки
        
        Returns:
            True если текст скопирован в буфер
        """
        try:
            pyperclip.copy(text)
            logger.info("✅ Текст скопирован в буфер обмена (нажмите Cmd+V для вставки)")
            return True
        except Exception as e:
            logger.error(f"Ошибка копирования в буфер обмена: {e}")
            return False
    
    def _paste_via_applescript(self, text: str) -> bool:
        """
        Вставка текста через AppleScript (альтернативный метод)
        Использует буфер обмена и Cmd+V
        
        Args:
            text: Текст для вставки
        
        Returns:
            True если успешно
        """
        try:
            # Сначала копируем в буфер обмена
            pyperclip.copy(text)
            time.sleep(0.1)
            
            # AppleScript команда для вставки через Cmd+V
            applescript = '''
            tell application "System Events"
                keystroke "v" using command down
            end tell
            '''
            
            # Выполняем через osascript
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info("✅ Текст вставлен через AppleScript (Cmd+V)")
                return True
            else:
                logger.warning(f"AppleScript вернул ошибку: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка вставки через AppleScript: {e}")
            return False

