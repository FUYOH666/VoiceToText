"""
Запись аудио с микрофона для VTTv2
Оптимизировано для длинных записей (15-45 минут и более)
"""
import logging
import numpy as np
import sounddevice as sd
from typing import Optional, List
from queue import Queue
import time

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
        self.audio_queue: Queue = Queue()
        self.recorded_audio: List[np.ndarray] = []
        self.recording_start_time: Optional[float] = None
        self.last_progress_log_time: Optional[float] = None
        
        logger.info(f"AudioRecorder инициализирован (sample_rate={self.sample_rate}, channels={self.channels}, max_duration={self.max_duration}s)")
    
    def start_recording(self):
        """Начало записи аудио"""
        if self.is_recording:
            logger.warning("Запись уже идет")
            return
        
        self.is_recording = True
        self.recorded_audio = []
        self.audio_queue = Queue()
        self.recording_start_time = time.time()
        self.last_progress_log_time = self.recording_start_time
        
        def audio_callback(indata, frames, time_info, status):
            """Callback для записи аудио"""
            if status:
                logger.warning(f"Статус записи: {status}")
            
            if self.is_recording:
                # Проверка максимальной длительности
                current_time = time.time()
                elapsed = current_time - self.recording_start_time
                
                if elapsed >= self.max_duration:
                    logger.warning(f"Достигнута максимальная длительность записи ({self.max_duration}s), останавливаем запись")
                    self.is_recording = False
                    return
                
                # Логирование прогресса для длинных записей (каждые 30 секунд)
                if elapsed - (self.last_progress_log_time - self.recording_start_time) >= 30:
                    logger.info(f"Запись продолжается: {elapsed:.0f}s / {self.max_duration}s")
                    self.last_progress_log_time = current_time
                
                # Конвертация в numpy array
                audio_data = indata.copy()
                self.audio_queue.put(audio_data)
        
        try:
            # Начало записи
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device_index,
                blocksize=self.chunk_size,
                callback=audio_callback,
                dtype='float32'
            )
            self.stream.start()
            logger.info("Запись аудио начата")
        except Exception as e:
            logger.error(f"Ошибка начала записи: {e}")
            self.is_recording = False
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
            # Остановка потока: abort(), не stop() — stop() ждёт все буферы в PortAudio
            # и может зависнуть навсегда (сон Mac, Bluetooth, смена устройства).
            if hasattr(self, 'stream') and self.stream is not None:
                stream = self.stream
                self.stream = None
                try:
                    if not stream.closed and stream.active:
                        stream.abort(ignore_errors=True)
                    stream.close(ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Остановка аудиопотока: {e}")
            
            # Сборка всех записанных данных
            audio_chunks = []
            while not self.audio_queue.empty():
                chunk = self.audio_queue.get()
                audio_chunks.append(chunk)
            
            if not audio_chunks:
                logger.warning("Нет аудио данных")
                return None
            
            # Объединение всех чанков
            # Для длинных записей это может занять время, логируем прогресс
            if len(audio_chunks) > 100:  # Большое количество чанков
                logger.info(f"Объединение {len(audio_chunks)} чанков аудио...")
            
            audio_data = np.concatenate(audio_chunks, axis=0)
            
            # Конвертация в моно (если stereo)
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            duration = len(audio_data) / self.sample_rate
            size_mb = (audio_data.nbytes / (1024 * 1024))
            
            # Очистка промежуточных данных для экономии памяти
            del audio_chunks
            
            logger.info(f"Запись остановлена: {duration:.2f} секунд ({duration/60:.1f} минут), {len(audio_data)} сэмплов, ~{size_mb:.1f} MB")
            
            return audio_data.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Ошибка остановки записи: {e}")
            return None
    
    def cleanup(self):
        """Очистка ресурсов"""
        if hasattr(self, 'stream') and self.stream is not None and not self.stream.closed:
            try:
                if self.stream.active:
                    self.stream.abort(ignore_errors=True)
                self.stream.close(ignore_errors=True)
            except Exception as e:
                logger.warning(f"cleanup stream: {e}")
            self.stream = None
        
        self.is_recording = False
        self.recorded_audio = []
        self.recording_start_time = None
        self.last_progress_log_time = None

