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
        kCGSessionEventTap,
        kCGEventFlagMaskCommand,
    )
    from AppKit import (
        NSPasteboard, 
        NSStringPboardType, 
        NSWorkspace,
    )
    # Константа для активации приложения
    NSApplicationActivateIgnoringOtherApps = 1 << 0
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
        self.saved_app = None  # Сохраненное активное приложение
        
        if not PYOBJC_AVAILABLE:
            logger.warning("PyObjC недоступен - автовставка невозможна, но приложение продолжит работу")
            # Не завершаем приложение, только предупреждаем
        
        logger.info(f"TextInjector инициализирован (метод: {self.method})")
    
    def save_active_app(self):
        """Сохранение текущего активного приложения"""
        try:
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.frontmostApplication()
            if active_app:
                self.saved_app = active_app.bundleIdentifier()
                app_name = active_app.localizedName() if hasattr(active_app, 'localizedName') else self.saved_app
                logger.info(f"💾 Сохранено активное приложение: {app_name} ({self.saved_app})")
                return True
            else:
                logger.warning("Не удалось получить активное приложение")
                return False
        except Exception as e:
            logger.warning(f"Не удалось сохранить активное приложение: {e}")
            return False
    
    def restore_active_app(self):
        """Восстановление активного приложения"""
        if not self.saved_app:
            logger.warning("Нет сохраненного приложения для восстановления")
            return False
        
        try:
            workspace = NSWorkspace.sharedWorkspace()
            running_apps = workspace.runningApplications()
            
            for app in running_apps:
                if app.bundleIdentifier() == self.saved_app:
                    logger.info(f"Активируем приложение: {self.saved_app}")
                    # Используем правильный метод активации
                    app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
                    logger.debug(f"Вызван activateWithOptions для: {self.saved_app}")
                    time.sleep(0.5)  # Увеличена задержка для активации
                    
                    # Проверяем что приложение действительно активно
                    active_app = workspace.frontmostApplication()
                    if active_app and active_app.bundleIdentifier() == self.saved_app:
                        logger.info(f"✅ Приложение успешно активировано: {self.saved_app}")
                        return True
                    else:
                        logger.warning(f"⚠️ Приложение не активировано. Активно: {active_app.bundleIdentifier() if active_app else 'None'}")
                        return False
            logger.warning(f"Приложение {self.saved_app} не найдено среди запущенных")
            return False
        except Exception as e:
            logger.error(f"Ошибка восстановления активного приложения: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
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
            # Сначала пробуем CGEvent с прямой вставкой (Cmd+V)
            logger.debug("Пробуем CGEvent с Cmd+V")
            if self._paste_via_cgevent(text):
                return True
            # Если не получилось, пробуем прямую типизацию
            logger.info("CGEvent Cmd+V не сработал, пробуем прямую типизацию")
            if self._paste_via_direct_typing(text):
                return True
            # Если не получилось, пробуем AppleScript
            logger.info("Прямая типизация не сработала, пробуем AppleScript")
            if self._paste_via_applescript(text):
                return True
            # Fallback на clipboard
            logger.warning("Все методы не сработали, используем clipboard")
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
            # Определяем активное приложение прямо перед вставкой (более надежно)
            workspace = NSWorkspace.sharedWorkspace()
            current_active_app = workspace.frontmostApplication()
            target_app_id = None
            
            if current_active_app:
                target_app_id = current_active_app.bundleIdentifier()
                app_name = current_active_app.localizedName() if hasattr(current_active_app, 'localizedName') else target_app_id
                logger.info(f"Текущее активное приложение перед вставкой: {app_name} ({target_app_id})")
            
            # Пробуем активировать сохраненное приложение, если оно отличается от текущего
            app_activated = False
            if self.saved_app and self.saved_app != target_app_id:
                logger.info(f"Пробуем активировать сохраненное приложение: {self.saved_app}")
                app_activated = self.restore_active_app()
                if app_activated:
                    logger.info("✅ Сохраненное приложение успешно активировано")
                else:
                    logger.info("Используем текущее активное приложение для вставки")
            elif target_app_id:
                # Используем текущее активное приложение
                logger.info(f"Используем текущее активное приложение для вставки: {target_app_id}")
                app_activated = True
            
            # Небольшая задержка для гарантии активации
            time.sleep(0.5)  # Задержка для надежной активации приложения
            
            # Сначала копируем в буфер обмена через NSPasteboard (более надежно)
            try:
                pasteboard = NSPasteboard.generalPasteboard()
                pasteboard.clearContents()
                pasteboard.setString_forType_(text, NSStringPboardType)
                logger.debug("Текст скопирован в буфер обмена через NSPasteboard")
            except Exception as e:
                logger.warning(f"Не удалось скопировать через NSPasteboard: {e}, используем pyperclip")
                pyperclip.copy(text)
            
            # Небольшая задержка для гарантии копирования
            time.sleep(0.3)  # Увеличена задержка для надежного копирования
            
            # Проверяем активное приложение перед вставкой (финальная проверка)
            final_active_app = workspace.frontmostApplication()
            if final_active_app:
                logger.info(f"Финальное активное приложение перед вставкой: {final_active_app.bundleIdentifier()}")
            
            # Эмуляция Cmd+V
            # Коды клавиш (macOS HID)
            cmd_key = 0x37  # Command (Left Command)
            v_key = 0x09    # V
            
            # Создаем события с правильными флагами
            # ВАЖНО: НЕ помечаем события как injected, чтобы приложения их принимали
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
            
            logger.debug("Отправка событий клавиатуры Cmd+V...")
            
            # Отправка событий в правильном порядке
            # Используем kCGSessionEventTap для глобальной вставки
            CGEventPost(kCGSessionEventTap, cmd_down)
            time.sleep(0.1)  # Увеличена задержка между событиями
            CGEventPost(kCGSessionEventTap, v_down)
            time.sleep(0.2)  # Увеличена задержка для обработки вставки
            CGEventPost(kCGSessionEventTap, v_up)
            time.sleep(0.1)
            CGEventPost(kCGSessionEventTap, cmd_up)
            
            # Небольшая задержка для проверки результата
            time.sleep(0.3)
            
            logger.info("✅ События Cmd+V отправлены через CGEvent")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка вставки через CGEvent: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Fallback на clipboard
            return False
    
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
            # Восстанавливаем активное приложение если сохранено
            if self.saved_app:
                self.restore_active_app()
            
            # Сначала копируем в буфер обмена
            pyperclip.copy(text)
            time.sleep(0.2)
            
            # AppleScript команда для вставки через Cmd+V
            # Более надежная версия с активацией активного приложения
            applescript = '''
            tell application "System Events"
                -- Активируем активное приложение
                set frontApp to first application process whose frontmost is true
                set frontAppName to name of frontApp
                tell application frontAppName to activate
                delay 0.2
                -- Вставляем текст
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
                # Пробуем упрощенную версию
                return self._paste_via_applescript_simple(text)
                
        except Exception as e:
            logger.error(f"Ошибка вставки через AppleScript: {e}")
            return self._paste_via_applescript_simple(text)
    
    def _paste_via_applescript_simple(self, text: str) -> bool:
        """Упрощенная версия AppleScript вставки"""
        try:
            # Упрощенная AppleScript команда
            applescript = 'tell application "System Events" to keystroke "v" using command down'
            
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info("✅ Текст вставлен через AppleScript (упрощенная версия)")
                return True
            else:
                logger.warning(f"Упрощенный AppleScript вернул ошибку: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Ошибка упрощенной вставки через AppleScript: {e}")
            return False
    
    def _paste_via_direct_typing(self, text: str) -> bool:
        """
        Вставка текста через прямую типизацию символов (альтернатива Cmd+V)
        Может работать лучше для некоторых приложений
        
        Args:
            text: Текст для вставки
        
        Returns:
            True если успешно
        """
        try:
            # Определяем активное приложение прямо перед вставкой
            workspace = NSWorkspace.sharedWorkspace()
            current_active_app = workspace.frontmostApplication()
            target_app_id = None
            
            if current_active_app:
                target_app_id = current_active_app.bundleIdentifier()
                app_name = current_active_app.localizedName() if hasattr(current_active_app, 'localizedName') else target_app_id
                logger.info(f"Текущее активное приложение для прямой типизации: {app_name} ({target_app_id})")
            
            # Пробуем активировать сохраненное приложение, если оно отличается от текущего
            if self.saved_app and self.saved_app != target_app_id:
                logger.info(f"Пробуем активировать сохраненное приложение: {self.saved_app}")
                app_activated = self.restore_active_app()
                if not app_activated:
                    logger.info("Используем текущее активное приложение для вставки")
            
            # Задержка для активации
            time.sleep(0.5)  # Задержка для надежной активации приложения
            
            # Типизируем каждый символ через CGEvent
            logger.debug(f"Начинаем прямую типизацию {len(text)} символов...")
            
            # Используем упрощенный подход - копируем в буфер и используем Cmd+V
            # но с более надежной активацией приложения
            try:
                pasteboard = NSPasteboard.generalPasteboard()
                pasteboard.clearContents()
                pasteboard.setString_forType_(text, NSStringPboardType)
                logger.debug("Текст скопирован в буфер обмена для прямой типизации")
            except Exception as e:
                logger.warning(f"Не удалось скопировать через NSPasteboard: {e}, используем pyperclip")
                pyperclip.copy(text)
            
            time.sleep(0.3)  # Увеличена задержка для надежного копирования
            
            # Просто отправляем Cmd+V более надежно
            # ВАЖНО: НЕ помечаем события как injected, чтобы приложения их принимали
            cmd_key = 0x37
            v_key = 0x09
            
            # Отправляем события с большими задержками
            cmd_down = CGEventCreateKeyboardEvent(None, cmd_key, True)
            CGEventSetFlags(cmd_down, kCGEventFlagMaskCommand)
            CGEventPost(kCGSessionEventTap, cmd_down)
            time.sleep(0.1)
            
            v_down = CGEventCreateKeyboardEvent(None, v_key, True)
            CGEventSetFlags(v_down, kCGEventFlagMaskCommand)
            CGEventPost(kCGSessionEventTap, v_down)
            time.sleep(0.2)
            
            v_up = CGEventCreateKeyboardEvent(None, v_key, False)
            CGEventSetFlags(v_up, kCGEventFlagMaskCommand)
            CGEventPost(kCGSessionEventTap, v_up)
            time.sleep(0.1)
            
            cmd_up = CGEventCreateKeyboardEvent(None, cmd_key, False)
            CGEventPost(kCGSessionEventTap, cmd_up)
            
            logger.info(f"✅ Отправлено Cmd+V через прямую типизацию")
            time.sleep(0.3)  # Увеличена задержка для завершения
            return True
            
        except Exception as e:
            logger.error(f"Ошибка прямой типизации: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

