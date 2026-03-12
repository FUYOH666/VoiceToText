"""
VTTv2 - Главное приложение
Voice-to-Text для macOS с MLX Whisper
"""
import sys
import signal
import argparse
import threading
import time
from pathlib import Path
import rumps

from utils.logger import setup_logging
from config.loader import Config
from system.permissions import PermissionsChecker
from audio.recorder import AudioRecorder
from audio.processor import AudioProcessor
from transcription.engine import TranscriptionEngineWrapper
from system.text_injector import TextInjector
from system.hotkeys import HotkeyManager
from utils.memory_manager import MemoryManager
from utils.pid_manager import acquire_pid_file, release_pid_file

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
        
        # Состояние приложения (thread-safe через Lock)
        self._state_lock = threading.Lock()
        self._is_recording = False
        self._is_processing = False
        self.last_text = ""
        
        # Инициализация менеджера памяти для долгой работы
        cleanup_threshold = int(
            config.performance.memory_limit_mb * 
            (config.performance.cleanup_threshold_percent / 100)
        )
        self.memory_manager = MemoryManager(
            memory_limit_mb=config.performance.memory_limit_mb,
            cleanup_threshold_mb=cleanup_threshold
        )
        self.periodic_cleanup_interval = config.performance.periodic_cleanup_interval
        self.memory_manager.log_memory_usage("при старте")
        
        # Инициализация компонентов
        self._init_components()
        
        # Создание меню
        self._create_menu()
        
        # Запуск горячих клавиш
        self._start_hotkeys()
        
        self.logger.info("VTTv2 запущен")
    
    @property
    def is_recording(self):
        with self._state_lock:
            return self._is_recording

    @is_recording.setter
    def is_recording(self, value):
        with self._state_lock:
            self._is_recording = value

    @property
    def is_processing(self):
        with self._state_lock:
            return self._is_processing

    @is_processing.setter
    def is_processing(self, value):
        with self._state_lock:
            self._is_processing = value

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
            
            # Проверка Input Monitoring (требуется в macOS Sequoia 15+ для автовставки)
            input_monitoring_ok = permissions.check_input_monitoring_permission(fail_fast=False)
            if not input_monitoring_ok:
                self.logger.warning("⚠️ Разрешение Input Monitoring не предоставлено")
                self.logger.warning("⚠️ Автовставка может не работать")
                self.logger.warning("⚠️ Перейдите в Системные настройки > Конфиденциальность и безопасность > Мониторинг ввода")
                # Не завершаем приложение, но предупреждаем пользователя
                if self.config.ui.auto_paste_enabled:
                    rumps.alert(
                        "Требуется разрешение",
                        "Для автовставки текста требуется разрешение 'Мониторинг ввода'.\n\n"
                        "Перейдите в:\n"
                        "Системные настройки > Конфиденциальность и безопасность > Мониторинг ввода\n\n"
                        "Добавьте Terminal или это приложение в список разрешенных.",
                        ok="Понятно"
                    )
            
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
            rumps.MenuItem("🧹 Очистить память", callback=self.cleanup_memory),
            rumps.MenuItem("💾 Статус памяти", callback=self.show_memory_status),
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
        self.logger.info("🔥 Горячая клавиша нажата!")
        
        if self.is_processing:
            self.logger.warning("⚠️ Обработка уже идет, игнорируем нажатие")
            return
        
        if self.is_recording:
            self.logger.info("⏹️ Останавливаем запись...")
            self.stop_recording()
        else:
            self.logger.info("▶️ Начинаем запись...")
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
            # Сохраняем активное приложение ПЕРЕД началом записи (для автовставки)
            if self.config.ui.auto_paste_enabled:
                self.logger.debug("Сохранение активного приложения перед началом записи...")
                saved = self.text_injector.save_active_app()
                if not saved:
                    self.logger.warning("⚠️ Не удалось сохранить активное приложение, автовставка может не работать")
            
            self.is_recording = True
            self.title = self.config.menu_bar.icon_recording
            self._update_status("ЗАПИСЬ")
            
            self.audio_recorder.start_recording()
            self.logger.info("✅ Запись начата")
            
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
            
            # Остановка записи
            audio_data = self.audio_recorder.stop_recording()
            
            if audio_data is None or len(audio_data) == 0:
                self.logger.warning("Нет аудио данных")
                self.title = self.config.menu_bar.icon_idle
                self._update_status("Готов")
                return
            
            duration_seconds = len(audio_data) / self.config.audio.sample_rate
            self.logger.info(f"📊 Получено аудио: {len(audio_data)} сэмплов ({duration_seconds:.1f} секунд, {duration_seconds/60:.1f} минут)")
            
            # Обработка в отдельном потоке
            self.logger.info("🔄 Запуск потока обработки аудио...")
            threading.Thread(
                target=self._process_audio,
                args=(audio_data,),
                daemon=True
            ).start()
            self.logger.info("✅ Поток обработки запущен")
            
        except Exception as e:
            self.logger.error(f"Ошибка остановки записи: {e}")
            self.title = self.config.menu_bar.icon_idle
            self._update_status("Ошибка")
    
    def _process_audio(self, audio_data):
        """Обработка аудио в отдельном потоке"""
        try:
            self.logger.info("🎯 Начало обработки аудио в потоке")
            self.is_processing = True
            self._update_status("Транскрипция...")
            
            duration_seconds = len(audio_data) / self.config.audio.sample_rate
            self.logger.info(f"📊 Подготовка к транскрипции: {duration_seconds:.1f} секунд ({duration_seconds/60:.1f} минут)")
            
            # Мониторинг памяти перед транскрипцией
            self.memory_manager.monitor_and_cleanup_if_needed("перед транскрипцией")
            
            # Подготовка аудио
            self.logger.info("🔧 Подготовка аудио данных...")
            audio_data = self.audio_processor.prepare_for_whisper(audio_data)
            self.logger.info(f"✅ Аудио подготовлено: {len(audio_data)} сэмплов")
            
            # Транскрипция
            self.logger.info("🎤 Начало транскрипции...")
            start_time = time.time()
            text = self.transcription_engine.transcribe(audio_data)
            elapsed = time.time() - start_time
            self.logger.info(f"✅ Транскрипция завершена за {elapsed:.2f} секунд: {len(text)} символов")
            
            # Очистка памяти после транскрипции
            # Освобождаем ссылку на аудио данные
            del audio_data
            
            # Периодическая очистка памяти
            if not hasattr(self, '_transcription_count'):
                self._transcription_count = 0
            self._transcription_count += 1
            
            if self.config.performance.auto_cleanup_enabled:
                if self._transcription_count % self.periodic_cleanup_interval == 0:
                    self.logger.info(f"Периодическая очистка памяти после {self._transcription_count} транскрипций")
                    self.memory_manager.cleanup_memory()
                else:
                    # Лёгкая очистка после каждой транскрипции — gc.collect() для предотвращения накопления
                    self.memory_manager.light_cleanup()
                    self.memory_manager.monitor_and_cleanup_if_needed("после транскрипции")
            
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
            import traceback
            self.logger.debug(traceback.format_exc())
            
            # Попытка восстановления: очистка памяти и повторная инициализация компонентов
            try:
                self.logger.info("Попытка восстановления после ошибки...")
                self.memory_manager.cleanup_memory()
                
                # Переинициализация транскрипционного движка
                from transcription.engine import TranscriptionEngineWrapper
                self.transcription_engine = TranscriptionEngineWrapper(self.config)
                self.logger.info("✅ Компоненты переинициализированы")
            except Exception as recovery_error:
                self.logger.error(f"Ошибка восстановления: {recovery_error}")
            
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
        except Exception:
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
    
    @rumps.clicked("🧹 Очистить память")
    def cleanup_memory(self, _):
        """Очистка памяти"""
        try:
            self.memory_manager.log_memory_usage("до очистки")
            result = self.memory_manager.cleanup_memory()
            self.memory_manager.log_memory_usage("после очистки")
            
            if result.get('before') and result.get('after'):
                freed = result['before'].get('rss_mb', 0) - result['after'].get('rss_mb', 0)
                rumps.notification("VTTv2", "Память очищена", f"Освобождено ~{freed:.0f}MB")
            else:
                rumps.notification("VTTv2", "Память очищена", "")
        except Exception as e:
            self.logger.error(f"Ошибка очистки памяти: {e}")
            rumps.alert("Ошибка", f"Не удалось очистить память: {e}")
    
    @rumps.clicked("💾 Статус памяти")
    def show_memory_status(self, _):
        """Показ статуса памяти"""
        try:
            mem_info = self.memory_manager.get_memory_usage()
            if mem_info:
                status = (
                    f"RSS: {mem_info['rss_mb']:.0f}MB\n"
                    f"Система: {mem_info['system_percent']:.1f}%\n"
                    f"Свободно: {mem_info['system_available_gb']:.1f}GB"
                )
                rumps.alert("Статус памяти", status)
            else:
                rumps.alert("Статус памяти", "Не удалось получить информацию")
        except Exception as e:
            self.logger.error(f"Ошибка получения статуса памяти: {e}")
            rumps.alert("Ошибка", f"Не удалось получить статус: {e}")
    
    @rumps.clicked("❌ Выход")
    def quit_app(self, _):
        """Выход из приложения"""
        try:
            # Очистка перед выходом
            self.logger.info("Очистка перед выходом...")
            if hasattr(self, 'memory_manager'):
                self.memory_manager.cleanup_memory()
                self.memory_manager.cleanup_temp_files()

            # Остановка горячих клавиш с таймаутом (защита от зависания pynput)
            if hasattr(self, 'hotkey_manager'):
                HOTKEY_STOP_TIMEOUT = 2.0

                def stop_hotkeys():
                    try:
                        self.hotkey_manager.stop()
                    except Exception as e:
                        self.logger.debug(f"Ошибка при остановке горячих клавиш: {e}")

                stop_thread = threading.Thread(target=stop_hotkeys, daemon=True)
                stop_thread.start()
                stop_thread.join(timeout=HOTKEY_STOP_TIMEOUT)
                if stop_thread.is_alive():
                    self.logger.warning(
                        f"Остановка горячих клавиш заняла >{HOTKEY_STOP_TIMEOUT:.0f}с, выходим принудительно"
                    )

            if hasattr(self, 'audio_recorder'):
                self.audio_recorder.cleanup()
        except Exception as e:
            self.logger.error(f"Ошибка при выходе: {e}")
        finally:
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
    elif engine_type == "remote_asr":
        try:
            from transcription.remote_asr import RemoteASRTranscriber
            transcriber = RemoteASRTranscriber(config)
            if transcriber._check_health():
                checks["remote_asr"] = "✅"
            else:
                checks["remote_asr"] = "❌ ASR недоступен (проверьте Tailscale)"
        except Exception as e:
            checks["remote_asr"] = f"❌ {e}"

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
    
    # Проверяем только те ключи, которые должны быть ✅ (исключаем "engine" - это просто название)
    check_keys = [k for k in checks.keys() if k != "engine"]
    all_ok = all("✅" in str(checks[k]) for k in check_keys)
    
    if all_ok:
        print("\n✅ Все проверки пройдены - готово к запуску!")
        return 0
    else:
        print("\n⚠️ Некоторые проверки не пройдены, но приложение может работать")
        print("   Разрешения будут запрошены при первом запуске")
        return 0  # Возвращаем 0, так как это не критично для health check


def _resolve_project_root(config_path: str) -> Path:
    """Resolve project root directory based on config file location."""
    project_root = Path.cwd()
    if (project_root / config_path).exists():
        return project_root
    # Fallback: relative to this source file
    return Path(__file__).parent.parent.parent


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="VTTv2 - Voice-to-Text для macOS")
    parser.add_argument("--health", action="store_true", help="Run health check")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging")
    parser.add_argument("--install", action="store_true", help="Install as launchd service")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall launchd service")
    parser.add_argument("--status", action="store_true", help="Show service status")

    args = parser.parse_args()

    # Service management commands (no config needed)
    if args.install or args.uninstall or args.status:
        from service import install_service, uninstall_service, service_status
        if args.install:
            return install_service()
        elif args.uninstall:
            return uninstall_service()
        else:
            return service_status()

    if args.health:
        return health_check_command(args.config)

    # --- Normal app start ---
    project_root = _resolve_project_root(args.config)
    config_file = project_root / args.config

    try:
        config = Config.from_yaml(str(config_file), project_root)
    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        sys.exit(1)

    log_level = "DEBUG" if args.verbose else config.logging.level
    setup_logging(
        level=log_level,
        format_string=config.logging.format,
        log_file=config.logging.file,
    )

    # Single-instance guard
    if not acquire_pid_file():
        print("VTT2 already running. Use --status to check.")
        sys.exit(1)

    app = VTT2App(config)

    # Graceful shutdown on SIGTERM (sent by launchctl stop)
    def _handle_signal(signum, frame):
        import logging
        logging.getLogger("vtt2").info("Received signal %s, shutting down...", signum)
        app.quit_app(None)

    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        app.run()
    finally:
        release_pid_file()


if __name__ == "__main__":
    sys.exit(main())

