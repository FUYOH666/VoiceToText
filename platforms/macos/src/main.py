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
        self._hotkey_pending = False  # Защита от повторных вызовов горячих клавиш
        
        # Блокировка для защиты критических секций от состояний гонки
        # Используем RLock (реентерабельный) для возможности вложенных вызовов
        self._state_lock = threading.RLock()
        
        # Статистика для мониторинга долгосрочной стабильности
        self._operation_count = 0  # Счетчик операций записи/остановки
        self._last_health_check = time.time()  # Время последней проверки здоровья
        self._health_check_interval = 300  # Проверка здоровья каждые 5 минут
        
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
            try:
                mic_ok = permissions.check_microphone_permission(fail_fast=False)
                if not mic_ok:
                    # Пытаемся запросить разрешение интерактивно
                    try:
                        self._request_microphone_permission()
                        # Повторная проверка
                        mic_ok = permissions.check_microphone_permission(fail_fast=False)
                    except Exception as e:
                        self.logger.warning(f"Не удалось запросить разрешение микрофона: {e}")
                
                accessibility_ok = permissions.check_accessibility_permission(fail_fast=False)
            except Exception as e:
                self.logger.warning(f"Ошибка проверки разрешений: {e}, продолжаем работу")
                mic_ok = False
                accessibility_ok = False
            
            # Инициализация сервисов
            self.audio_recorder = AudioRecorder(self.config)
            self.audio_processor = AudioProcessor()
            try:
                self.transcription_engine = TranscriptionEngineWrapper(self.config)
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать движок транскрипции: {e}")
                self.logger.warning("Приложение будет работать, но транскрипция недоступна")
                self.transcription_engine = None
            
            try:
                self.text_injector = TextInjector(self.config)
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать TextInjector: {e}")
                self.logger.warning("Приложение будет работать, но автовставка недоступна")
                self.text_injector = None
            
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
        """Обработка нажатия горячей клавиши (вызывается из quickmachotkey)"""
        # quickmachotkey вызывает callback в главном потоке через NSApplication event loop
        # Но для безопасности используем AppHelper.callAfter если доступен
        if self._hotkey_pending:
            self.logger.debug("Горячая клавиша уже обрабатывается, игнорируем повторный вызов")
            return
        
        self.logger.info("🔔 Горячая клавиша активирована, планируем выполнение в главном потоке")
        
        if APPHELPER_AVAILABLE:
            self._hotkey_pending = True
            try:
                AppHelper.callAfter(self._handle_hotkey_in_main_thread)
                self.logger.debug("AppHelper.callAfter вызван успешно")
            except Exception as e:
                self.logger.error(f"Ошибка при вызове AppHelper.callAfter: {e}", exc_info=True)
                self._hotkey_pending = False
        else:
            # Fallback - quickmachotkey должен вызывать в главном потоке, но на всякий случай
            self._hotkey_pending = True
            try:
                self._handle_hotkey_in_main_thread()
            except Exception as e:
                self.logger.error(f"Ошибка при прямом вызове callback: {e}", exc_info=True)
                self._hotkey_pending = False
    
    def _handle_hotkey_in_main_thread(self):
        """Обработка горячей клавиши в главном потоке"""
        hotkey_start_time = time.time()
        try:
            self.logger.info(f"🔑 Обработка горячей клавиши в главном потоке: is_recording={self.is_recording}, is_processing={self.is_processing}, _hotkey_pending={self._hotkey_pending}")
            
            # Периодическая проверка здоровья компонентов - выполняем асинхронно, не блокируя обработку
            current_time = time.time()
            if current_time - self._last_health_check > self._health_check_interval:
                # Запускаем проверку в фоновом потоке, не блокируя обработку горячей клавиши
                threading.Thread(
                    target=self._perform_periodic_health_check,
                    daemon=True,
                    name="HealthCheck"
                ).start()
                self._last_health_check = current_time
            
            # Проверяем состояние (RLock позволяет вложенные вызовы)
            with self._state_lock:
                if self.is_processing:
                    self.logger.debug("Обработка идет, игнорируем горячую клавишу")
                    return
                
                # Определяем действие на основе текущего состояния
                should_stop = self.is_recording
            
            # Выполняем действие (методы сами используют RLock, поэтому это безопасно)
            action_start_time = time.time()
            if should_stop:
                self.logger.info("⏹️ Остановка записи по горячей клавише")
                self.stop_recording()
            else:
                self.logger.info("▶️ Начало записи по горячей клавише")
                self.start_recording()
            
            # Логируем время выполнения действия
            action_duration = time.time() - action_start_time
            total_duration = time.time() - hotkey_start_time
            if action_duration > 0.1 or total_duration > 0.2:
                self.logger.warning(
                    f"Медленная обработка горячей клавиши: действие={action_duration:.3f}с, "
                    f"всего={total_duration:.3f}с"
                )
            else:
                self.logger.debug(f"Обработка горячей клавиши: действие={action_duration:.3f}с, всего={total_duration:.3f}с")
            
            # Обновляем счетчик операций
            self._operation_count += 1
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки горячей клавиши: {e}", exc_info=True)
        finally:
            self._hotkey_pending = False
            total_time = time.time() - hotkey_start_time
            if total_time > 0.2:
                self.logger.warning(f"Общее время обработки горячей клавиши: {total_time:.3f}с")
            else:
                self.logger.debug(f"Общее время обработки горячей клавиши: {total_time:.3f}с")
    
    def _perform_periodic_health_check(self):
        """Периодическая проверка здоровья компонентов"""
        try:
            self.logger.debug("Выполнение периодической проверки здоровья...")
            
            # Проверка горячих клавиш
            if hasattr(self, 'hotkey_manager'):
                if not self.hotkey_manager.is_healthy():
                    self.logger.warning("Горячие клавиши не работают, пытаемся перезапустить...")
                    try:
                        self.hotkey_manager.restart()
                        self.logger.info("✅ Горячие клавиши успешно перезапущены")
                    except Exception as e:
                        self.logger.error(f"Ошибка перезапуска горячих клавиш: {e}")
            
            # Проверка состояния аудио
            if hasattr(self, 'audio_recorder'):
                if hasattr(self.audio_recorder, 'audio_chunks'):
                    chunks_count = len(self.audio_recorder.audio_chunks)
                    if chunks_count > 1000:  # Предупреждение при большом количестве чанков
                        self.logger.warning(f"Большое количество чанков аудио: {chunks_count} элементов")
            
            self.logger.debug(f"Проверка здоровья завершена (операций выполнено: {self._operation_count})")
            
        except Exception as e:
            self.logger.error(f"Ошибка при проверке здоровья: {e}", exc_info=True)
    
    @rumps.clicked("🎤 Начать запись")
    def toggle_recording(self, _):
        """Переключение записи"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """Начало записи"""
        with self._state_lock:
            if self.is_recording or self.is_processing:
                self.logger.debug(f"Запись уже идет или идет обработка: is_recording={self.is_recording}, is_processing={self.is_processing}")
                return
            
            try:
                self.is_recording = True
                self.title = self.config.menu_bar.icon_recording
                self._update_status("ЗАПИСЬ")
                
                self.audio_recorder.start_recording()
                self.logger.info("Запись начата")
                
            except Exception as e:
                self.logger.error(f"Ошибка начала записи: {e}", exc_info=True)
                self.is_recording = False
                self.title = self.config.menu_bar.icon_idle
                self._update_status("Ошибка")
                rumps.alert("Ошибка", f"Не удалось начать запись: {e}")
    
    def stop_recording(self):
        """Остановка записи и обработка"""
        self.logger.info(f"🛑 stop_recording вызван: is_recording={self.is_recording}, is_processing={self.is_processing}")
        with self._state_lock:
            if not self.is_recording:
                self.logger.warning("Попытка остановить запись, но запись не идет")
                return
            
            if self.is_processing:
                self.logger.warning("Попытка остановить запись во время обработки, игнорируем")
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
                    daemon=True,
                    name="AudioProcessor"
                ).start()
                
            except Exception as e:
                self.logger.error(f"Ошибка остановки записи: {e}", exc_info=True)
                self.is_recording = False
                self.title = self.config.menu_bar.icon_idle
                self._update_status("Ошибка")
    
    def _process_audio(self, audio_data):
        """Обработка аудио в отдельном потоке"""
        try:
            with self._state_lock:
                if self.is_processing:
                    self.logger.warning("Обработка уже идет, игнорируем новый запрос")
                    return
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
            
            # Автовставка (в главном потоке через AppHelper.callAfter для правильной работы CGEvent)
            if self.config.ui.auto_paste_enabled:
                self.logger.info(f"Автовставка текста: {len(text)} символов")
                
                # Используем threading.Timer для задержки, затем AppHelper.callAfter для выполнения в главном потоке
                def schedule_paste():
                    """Планирование вставки с задержкой"""
                    try:
                        self.logger.info("Планирование автовставки с задержкой 0.3с...")
                        # Небольшая задержка для гарантии активации приложения
                        time.sleep(0.3)
                        
                        # Выполняем вставку в главном потоке через AppHelper
                        if APPHELPER_AVAILABLE:
                            self.logger.info("Вызов AppHelper.callAfter для выполнения вставки в главном потоке")
                            def do_paste():
                                try:
                                    self.logger.info("Выполнение автовставки через AppHelper.callAfter")
                                    success = self.text_injector.paste_text(text)
                                    if success:
                                        self.logger.info("✅ Автовставка выполнена успешно")
                                    else:
                                        self.logger.warning("⚠️ Автовставка не удалась, текст скопирован в буфер обмена")
                                except Exception as e:
                                    self.logger.error(f"Ошибка автовставки: {e}", exc_info=True)
                            
                            # С quickmachotkey не нужна очистка состояния - нет проблем с injected событиями
                            AppHelper.callAfter(do_paste)
                        else:
                            # Fallback - выполняем напрямую
                            self.logger.warning("AppHelper недоступен, выполняем вставку напрямую")
                            try:
                                success = self.text_injector.paste_text(text)
                                if success:
                                    self.logger.info("✅ Автовставка выполнена успешно")
                                else:
                                    self.logger.warning("⚠️ Автовставка не удалась, текст скопирован в буфер обмена")
                                # С quickmachotkey не нужна очистка состояния - нет проблем с injected событиями
                            except Exception as e:
                                self.logger.error(f"Ошибка автовставки: {e}", exc_info=True)
                    except Exception as e:
                        self.logger.error(f"Ошибка планирования автовставки: {e}", exc_info=True)
                
                # Запускаем планирование в фоновом потоке
                self.logger.info("Запуск потока планирования автовставки...")
                threading.Thread(target=schedule_paste, daemon=True, name="PasteScheduler").start()
            
            self.last_text = text
            self._finalize_processing(text)
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки аудио: {e}", exc_info=True)
            try:
                self._finalize_processing(None)
            except Exception as finalize_error:
                self.logger.error(f"Критическая ошибка при завершении обработки: {finalize_error}", exc_info=True)
    
    def _finalize_processing(self, text):
        """Завершение обработки"""
        with self._state_lock:
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
        except Exception as e:
            self.logger.error(f"Ошибка проверки разрешений: {e}")
            checks.append("Разрешения: ❌")
        
        # Проверка компонентов
        checks.append(f"AudioRecorder: {'✅' if hasattr(self, 'audio_recorder') else '❌'}")
        checks.append(f"TranscriptionEngine: {'✅' if hasattr(self, 'transcription_engine') else '❌'}")
        checks.append(f"TextInjector: {'✅' if hasattr(self, 'text_injector') else '❌'}")
        
        # Проверка горячих клавиш
        if hasattr(self, 'hotkey_manager'):
            hotkey_healthy = self.hotkey_manager.is_healthy()
            hotkey_stats = self.hotkey_manager.get_stats()
            checks.append(f"Горячие клавиши: {'✅' if hotkey_healthy else '❌'}")
            checks.append(f"  - Активаций: {hotkey_stats['activation_count']}")
            checks.append(f"  - Комбинация: {hotkey_stats['hotkey_string']}")
            if not hotkey_healthy:
                self.logger.warning("Горячие клавиши не работают, пытаемся перезапустить...")
                try:
                    self.hotkey_manager.restart()
                    checks.append("  - Перезапуск: ✅")
                except Exception as e:
                    self.logger.error(f"Ошибка перезапуска горячих клавиш: {e}")
                    checks.append("  - Перезапуск: ❌")
        else:
            checks.append("Горячие клавиши: ❌ (не инициализированы)")
        
        # Проверка текущего движка
        engine_name = {
            "mlx_whisper": "MLX Whisper",
            "whisper_cpp": "whisper.cpp"
        }.get(self.config.transcription.engine, self.config.transcription.engine)
        checks.append(f"Движок ({engine_name}): ✅")
        
        # Состояние приложения
        checks.append(f"Состояние: запись={'🟢' if self.is_recording else '⚪'}, обработка={'🟡' if self.is_processing else '⚪'}")
        
        status_text = "\n".join(checks)
        rumps.alert("Health Check", status_text)
    
    @rumps.clicked("❌ Выход")
    def quit_app(self, _):
        """Выход из приложения"""
        self.logger.info("Завершение работы приложения...")
        
        try:
            # Останавливаем запись, если она идет
            if self.is_recording:
                self.logger.info("Останавливаем активную запись перед выходом...")
                try:
                    self.audio_recorder.stop_recording()
                except Exception as e:
                    self.logger.error(f"Ошибка при остановке записи: {e}")
            
            # Останавливаем горячие клавиши
            if hasattr(self, 'hotkey_manager'):
                try:
                    self.hotkey_manager.stop()
                    self.logger.debug("Горячие клавиши остановлены")
                except Exception as e:
                    self.logger.error(f"Ошибка при остановке горячих клавиш: {e}")
            
            # Очистка ресурсов аудио
            if hasattr(self, 'audio_recorder'):
                try:
                    self.audio_recorder.cleanup()
                    self.logger.debug("AudioRecorder очищен")
                except Exception as e:
                    self.logger.error(f"Ошибка при очистке AudioRecorder: {e}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при завершении работы: {e}", exc_info=True)
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

