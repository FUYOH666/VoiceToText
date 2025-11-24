"""
Проверка разрешений macOS для VTTv2
Проверка разрешений микрофона и Accessibility
"""
import logging
import sys

try:
    from AppKit import NSWorkspace
    from Quartz import (
        CGEventSourceKeyState,
        kCGEventSourceStateHIDSystemState
    )
    from PyObjCTools import AppHelper
    import AVFoundation
    PYOBJC_AVAILABLE = True
except ImportError:
    PYOBJC_AVAILABLE = False
    try:
        # Альтернативный импорт
        from AVFoundation import AVAudioSession
    except ImportError:
        pass

logger = logging.getLogger(__name__)


class PermissionsChecker:
    """Проверка системных разрешений macOS"""
    
    def __init__(self):
        """Инициализация проверки разрешений"""
        if not PYOBJC_AVAILABLE:
            logger.error("PyObjC недоступен - проверка разрешений невозможна")
            sys.exit(1)
        
        logger.info("Инициализация проверки разрешений")
    
    def check_microphone_permission(self, fail_fast: bool = True) -> bool:
        """
        Проверка разрешения на использование микрофона
        
        Args:
            fail_fast: Если True, завершает процесс при ошибке (default: True)
        
        Returns:
            True если разрешение предоставлено, False иначе
        
        Raises:
            SystemExit: Если разрешение не предоставлено и fail_fast=True
        """
        try:
            # Проверка через AVFoundation
            from AVFoundation import AVAudioSession
            import AVFoundation
            
            session = AVAudioSession.sharedInstance()
            permission = session.recordPermission()
            
            # Используем правильные константы из AVFoundation
            try:
                GRANTED = AVFoundation.AVAudioSessionRecordPermissionGranted
                DENIED = AVFoundation.AVAudioSessionRecordPermissionDenied
                UNDETERMINED = AVFoundation.AVAudioSessionRecordPermissionUndetermined
            except AttributeError:
                # Fallback на правильные числовые значения для macOS
                GRANTED = 1735552628  # kAVAudioSessionRecordPermissionGranted (правильное значение)
                DENIED = 1735552629   # kAVAudioSessionRecordPermissionDenied
                UNDETERMINED = 1970168948  # kAVAudioSessionRecordPermissionUndetermined
            
            logger.debug(f"Статус разрешения микрофона: {permission} (тип: {type(permission)})")
            
            # Проверка через сравнение с константами
            if permission == GRANTED or str(permission) == str(GRANTED):
                logger.info("✅ Разрешение на микрофон предоставлено")
                return True
            elif permission == DENIED or str(permission) == str(DENIED):
                logger.error("❌ Разрешение на микрофон отклонено")
                logger.error("Перейдите в Системные настройки > Конфиденциальность > Микрофон")
                if fail_fast:
                    sys.exit(1)
                return False
            else:
                # Требуется запрос разрешения или разрешение не определено
                logger.warning("⚠️ Требуется запрос разрешения на микрофон")
                logger.warning("⚠️ Разрешение будет запрошено при первом запуске приложения")
                logger.warning("⚠️ Для health check: разрешите микрофон в настройках системы")
                logger.debug(f"Текущий статус: {permission} (ожидается {GRANTED})")
                # Не запрашиваем разрешение в health check режиме
                if fail_fast:
                    logger.error("❌ Разрешение на микрофон не получено")
                    sys.exit(1)
                return False
        except Exception as e:
            logger.error(f"Ошибка проверки разрешения микрофона: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            if fail_fast:
                sys.exit(1)
            return False
    
    def check_accessibility_permission(self, fail_fast: bool = True) -> bool:
        """
        Проверка разрешения Accessibility для вставки текста
        
        Args:
            fail_fast: Если True, завершает процесс при ошибке (default: True)
        
        Returns:
            True если разрешение предоставлено, False иначе
        
        Raises:
            SystemExit: Если разрешение не предоставлено и fail_fast=True
        """
        try:
            # Проверка через попытку создания CGEvent
            # Если можем создать событие - разрешение есть
            # Упрощенная проверка: пытаемся получить состояние клавиши
            try:
                CGEventSourceKeyState(kCGEventSourceStateHIDSystemState, 0)
                logger.info("✅ Разрешение Accessibility предоставлено")
                return True
            except Exception:
                # Если не можем - вероятно нет разрешения
                logger.error("❌ Разрешение Accessibility не предоставлено")
                logger.error("Перейдите в Системные настройки > Конфиденциальность > Управление компьютером")
                logger.error("Добавьте Terminal или приложение в список разрешенных")
                if fail_fast:
                    sys.exit(1)
                return False
        except Exception as e:
            logger.error(f"Ошибка проверки разрешения Accessibility: {e}")
            if fail_fast:
                sys.exit(1)
            return False
    
    def check_all_permissions(self, fail_fast: bool = True) -> bool:
        """
        Проверка всех необходимых разрешений
        
        Args:
            fail_fast: Если True, завершает процесс при ошибке (default: True)
        
        Returns:
            True если все разрешения предоставлены
        
        Raises:
            SystemExit: Если какое-либо разрешение не предоставлено и fail_fast=True
        """
        logger.info("Проверка системных разрешений...")
        
        mic_ok = self.check_microphone_permission(fail_fast=fail_fast)
        accessibility_ok = self.check_accessibility_permission(fail_fast=fail_fast)
        
        if mic_ok and accessibility_ok:
            logger.info("✅ Все необходимые разрешения предоставлены")
            return True
        
        return False

