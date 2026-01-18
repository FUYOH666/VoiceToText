"""
Глобальные горячие клавиши для VTTv2
Использует quickmachotkey для надежной работы на macOS
"""
import logging
import time
import threading
from typing import Optional, Callable, Tuple

logger = logging.getLogger(__name__)

# Импорт quickmachotkey
try:
    from quickmachotkey import quickHotKey, mask
    from quickmachotkey.constants import (
        # Модификаторы
        cmdKey,
        controlKey,
        optionKey,
        shiftKey,
        # Virtual key codes
        kVK_Space,
        kVK_Return,
        kVK_Tab,
        kVK_Escape,
        kVK_Delete,
        kVK_ForwardDelete,
        kVK_ANSI_A, kVK_ANSI_B, kVK_ANSI_C, kVK_ANSI_D, kVK_ANSI_E,
        kVK_ANSI_F, kVK_ANSI_G, kVK_ANSI_H, kVK_ANSI_I, kVK_ANSI_J,
        kVK_ANSI_K, kVK_ANSI_L, kVK_ANSI_M, kVK_ANSI_N, kVK_ANSI_O,
        kVK_ANSI_P, kVK_ANSI_Q, kVK_ANSI_R, kVK_ANSI_S, kVK_ANSI_T,
        kVK_ANSI_U, kVK_ANSI_V, kVK_ANSI_W, kVK_ANSI_X, kVK_ANSI_Y, kVK_ANSI_Z,
        kVK_ANSI_0, kVK_ANSI_1, kVK_ANSI_2, kVK_ANSI_3, kVK_ANSI_4,
        kVK_ANSI_5, kVK_ANSI_6, kVK_ANSI_7, kVK_ANSI_8, kVK_ANSI_9,
    )
    QUICKMACHOTKEY_AVAILABLE = True
except ImportError:
    QUICKMACHOTKEY_AVAILABLE = False
    logger.error("quickmachotkey не установлен. Установите: uv add quickmachotkey")


class HotkeyManager:
    """Управление глобальными горячими клавишами через quickmachotkey"""
    
    def __init__(self, hotkey_string: str, callback: Optional[Callable] = None):
        """
        Инициализация менеджера горячих клавиш
        
        Args:
            hotkey_string: Комбинация клавиш (например, "option+space")
            callback: Функция-колбэк при нажатии
        """
        if not QUICKMACHOTKEY_AVAILABLE:
            raise ImportError("quickmachotkey не установлен. Установите: uv add quickmachotkey")
        
        self.hotkey_string = hotkey_string
        self.callback = callback
        self.is_running = False
        self.hotkey_handler = None
        
        # Парсинг горячей клавиши
        self.virtual_key, self.modifier_mask = self._parse_hotkey(hotkey_string)
        
        # Debounce механизм для предотвращения спама активаций
        self.last_activation_time: Optional[float] = None
        self.debounce_timeout = 0.3  # секунд между активациями (300ms)
        self.activation_count = 0
        self.max_activation_count = 1000000
        
        # Блокировка для защиты от одновременных активаций
        self._lock = threading.Lock()
        self._activation_pending = False
        
        logger.info(f"HotkeyManager инициализирован: {hotkey_string} (virtual_key={self.virtual_key}, modifier_mask={self.modifier_mask})")
    
    def _parse_hotkey(self, hotkey_string: str) -> Tuple[int, int]:
        """
        Парсинг строки горячей клавиши в virtual key code и modifier mask
        
        Args:
            hotkey_string: Строка типа "option+space"
        
        Returns:
            Tuple (virtual_key_code, modifier_mask)
        """
        parts = [p.strip().lower() for p in hotkey_string.split('+')]
        
        # Маппинг модификаторов
        modifier_map = {
            'option': optionKey,
            'alt': optionKey,
            'command': cmdKey,
            'cmd': cmdKey,
            'control': controlKey,
            'ctrl': controlKey,
            'shift': shiftKey,
        }
        
        # Маппинг клавиш в virtual key codes
        key_map = {
            'space': kVK_Space,
            'return': kVK_Return,
            'enter': kVK_Return,
            'tab': kVK_Tab,
            'escape': kVK_Escape,
            'esc': kVK_Escape,
            'delete': kVK_Delete,
            'backspace': kVK_Delete,
            'a': kVK_ANSI_A, 'b': kVK_ANSI_B, 'c': kVK_ANSI_C, 'd': kVK_ANSI_D,
            'e': kVK_ANSI_E, 'f': kVK_ANSI_F, 'g': kVK_ANSI_G, 'h': kVK_ANSI_H,
            'i': kVK_ANSI_I, 'j': kVK_ANSI_J, 'k': kVK_ANSI_K, 'l': kVK_ANSI_L,
            'm': kVK_ANSI_M, 'n': kVK_ANSI_N, 'o': kVK_ANSI_O, 'p': kVK_ANSI_P,
            'q': kVK_ANSI_Q, 'r': kVK_ANSI_R, 's': kVK_ANSI_S, 't': kVK_ANSI_T,
            'u': kVK_ANSI_U, 'v': kVK_ANSI_V, 'w': kVK_ANSI_W, 'x': kVK_ANSI_X,
            'y': kVK_ANSI_Y, 'z': kVK_ANSI_Z,
            '0': kVK_ANSI_0, '1': kVK_ANSI_1, '2': kVK_ANSI_2, '3': kVK_ANSI_3,
            '4': kVK_ANSI_4, '5': kVK_ANSI_5, '6': kVK_ANSI_6, '7': kVK_ANSI_7,
            '8': kVK_ANSI_8, '9': kVK_ANSI_9,
        }
        
        modifiers = []
        virtual_key = None
        
        for part in parts:
            if part in modifier_map:
                modifiers.append(modifier_map[part])
            elif part in key_map:
                if virtual_key is not None:
                    raise ValueError(f"Несколько клавиш указано в комбинации: {hotkey_string}")
                virtual_key = key_map[part]
            else:
                raise ValueError(f"Неизвестная клавиша или модификатор: {part} в {hotkey_string}")
        
        if virtual_key is None:
            raise ValueError(f"Не указана основная клавиша в комбинации: {hotkey_string}")
        
        # Создаем modifier mask
        if modifiers:
            modifier_mask = mask(*modifiers)
        else:
            modifier_mask = 0
        
        return virtual_key, modifier_mask
    
    def _hotkey_handler(self):
        """Внутренний обработчик горячей клавиши с debounce"""
        with self._lock:
            # Debounce проверка
            current_time = time.time()
            if self.last_activation_time is not None:
                time_since_last = current_time - self.last_activation_time
                if time_since_last < self.debounce_timeout:
                    logger.debug(
                        f"Активация игнорирована (debounce): прошло {time_since_last:.3f}с, "
                        f"минимум {self.debounce_timeout}с"
                    )
                    return
            
            if self._activation_pending:
                logger.debug("Активация уже обрабатывается, игнорируем")
                return
            
            self._activation_pending = True
            self.last_activation_time = current_time
            self.activation_count += 1
            
            # Защита от переполнения счетчика
            if self.activation_count >= self.max_activation_count:
                logger.info(f"Счетчик активаций достиг максимума ({self.max_activation_count}), сбрасываем")
                self.activation_count = 0
        
        try:
            logger.info(
                f"✅ Горячая клавиша активирована: {self.hotkey_string} "
                f"(активация #{self.activation_count})"
            )
            
            if self.callback:
                try:
                    self.callback()
                except Exception as e:
                    logger.error(f"Ошибка в callback горячей клавиши: {e}", exc_info=True)
        finally:
            with self._lock:
                self._activation_pending = False
    
    def start(self):
        """Запуск слушателя горячих клавиш"""
        if self.is_running:
            logger.warning("Слушатель уже запущен")
            return
        
        try:
            # Регистрация горячей клавиши через quickHotKey декоратор
            # Создаем функцию-обертку для применения декоратора
            @quickHotKey(virtualKey=self.virtual_key, modifierMask=self.modifier_mask)
            def hotkey_wrapper():
                """Обертка для обработчика горячей клавиши"""
                self._hotkey_handler()
            
            # Сохраняем ссылку на задекорированную функцию
            self.hotkey_handler = hotkey_wrapper
            
            self.is_running = True
            logger.info(f"✅ Горячие клавиши активированы: {self.hotkey_string}")
            logger.debug(f"Зарегистрирована горячая клавиша: virtual_key={self.virtual_key}, modifier_mask={self.modifier_mask}")
            
        except Exception as e:
            logger.error(f"Ошибка запуска слушателя: {e}", exc_info=True)
            self.is_running = False
            raise
    
    def stop(self):
        """Остановка слушателя"""
        if not self.is_running:
            return
        
        try:
            # quickmachotkey не предоставляет явного метода остановки
            # Горячие клавиши остаются активными пока работает event loop
            # Мы просто помечаем как остановленный
            self.is_running = False
            self.hotkey_handler = None
            logger.info("Слушатель горячих клавиш остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки слушателя: {e}", exc_info=True)
    
    def restart(self):
        """Перезапуск слушателя (для восстановления при проблемах)"""
        logger.info("Перезапуск слушателя горячих клавиш...")
        self.stop()
        time.sleep(0.1)  # Небольшая задержка перед перезапуском
        self.start()
        logger.info("Слушатель горячих клавиш перезапущен")
    
    def is_healthy(self) -> bool:
        """
        Проверка работоспособности
        
        Returns:
            True если работает нормально, False иначе
        """
        return self.is_running and self.hotkey_handler is not None
    
    def get_stats(self) -> dict:
        """
        Получение статистики работы горячих клавиш
        
        Returns:
            Словарь со статистикой
        """
        return {
            'is_running': self.is_running,
            'is_healthy': self.is_healthy(),
            'activation_count': self.activation_count,
            'last_activation_time': self.last_activation_time,
            'hotkey_string': self.hotkey_string,
            'virtual_key': self.virtual_key,
            'modifier_mask': self.modifier_mask,
        }
    
    def set_callback(self, callback: Callable):
        """Установка callback функции"""
        self.callback = callback
