"""
VTTv2 - Главное приложение
Voice-to-Text для macOS с MLX Whisper
"""
import sys
import argparse
import threading
import time
from pathlib import Path
import rumps

# Импорт модулей
from utils.logger import setup_logging
from config.loader import Config
from system.permissions import PermissionsChecker
from audio.recorder import AudioRecorder
from audio.processor import AudioProcessor
from transcription.engine import TranscriptionEngineWrapper
from system.text_injector import TextInjector
from system.hotkeys import HotkeyManager

# Для выполнения в главном потоке
try:
    from PyObjCTools import AppHelper
    APPHELPER_AVAILABLE = True
except ImportError:
    APPHELPER_AVAILABLE = False


class VTT2App(rumps.App):
    """Главное приложение VTTv2"""
    
    def __init__(self, config: Config):
        """
        Инициализация приложения
        
        Args:
            config: Конфигурация приложения
        """
        # Инициализация rumps
        super().__init__(config.app.name, title=config.menu_bar.icon_idle)
        
        self.config = config
        self.logger = setup_logging(
            level=config.logging.level,
            format_string=config.logging.format,
            log_file=config.logging.file
        )
        
        # Состояние приложения
        self.is_recording = False
        self.is_processing = False
        self.last_text = ""
        
        # Инициализация компонентов
        self._init_components()
        
        # Создание меню
        self._create_menu()
        
        # Запуск горячих клавиш
        self._start_hotkeys()
        
        self.logger.info("VTTv2 запущен")
    
    def _init_components(self):
        """Инициализация всех компонентов"""
        try:
            # Проверка разрешений (fail_fast=True для обычного запуска)
            permissions = PermissionsChecker()
            
            # Проверяем разрешения с возможностью запроса
            mic_ok = permissions.check_microphone_permission(fail_fast=False)
            if not mic_ok:
                # Пытаемся запросить разрешение интерактивно
                self._request_microphone_permission()
                # Повторная проверка
                mic_ok = permissions.check_microphone_permission(fail_fast=True)
            
            accessibility_ok = permissions.check_accessibility_permission(fail_fast=True)
            
            # Инициализация сервисов
            self.audio_recorder = AudioRecorder(self.config)
            self.audio_processor = AudioProcessor()
            self.transcription_engine = TranscriptionEngineWrapper(self.config)
            self.text_injector = TextInjector(self.config)
            
            self.logger.info("Все компоненты инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
            rumps.alert("Ошибка", f"Не удалось инициализировать приложение: {e}")
            sys.exit(1)
    
    def _request_microphone_permission(self):
        """Запрос разрешения на микрофон интерактивно"""
        try:
            from AVFoundation import AVAudioSession
            
            session = AVAudioSession.sharedInstance()
            permission = session.recordPermission()
            
            UNDETERMINED = 1970168948  # kAVAudioSessionRecordPermissionUndetermined
            
            if permission == UNDETERMINED:
                self.logger.info("Запрос разрешения на микрофон...")
                # Запрашиваем разрешение (покажет системный диалог)
                session.requestRecordPermission_(lambda granted: None)
                # Небольшая задержка для обработки диалога
                import time
                time.sleep(0.5)
        except Exception as e:
            self.logger.warning(f"Не удалось запросить разрешение: {e}")
    
    def _create_menu(self):
        """Создание меню приложения"""
        self.menu = [
            rumps.MenuItem(f"📍 Статус: Готов", callback=None),
            rumps.separator,
            rumps.MenuItem("🎤 Начать запись", callback=self.toggle_recording),
            rumps.separator,
            rumps.MenuItem("📋 Копировать текст", callback=self.copy_text),
            rumps.MenuItem("📝 Показать текст", callback=self.show_text),
            rumps.separator,
            rumps.MenuItem("ℹ️ О программе", callback=self.show_about),
            rumps.MenuItem("🔍 Health Check", callback=self.health_check),
            rumps.separator,
            rumps.MenuItem("❌ Выход", callback=self.quit_app),
        ]
    
    def _start_hotkeys(self):
        """Запуск горячих клавиш"""
        try:
            hotkey_string = self.config.ui.hotkey
            self.hotkey_manager = HotkeyManager(hotkey_string, callback=self._on_hotkey_pressed)
            self.hotkey_manager.start()
            self.logger.info(f"Горячие клавиши активированы: {hotkey_string}")
        except Exception as e:
            self.logger.error(f"Ошибка горячих клавиш: {e}")
    
    def _on_hotkey_pressed(self):
        """Обработка нажатия горячей клавиши"""
        if self.is_processing:
            return
        
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    @rumps.clicked("🎤 Начать запись")
    def toggle_recording(self, _):
        """Переключение записи"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """Начало записи"""
        if self.is_recording or self.is_processing:
            return
        
        try:
            self.is_recording = True
            self.title = self.config.menu_bar.icon_recording
            self._update_status("ЗАПИСЬ")
            
            self.audio_recorder.start_recording()
            self.logger.info("Запись начата")
            
        except Exception as e:
            self.logger.error(f"Ошибка начала записи: {e}")
            self.is_recording = False
            self.title = self.config.menu_bar.icon_idle
            self._update_status("Ошибка")
            rumps.alert("Ошибка", f"Не удалось начать запись: {e}")
    
    def stop_recording(self):
        """Остановка записи и обработка"""
        if not self.is_recording:
            return
        
        try:
            self.is_recording = False
            self._update_status("Обработка...")
            
            # Сохраняем активное приложение перед обработкой (для автовставки)
            if self.config.ui.auto_paste_enabled:
                self.logger.debug("Сохранение активного приложения перед транскрипцией...")
                saved = self.text_injector.save_active_app()
                if not saved:
                    self.logger.warning("⚠️ Не удалось сохранить активное приложение, автовставка может не работать")
            
            # Остановка записи
            audio_data = self.audio_recorder.stop_recording()
            
            if audio_data is None or len(audio_data) == 0:
                self.logger.warning("Нет аудио данных")
                self.title = self.config.menu_bar.icon_idle
                self._update_status("Готов")
                return
            
            # Обработка в отдельном потоке
            threading.Thread(
                target=self._process_audio,
                args=(audio_data,),
                daemon=True
            ).start()
            
        except Exception as e:
            self.logger.error(f"Ошибка остановки записи: {e}")
            self.title = self.config.menu_bar.icon_idle
            self._update_status("Ошибка")
    
    def _process_audio(self, audio_data):
        """Обработка аудио в отдельном потоке"""
        try:
            self.is_processing = True
            self._update_status("Транскрипция...")
            
            # Подготовка аудио
            audio_data = self.audio_processor.prepare_for_whisper(audio_data)
            
            # Транскрипция
            text = self.transcription_engine.transcribe(audio_data)
            
            if not text or not text.strip():
                self.logger.warning("Пустой результат транскрипции")
                self._finalize_processing(None)
                return
            
            # Автовставка (в главном потоке для правильной работы CGEvent)
            if self.config.ui.auto_paste_enabled:
                self.logger.info(f"Автовставка текста: {len(text)} символов")
                # Выполняем вставку в главном потоке через PyObjCTools
                if APPHELPER_AVAILABLE:
                    def do_paste():
                        try:
                            success = self.text_injector.paste_text(text)
                            if success:
                                self.logger.info("✅ Автовставка выполнена успешно")
                            else:
                                self.logger.warning("⚠️ Автовставка не удалась, текст скопирован в буфер обмена")
                        except Exception as e:
                            self.logger.error(f"Ошибка автовставки: {e}")
                    
                    AppHelper.callAfter(do_paste)
                else:
                    # Fallback - выполняем напрямую (может не работать в некоторых случаях)
                    try:
                        success = self.text_injector.paste_text(text)
                        if success:
                            self.logger.info("✅ Автовставка выполнена успешно")
                        else:
                            self.logger.warning("⚠️ Автовставка не удалась, текст скопирован в буфер обмена")
                    except Exception as e:
                        self.logger.error(f"Ошибка автовставки: {e}")
            
            self.last_text = text
            self._finalize_processing(text)
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки аудио: {e}")
            self._finalize_processing(None)
    
    def _finalize_processing(self, text):
        """Завершение обработки"""
        self.is_processing = False
        self.title = self.config.menu_bar.icon_idle
        
        if text:
            self._update_status("Готов")
            self.logger.info(f"Транскрипция завершена: {len(text)} символов")
        else:
            self._update_status("Ошибка")
    
    def _update_status(self, status: str):
        """Обновление статуса в меню"""
        if hasattr(self, 'menu') and self.menu:
            status_item = self.menu["📍 Статус: Готов"]
            status_item.title = f"📍 Статус: {status}"
    
    @rumps.clicked("📋 Копировать текст")
    def copy_text(self, _):
        """Копирование последнего текста"""
        if not self.last_text:
            rumps.alert("Нет текста", "Нет текста для копирования")
            return
        
        import pyperclip
        pyperclip.copy(self.last_text)
        rumps.notification("VTTv2", "Текст скопирован", "")
    
    @rumps.clicked("📝 Показать текст")
    def show_text(self, _):
        """Показ последнего текста"""
        if not self.last_text:
            rumps.alert("Нет текста", "Нет текста для отображения")
            return
        
        display_text = self.last_text[:500] + "..." if len(self.last_text) > 500 else self.last_text
        rumps.alert("Последний текст", display_text)
    
    @rumps.clicked("ℹ️ О программе")
    def show_about(self, _):
        """О программе"""
        # Определяем название движка для отображения
        engine_name = {
            "mlx_whisper": "MLX Whisper",
            "whisper_cpp": "whisper.cpp"
        }.get(self.config.transcription.engine, self.config.transcription.engine)
        
        rumps.alert(
            "VTTv2",
            f"Voice-to-Text для macOS\n\n"
            f"Версия: {self.config.app.version}\n"
            f"Движок: {engine_name}\n"
            f"Горячие клавиши: {self.config.ui.hotkey}"
        )
    
    @rumps.clicked("🔍 Health Check")
    def health_check(self, _):
        """Health check приложения"""
        checks = []
        
        # Проверка разрешений
        try:
            permissions = PermissionsChecker()
            mic_ok = permissions.check_microphone_permission()
            accessibility_ok = permissions.check_accessibility_permission()
            checks.append(f"Микрофон: {'✅' if mic_ok else '❌'}")
            checks.append(f"Accessibility: {'✅' if accessibility_ok else '❌'}")
        except:
            checks.append("Разрешения: ❌")
        
        # Проверка компонентов
        checks.append(f"AudioRecorder: {'✅' if hasattr(self, 'audio_recorder') else '❌'}")
        checks.append(f"TranscriptionEngine: {'✅' if hasattr(self, 'transcription_engine') else '❌'}")
        checks.append(f"TextInjector: {'✅' if hasattr(self, 'text_injector') else '❌'}")
        
        # Проверка текущего движка
        engine_name = {
            "mlx_whisper": "MLX Whisper",
            "whisper_cpp": "whisper.cpp"
        }.get(self.config.transcription.engine, self.config.transcription.engine)
        checks.append(f"Движок ({engine_name}): ✅")
        
        status_text = "\n".join(checks)
        rumps.alert("Health Check", status_text)
    
    @rumps.clicked("❌ Выход")
    def quit_app(self, _):
        """Выход из приложения"""
        if hasattr(self, 'hotkey_manager'):
            self.hotkey_manager.stop()
        rumps.quit_application()


def health_check_command(config_path: str = "config.yaml"):
    """Команда health check из CLI"""
    project_root = Path.cwd()
    if not (project_root / config_path).exists():
        # Попробуем найти относительно src/
        project_root = Path(__file__).parent.parent.parent
    
    config_file = project_root / config_path
    
    logger = setup_logging()
    logger.info("=== Health Check VTTv2 ===")
    
    checks = {}
    
    # Проверка конфигурации
    try:
        config = Config.from_yaml(str(config_file), project_root)
        checks["config"] = "✅"
        logger.info("Конфигурация: OK")
    except Exception as e:
        checks["config"] = f"❌ {e}"
        logger.error(f"Конфигурация: ERROR - {e}")
        return
    
    # Проверка разрешений (без fail_fast для health check)
    try:
        permissions = PermissionsChecker()
        checks["permissions_mic"] = "✅" if permissions.check_microphone_permission(fail_fast=False) else "❌"
        checks["permissions_accessibility"] = "✅" if permissions.check_accessibility_permission(fail_fast=False) else "❌"
    except Exception as e:
        logger.error(f"Разрешения: ERROR - {e}")
        checks["permissions"] = f"❌ {e}"
    
    # Проверка движка транскрипции
    engine_type = config.transcription.engine
    checks["engine"] = engine_type
    
    if engine_type == "mlx_whisper":
        try:
            from transcription.mlx_engine import MLXWhisperTranscriber
            transcriber = MLXWhisperTranscriber(config)
            checks["mlx_whisper"] = "✅"
        except Exception as e:
            checks["mlx_whisper"] = f"❌ {e}"
    elif engine_type == "whisper_cpp":
        try:
            from transcription.whisper_cpp import WhisperCppTranscriber
            transcriber = WhisperCppTranscriber(config)
            checks["whisper_cpp"] = "✅"
        except Exception as e:
            checks["whisper_cpp"] = f"❌ {e}"
    
    # Вывод результатов
    print("\n=== Результаты Health Check ===")
    for check, status in checks.items():
        print(f"{check}: {status}")
    
    # Дополнительная информация
    print("\n=== Инструкции ===")
    if checks.get("permissions_mic") == "❌":
        print("⚠️ Разрешение на микрофон не предоставлено:")
        print("   1. Системные настройки > Конфиденциальность > Микрофон")
        print("   2. Добавьте Terminal (или приложение) в список")
        print("   3. Или разрешение будет запрошено при первом запуске приложения")
    
    if checks.get("permissions_accessibility") == "❌":
        print("⚠️ Разрешение Accessibility не предоставлено:")
        print("   1. Системные настройки > Конфиденциальность > Управление компьютером")
        print("   2. Добавьте Terminal (или приложение) в список")
    
    all_ok = all("✅" in str(status) for status in checks.values())
    if all_ok:
        print("\n✅ Все проверки пройдены - готово к запуску!")
        return 0
    else:
        print("\n⚠️ Некоторые проверки не пройдены, но приложение может работать")
        print("   Разрешения будут запрошены при первом запуске")
        return 0  # Возвращаем 0, так как это не критично для health check


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="VTTv2 - Voice-to-Text для macOS")
    parser.add_argument(
        '--health',
        action='store_true',
        help='Выполнить health check'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Путь к config.yaml'
    )
    
    args = parser.parse_args()
    
    if args.health:
        return health_check_command(args.config)
    
    # Обычный запуск приложения
    project_root = Path.cwd()
    if not (project_root / args.config).exists():
        # Попробуем найти относительно src/
        project_root = Path(__file__).parent.parent.parent
    
    config_file = project_root / args.config
    
    # Загрузка конфигурации
    try:
        config = Config.from_yaml(str(config_file), project_root)
    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        sys.exit(1)
    
    # Инициализация логирования
    setup_logging(
        level=config.logging.level,
        format_string=config.logging.format,
        log_file=config.logging.file
    )
    
    # Запуск приложения
    app = VTT2App(config)
    app.run()


if __name__ == "__main__":
    sys.exit(main())

