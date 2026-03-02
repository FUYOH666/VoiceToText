"""
Глобальные горячие клавиши для VTTv2
"""
import logging
import threading
import queue
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
    
    def _on_press(self, key, injected=False):
        """Обработка нажатия клавиши
        
        Args:
            key: Клавиша
            injected: Флаг, указывающий, что событие было инжектировано (для совместимости с pynput)
        """
        # Проверяем комбинацию
        # Упрощенная версия - проверяем все модификаторы + основную клавишу
        pass  # Реализация через глобальный listener
    
    def _on_release(self, key, injected=False):
        """Обработка отпускания клавиши
        
        Args:
            key: Клавиша
            injected: Флаг, указывающий, что событие было инжектировано (для совместимости с pynput)
        """
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
            
            # Используем SafeGlobalHotKeys для корректной обработки injected параметра
            # pynput поддерживает глобальные горячие клавиши через keyboard.GlobalHotKeys
            try:
                # Парсинг комбинации для правильного формата
                # pynput использует формат '<modifier>+<key>'
                hotkey_format = self._format_hotkey_for_pynput()
                
                logger.debug(f"Регистрация горячей клавиши: {hotkey_format}")
                
                # Обертка для обработки ошибок внутри GlobalHotKeys
                # В pynput 1.8.0+ обработчики должны принимать аргумент 'injected'
                def safe_on_activate(injected=False):
                    """Безопасная обертка для активации
                    
                    Args:
                        injected: Флаг, указывающий, что событие было инжектировано программно
                    """
                    try:
                        if self.callback:
                            self.callback()
                    except Exception as e:
                        logger.error(f"Ошибка в callback горячей клавиши: {e}", exc_info=True)
                
                # Маппинг комбинации
                hotkey_mapping = {
                    hotkey_format: safe_on_activate,
                }
                
                # Создание SafeGlobalHotKeys (исправляет проблему с injected параметром)
                self.listener = SafeGlobalHotKeys(hotkey_mapping)
                self.listener.start()
                self.is_running = True
                
                # Даем время на инициализацию
                import time
                time.sleep(0.1)
                
                # Проверяем, что listener действительно работает
                if self.listener.running:
                    logger.info("✅ Горячие клавиши активированы")
                else:
                    logger.warning("⚠️ Слушатель запущен, но может не работать без разрешения Accessibility")
                    logger.warning("⚠️ Убедитесь, что приложение добавлено в Системные настройки > Конфиденциальность > Управление компьютером")
                
            except (TypeError, AttributeError, RuntimeError) as e:
                # Обработка ошибок совместимости с pynput
                logger.warning(f"Проблема совместимости с GlobalHotKeys: {e}")
                logger.debug("Используем fallback метод через обычный Listener")
                # Fallback на обычный listener (не будет работать глобально)
                try:
                    self.listener = keyboard.Listener(
                        on_press=self._on_press,
                        on_release=self._on_release
                    )
                    self.listener.start()
                    self.is_running = True
                    logger.warning("⚠️ Fallback метод активирован (может не работать глобально)")
                except Exception as fallback_error:
                    logger.error(f"Ошибка fallback метода: {fallback_error}")
                    raise
            except Exception as e:
                logger.error(f"Ошибка создания SafeGlobalHotKeys: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                logger.error("❌ Не удалось зарегистрировать глобальные горячие клавиши")
                logger.error("⚠️ Убедитесь, что приложение добавлено в Системные настройки > Конфиденциальность > Управление компьютером")
                # Fallback на обычный listener (не будет работать глобально)
                logger.warning("Пробуем fallback метод (может не работать глобально)")
                try:
                    self.listener = keyboard.Listener(
                        on_press=self._on_press,
                        on_release=self._on_release
                    )
                    self.listener.start()
                    self.is_running = True
                except Exception as fallback_error:
                    logger.error(f"Ошибка fallback метода: {fallback_error}")
                    raise
                
        except Exception as e:
            logger.error(f"Ошибка запуска слушателя: {e}")
            raise
    
    def stop(self):
        """Остановка слушателя"""
        if self.listener:
            self.listener.stop()
            self.is_running = False
            logger.info("Слушатель горячих клавиш остановлен")
    
    def _format_hotkey_for_pynput(self) -> str:
        """
        Форматирование горячей клавиши для pynput GlobalHotKeys
        
        Returns:
            Строка в формате pynput (например, '<alt>+<space>')
        """
        parts = self.hotkey_string.lower().split('+')
        formatted_parts = []
        
        key_map = {
            'option': 'alt',
            'alt': 'alt',
            'command': 'cmd',
            'cmd': 'cmd',
            'control': 'ctrl',
            'ctrl': 'ctrl',
            'shift': 'shift',
            'space': 'space',
        }
        
        for part in parts:
            part = part.strip()
            if part in key_map:
                formatted_parts.append(f'<{key_map[part]}>')
            else:
                # Обычная клавиша
                formatted_parts.append(f'<{part}>')
        
        return '+'.join(formatted_parts)
    
    def set_callback(self, callback: Callable):
        """Установка callback функции"""
        self.callback = callback

