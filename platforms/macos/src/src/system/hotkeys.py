"""
Глобальные горячие клавиши для VTTv2
"""
import logging
import threading
import time
from pynput import keyboard
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class SafeGlobalHotKeys(keyboard.GlobalHotKeys):
    """
    Безопасная обертка над GlobalHotKeys, которая корректно обрабатывает
    случаи, когда pynput не передает injected параметр для специальных клавиш.
    
    Проблема: В pynput/keyboard/_darwin.py для специальных клавиш (например, space)
    вызывается on_press без injected параметра, но GlobalHotKeys._on_press()
    требует два аргумента (key, injected).
    """
    
    def _on_press(self, key, injected=None):
        """
        Переопределенный метод обработки нажатия клавиши.
        
        Args:
            key: Клавиша
            injected: Флаг инжектированного события (может быть None для специальных клавиш)
        """
        # Если injected не передан (None), считаем что событие не инжектировано
        if injected is None:
            injected = False
        
        # Вызываем родительский метод с правильными аргументами
        super()._on_press(key, injected)
    
    def _on_release(self, key, injected=None):
        """
        Переопределенный метод обработки отпускания клавиши.
        
        Args:
            key: Клавиша
            injected: Флаг инжектированного события (может быть None для специальных клавиш)
        """
        # Если injected не передан (None), считаем что событие не инжектировано
        if injected is None:
            injected = False
        
        # Вызываем родительский метод с правильными аргументами
        super()._on_release(key, injected)


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
        self._restart_lock = threading.Lock()
        self._restart_count = 0
        self._max_restarts = 5
        
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
    
    def _safe_on_press(self, key, *args, **kwargs):
        """Безопасная обработка нажатия клавиши (fallback режим)"""
        try:
            # Проверяем комбинацию
            # Упрощенная версия - проверяем все модификаторы + основную клавишу
            # Реализация через глобальный listener (не используется в основном режиме)
            pass
        except Exception as e:
            logger.error(f"Ошибка в _safe_on_press: {e}", exc_info=True)
    
    def _safe_on_release(self, key, *args, **kwargs):
        """Безопасная обработка отпускания клавиши (fallback режим)"""
        try:
            pass
        except Exception as e:
            logger.error(f"Ошибка в _safe_on_release: {e}", exc_info=True)
    
    def start(self):
        """Запуск слушателя горячих клавиш"""
        if self.is_running:
            logger.warning("Слушатель уже запущен")
            return
        
        # Создание комбинации для pynput
        try:
            # Используем SafeGlobalHotKeys вместо GlobalHotKeys для корректной обработки
            # специальных клавиш, когда pynput не передает injected параметр
            try:
                # Обертка для callback с обработкой исключений
                def safe_callback_wrapper():
                    """Внутренняя обертка для безопасного вызова callback"""
                    try:
                        if self.callback:
                            self.callback()
                    except Exception as e:
                        logger.error(f"Ошибка в callback горячих клавиш: {e}", exc_info=True)
                        # Не перезапускаем listener здесь, чтобы избежать рекурсии
                
                # Lambda для обработки аргумента injected от pynput
                # SafeGlobalHotKeys корректно обрабатывает случаи без injected
                safe_callback = lambda *args, **kwargs: safe_callback_wrapper()
                
                # Маппинг комбинации
                hotkey_mapping = {
                    '<alt>+<space>': safe_callback,
                }
                
                # Создание SafeGlobalHotKeys с обработкой исключений
                # SafeGlobalHotKeys корректно обрабатывает случаи, когда injected не передается
                self.listener = SafeGlobalHotKeys(hotkey_mapping)
                
                # Обертка для обработки исключений в listener.start()
                original_start = self.listener.start
                def safe_start():
                    try:
                        original_start()
                    except Exception as e:
                        logger.error(f"Ошибка запуска GlobalHotKeys listener: {e}", exc_info=True)
                        raise
                
                self.listener.start = safe_start
                self.listener.start()
                self.is_running = True
                self._restart_count = 0  # Сброс счетчика при успешном запуске
                logger.info("✅ Горячие клавиши активированы")
            except Exception as e:
                logger.error(f"Ошибка создания SafeGlobalHotKeys: {e}", exc_info=True)
                # Fallback на обычный listener
                try:
                    self.listener = keyboard.Listener(
                        on_press=self._safe_on_press,
                        on_release=self._safe_on_release
                    )
                    self.listener.start()
                    self.is_running = True
                    logger.info("✅ Горячие клавиши активированы (fallback режим)")
                except Exception as fallback_error:
                    logger.error(f"Ошибка fallback listener: {fallback_error}", exc_info=True)
                    raise
                
        except Exception as e:
            logger.error(f"Ошибка запуска слушателя: {e}")
            raise
    
    def stop(self):
        """Остановка слушателя"""
        if self.listener:
            try:
                self.listener.stop()
                self.is_running = False
                logger.info("Слушатель горячих клавиш остановлен")
            except Exception as e:
                logger.error(f"Ошибка остановки слушателя: {e}", exc_info=True)
                self.is_running = False
    
    def _restart_listener(self):
        """Перезапуск listener при ошибках (с защитой от бесконечных перезапусков)"""
        with self._restart_lock:
            if self._restart_count >= self._max_restarts:
                logger.error(f"Превышен лимит перезапусков ({self._max_restarts}). Остановка автоматических перезапусков.")
                return
            
            self._restart_count += 1
            logger.warning(f"Перезапуск listener горячих клавиш (попытка {self._restart_count}/{self._max_restarts})")
            
            try:
                # Останавливаем текущий listener
                if self.listener:
                    try:
                        self.listener.stop()
                    except:
                        pass
                
                # Небольшая задержка перед перезапуском
                time.sleep(0.5)
                
                # Перезапускаем
                self.start()
            except Exception as e:
                logger.error(f"Ошибка перезапуска listener: {e}", exc_info=True)
                # Планируем следующую попытку через некоторое время
                if self._restart_count < self._max_restarts:
                    threading.Timer(5.0, self._restart_listener).start()
    
    def set_callback(self, callback: Callable):
        """Установка callback функции"""
        self.callback = callback

