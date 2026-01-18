"""
Запись аудио с микрофона для VTTv2
"""
import logging
import numpy as np
import sounddevice as sd
import threading
import time
from typing import Optional, List

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Запись аудио с микрофона"""
    
    def __init__(self, config):
        """
        Инициализация записи аудио
        
        Args:
            config: Конфигурация приложения
        """
        self.config = config
        self.audio_config = config.audio
        
        self.sample_rate = self.audio_config.sample_rate
        self.channels = self.audio_config.channels
        self.device_index = self.audio_config.device_index
        self.chunk_size = self.audio_config.chunk_size
        self.max_duration = self.audio_config.max_recording_duration
        
        self.is_recording = False
        # Используем list вместо Queue для предотвращения потери данных
        # Блокировка обеспечивает потокобезопасность
        self.audio_chunks: List[np.ndarray] = []
        self._chunks_lock = threading.Lock()
        self.recorded_audio: List[np.ndarray] = []
        
        # Метрики для мониторинга производительности
        self._recording_start_time: Optional[float] = None
        self._total_chunks_recorded = 0
        
        logger.info(f"AudioRecorder инициализирован (sample_rate={self.sample_rate}, channels={self.channels})")
    
    def start_recording(self):
        """Начало записи аудио"""
        if self.is_recording:
            logger.warning("Запись уже идет, игнорируем повторный вызов")
            return
        
        # Проверяем, что предыдущий поток закрыт
        if hasattr(self, 'stream') and self.stream is not None:
            try:
                if self.stream.active:
                    logger.warning("Предыдущий поток записи все еще активен, останавливаем его")
                    self.stream.stop()
                    self.stream.close()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии предыдущего потока: {e}")
        
        self.is_recording = True
        self.recorded_audio = []
        
        # Очищаем список чанков перед началом новой записи
        with self._chunks_lock:
            self.audio_chunks.clear()
        
        # Сбрасываем метрики
        self._recording_start_time = time.time()
        self._total_chunks_recorded = 0
        
        def audio_callback(indata, frames, time_info, status):
            """Callback для записи аудио"""
            if status:
                logger.warning(f"Статус записи: {status}")
            
            if self.is_recording:
                try:
                    # Минимальное копирование - добавляем данные напрямую в список
                    # Используем блокировку для потокобезопасности
                    with self._chunks_lock:
                        # Копируем данные для безопасности (indata может быть переиспользован)
                        self.audio_chunks.append(indata.copy())
                        self._total_chunks_recorded += 1
                        
                        # Проверка максимальной длительности записи
                        if self._recording_start_time:
                            elapsed = time.time() - self._recording_start_time
                            # Предупреждение при приближении к лимиту (90% от максимума)
                            if elapsed >= self.max_duration * 0.9 and elapsed < self.max_duration:
                                remaining = self.max_duration - elapsed
                                logger.warning(
                                    f"Приближение к максимальной длительности записи: "
                                    f"осталось ~{remaining:.1f}с из {self.max_duration}с"
                                )
                            elif elapsed >= self.max_duration:
                                logger.warning(f"Достигнута максимальная длительность записи ({self.max_duration}с), останавливаем запись")
                                self.is_recording = False
                except Exception as e:
                    logger.error(f"Ошибка в audio_callback: {e}", exc_info=True)
        
        try:
            # Начало записи с измерением времени
            stream_create_start = time.time()
            
            # Начало записи
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device_index,
                blocksize=self.chunk_size,
                callback=audio_callback,
                dtype='float32'
            )
            
            stream_create_time = time.time() - stream_create_start
            stream_start_time = time.time()
            
            self.stream.start()
            
            stream_start_duration = time.time() - stream_start_time
            
            # Проверяем, что поток действительно запустился
            if not self.stream.active:
                raise RuntimeError("Поток записи не активировался")
            
            total_setup_time = time.time() - stream_create_start
            
            if total_setup_time > 0.1:
                logger.warning(
                    f"Медленная инициализация записи: создание={stream_create_time:.3f}с, "
                    f"старт={stream_start_duration:.3f}с, всего={total_setup_time:.3f}с"
                )
            else:
                logger.debug(f"Инициализация записи: создание={stream_create_time:.3f}с, старт={stream_start_duration:.3f}с")
            
            logger.info("Запись аудио начата")
        except Exception as e:
            logger.error(f"Ошибка начала записи: {e}", exc_info=True)
            self.is_recording = False
            # Очистка ресурсов при ошибке
            if hasattr(self, 'stream') and self.stream is not None:
                try:
                    self.stream.stop()
                    self.stream.close()
                except:
                    pass
            raise
    
    def stop_recording(self) -> Optional[np.ndarray]:
        """
        Остановка записи и возврат аудио данных
        
        Returns:
            numpy array с аудио данными или None при ошибке
        """
        if not self.is_recording:
            logger.warning("Запись не была начата")
            return None
        
        self.is_recording = False
        
        try:
            # Остановка потока с проверкой состояния
            if hasattr(self, 'stream') and self.stream is not None:
                try:
                    if self.stream.active:
                        logger.debug("Останавливаем активный поток записи")
                        self.stream.stop()
                    self.stream.close()
                    logger.debug("Поток записи закрыт")
                except Exception as stream_error:
                    logger.error(f"Ошибка при остановке потока: {stream_error}", exc_info=True)
            
            # Сборка всех записанных данных из списка
            # Используем блокировку для безопасного копирования и очистки
            with self._chunks_lock:
                audio_chunks = self.audio_chunks.copy()
                self.audio_chunks.clear()
            
            if not audio_chunks:
                logger.warning("Нет аудио данных в записи")
                return None
            
            # Логируем статистику записи
            if self._recording_start_time:
                actual_duration = time.time() - self._recording_start_time
                total_samples = sum(len(chunk) for chunk in audio_chunks)
                estimated_duration = total_samples / self.sample_rate
                logger.info(
                    f"Статистика записи: {len(audio_chunks)} чанков, "
                    f"{self._total_chunks_recorded} всего обработано, "
                    f"реальное время: {actual_duration:.2f}с, "
                    f"оценка аудио: {estimated_duration:.2f}с"
                )
            
            # Объединение всех чанков
            try:
                audio_data = np.concatenate(audio_chunks, axis=0)
            except Exception as concat_error:
                logger.error(f"Ошибка при объединении аудио чанков: {concat_error}", exc_info=True)
                return None
            
            # Конвертация в моно (если stereo)
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            duration = len(audio_data) / self.sample_rate
            logger.info(f"Запись остановлена: {duration:.2f} секунд, {len(audio_data)} сэмплов")
            
            return audio_data.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Ошибка остановки записи: {e}", exc_info=True)
            # Очистка ресурсов при ошибке
            try:
                if hasattr(self, 'stream') and self.stream is not None:
                    try:
                        self.stream.stop()
                    except:
                        pass
                    try:
                        self.stream.close()
                    except:
                        pass
            except:
                pass
            return None
    
    def cleanup(self):
        """Очистка ресурсов"""
        logger.debug("Очистка ресурсов AudioRecorder...")
        
        try:
            # Останавливаем запись, если она идет
            if self.is_recording:
                logger.info("Останавливаем активную запись при очистке...")
                self.is_recording = False
            
            # Закрываем поток
            if hasattr(self, 'stream') and self.stream is not None:
                try:
                    if self.stream.active:
                        logger.debug("Останавливаем активный поток...")
                        self.stream.stop()
                    self.stream.close()
                    logger.debug("Поток закрыт")
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии потока: {e}")
            
            # Очищаем список чанков
            try:
                with self._chunks_lock:
                    self.audio_chunks.clear()
            except Exception as e:
                logger.debug(f"Ошибка при очистке списка чанков: {e}")
            
            # Очищаем данные
            self.recorded_audio = []
            logger.debug("Ресурсы AudioRecorder очищены")
            
        except Exception as e:
            logger.error(f"Ошибка при очистке ресурсов AudioRecorder: {e}", exc_info=True)

