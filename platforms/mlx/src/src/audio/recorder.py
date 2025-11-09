"""
Запись аудио с микрофона для VTTv2
"""
import logging
import numpy as np
import sounddevice as sd
from typing import Optional, List
from queue import Queue

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
        
        logger.info(f"AudioRecorder инициализирован (sample_rate={self.sample_rate}, channels={self.channels})")
    
    def start_recording(self):
        """Начало записи аудио"""
        if self.is_recording:
            logger.warning("Запись уже идет")
            return
        
        self.is_recording = True
        self.recorded_audio = []
        self.audio_queue = Queue()
        
        def audio_callback(indata, frames, time_info, status):
            """Callback для записи аудио"""
            if status:
                logger.warning(f"Статус записи: {status}")
            
            if self.is_recording:
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
            # Остановка потока
            if hasattr(self, 'stream'):
                self.stream.stop()
                self.stream.close()
            
            # Сборка всех записанных данных
            audio_chunks = []
            while not self.audio_queue.empty():
                chunk = self.audio_queue.get()
                audio_chunks.append(chunk)
            
            if not audio_chunks:
                logger.warning("Нет аудио данных")
                return None
            
            # Объединение всех чанков
            audio_data = np.concatenate(audio_chunks, axis=0)
            
            # Конвертация в моно (если stereo)
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            duration = len(audio_data) / self.sample_rate
            logger.info(f"Запись остановлена: {duration:.2f} секунд, {len(audio_data)} сэмплов")
            
            return audio_data.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Ошибка остановки записи: {e}")
            return None
    
    def cleanup(self):
        """Очистка ресурсов"""
        if hasattr(self, 'stream') and self.stream.active:
            self.stream.stop()
            self.stream.close()
        
        self.is_recording = False
        self.recorded_audio = []

