"""
Глобальные горячие клавиши для VTTv2
"""
import logging
from pynput import keyboard
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class HotkeyManager:
    """Управление глобальными горячими клавишами"""
    
    def __init__(self, hotkey_string: str, callback: Optional[Callable] = None):
        """
        Инициализация менеджера горячих клавиш
        
        Args:
            hotkey_string: Комбинация клавиш (например, "option+space")
            callback: Функция-колбэк при нажатии
        """
        self.hotkey_string = hotkey_string
        self.callback = callback
        self.listener: Optional[keyboard.Listener] = None
        self.is_running = False
        
        # Парсинг комбинации клавиш
        self.keys = self._parse_hotkey(hotkey_string)
        
        logger.info(f"HotkeyManager инициализирован: {hotkey_string}")
    
    def _parse_hotkey(self, hotkey_string: str) -> set:
        """
        Парсинг строки горячей клавиши
        
        Args:
            hotkey_string: Строка типа "option+space"
        
        Returns:
            Множество кодов клавиш
        """
        keys = set()
        parts = hotkey_string.lower().split('+')
        
        key_map = {
            'option': keyboard.Key.alt,
            'alt': keyboard.Key.alt,
            'command': keyboard.Key.cmd,
            'cmd': keyboard.Key.cmd,
            'control': keyboard.Key.ctrl,
            'ctrl': keyboard.Key.ctrl,
            'shift': keyboard.Key.shift,
            'space': keyboard.Key.space,
        }
        
        for part in parts:
            part = part.strip()
            if part in key_map:
                keys.add(key_map[part])
            else:
                # Обычная клавиша
                try:
                    keys.add(keyboard.KeyCode.from_char(part))
                except (ValueError, AttributeError):
                    logger.warning(f"Неизвестная клавиша: {part}")
        
        return keys
    
    def _on_press(self, key):
        """Обработка нажатия клавиши"""
        # Проверяем комбинацию
        # Упрощенная версия - проверяем все модификаторы + основную клавишу
        pass  # Реализация через глобальный listener
    
    def _on_release(self, key):
        """Обработка отпускания клавиши"""
        pass
    
    def start(self):
        """Запуск слушателя горячих клавиш"""
        if self.is_running:
            logger.warning("Слушатель уже запущен")
            return
        
        # Создание комбинации для pynput
        try:
            # Парсинг комбинации
            if 'option' in self.hotkey_string.lower() and 'space' in self.hotkey_string.lower():
                # Option+Space
                combination = {keyboard.Key.alt, keyboard.Key.space}
            else:
                # Общая обработка
                combination = self.keys
            
            # Создание глобального hotkey listener
            def for_canonical(f):
                return lambda k: f(self.listener.canonical(k))
            
            def on_activate():
                """Активация при нажатии комбинации"""
                if self.callback:
                    self.callback()
            
            # Упрощенная версия через keyboard.GlobalHotKeys
            # pynput поддерживает глобальные горячие клавиши через keyboard.GlobalHotKeys
            try:
                from pynput.keyboard import GlobalHotKeys
                
                # Маппинг комбинации
                hotkey_mapping = {
                    '<alt>+<space>': on_activate,
                }
                
                self.listener = GlobalHotKeys(hotkey_mapping)
                self.listener.start()
                self.is_running = True
                logger.info("✅ Горячие клавиши активированы")
            except Exception as e:
                logger.error(f"Ошибка создания GlobalHotKeys: {e}")
                # Fallback на обычный listener
                self.listener = keyboard.Listener(
                    on_press=self._on_press,
                    on_release=self._on_release
                )
                self.listener.start()
                self.is_running = True
                
        except Exception as e:
            logger.error(f"Ошибка запуска слушателя: {e}")
            raise
    
    def stop(self):
        """Остановка слушателя"""
        if self.listener:
            self.listener.stop()
            self.is_running = False
            logger.info("Слушатель горячих клавиш остановлен")
    
    def set_callback(self, callback: Callable):
        """Установка callback функции"""
        self.callback = callback

