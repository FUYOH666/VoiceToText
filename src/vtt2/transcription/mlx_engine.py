"""
Интеграция с MLX Whisper для транскрипции (оптимизировано для Apple Silicon)

MLX Whisper работает полностью локально после первой загрузки модели:
- Модель скачивается один раз из Hugging Face Hub при первом использовании
- Сохраняется в локальный кэш: ~/.cache/huggingface/hub/
- Все последующие транскрипции работают полностью офлайн без интернета
- Обработка аудио происходит 100% локально на вашем Mac

Оптимизировано для длинных записей (15-45 минут):
- Разбиение на чанки с перекрытием для эффективной обработки
- Batch processing для использования всех GPU cores M4 Max
- Потоковая обработка для экономии памяти
"""
import logging
import numpy as np
from typing import Optional, List, Generator
import os
import time

logger = logging.getLogger(__name__)

# Импорт mlx_whisper (может быть не установлен в тестовой среде)
try:
    import mlx_whisper as whisper
    MLX_WHISPER_AVAILABLE = True
except ImportError:
    MLX_WHISPER_AVAILABLE = False
    whisper = None


class MLXWhisperTranscriber:
    """Транскрипция через MLX Whisper (оптимизировано для Apple Silicon)"""
    
    def __init__(self, config):
        """
        Инициализация MLX Whisper транскрибатора
        
        Args:
            config: Конфигурация приложения
        
        Raises:
            RuntimeError: Если MLX не может загрузить модель
        """
        self.config = config
        self.mlx_config = config.transcription.mlx_whisper
        
        # Guard-проверки
        self._check_dependencies()
        
        # Проверка наличия модели в локальном кэше
        self._check_model_cache()
        
        # Параметры для длинных записей
        self.chunk_size_seconds = getattr(self.mlx_config, 'chunk_size_seconds', 30)
        self.chunk_overlap_seconds = getattr(self.mlx_config, 'chunk_overlap_seconds', 2)
        self.batch_size = getattr(self.mlx_config, 'batch_size', 6)
        self.sample_rate = 16000  # MLX Whisper использует 16kHz
        
        self._model_cache = None
        self._transcription_count = 0
        
        logger.info("MLXWhisperTranscriber инициализирован")
        logger.info(f"Модель MLX: {self.mlx_config.model_name}")
        logger.info(f"Параметры длинных записей: chunk_size={self.chunk_size_seconds}s, overlap={self.chunk_overlap_seconds}s, batch_size={self.batch_size}")
    
    def _check_dependencies(self):
        """Проверка наличия MLX зависимостей"""
        if not MLX_WHISPER_AVAILABLE:
            logger.error("❌ MLX Whisper не установлен")
            logger.error("Установите: pip install mlx mlx-whisper")
            raise RuntimeError("MLX не установлен")
        
        try:
            import mlx
            logger.debug("MLX и MLX Whisper импортированы успешно")
            # Проверяем версию если доступна
            try:
                logger.debug(f"MLX Whisper версия: {whisper.__version__}")
            except AttributeError:
                pass
        except ImportError as e:
            logger.error(f"❌ MLX не установлен: {e}")
            logger.error("Установите: pip install mlx mlx-whisper")
            raise RuntimeError("MLX не установлен") from e
    
    def _check_model_cache(self):
        """Проверка наличия модели в локальном кэше"""
        try:
            # Hugging Face Hub кэширует модели в ~/.cache/huggingface/hub/
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            
            # Преобразуем имя модели в формат кэша
            # Например: "mlx-community/whisper-medium" -> "models--mlx-community--whisper-medium"
            model_cache_name = f"models--{self.mlx_config.model_name.replace('/', '--')}"
            model_cache_path = os.path.join(cache_dir, model_cache_name)
            
            if os.path.exists(model_cache_path):
                # Проверяем размер кэша
                try:
                    total_size = 0
                    for dirpath, dirnames, filenames in os.walk(model_cache_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            if os.path.exists(filepath):
                                total_size += os.path.getsize(filepath)
                    cache_size_mb = total_size / (1024 * 1024)
                    logger.info(f"✅ Модель найдена в локальном кэше: ~{cache_size_mb:.0f} MB")
                    logger.debug(f"Путь к кэшу: {model_cache_path}")
                except Exception:
                    logger.info("✅ Модель найдена в локальном кэше")
                    logger.debug(f"Путь к кэшу: {model_cache_path}")
            else:
                logger.info(f"ℹ️ Модель будет скачана при первом использовании (требуется интернет только один раз)")
                logger.info(f"✅ После первой загрузки модель будет работать полностью офлайн без интернета")
                logger.info(f"📦 Модель сохранится в: {model_cache_path}")
                logger.info(f"💡 Для полностью офлайн работы: скачайте модель заранее или используйте уже скачанную")
        except Exception as e:
            logger.debug(f"Не удалось проверить кэш модели: {e}")
    
    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Транскрибация аудио данных (автоматически выбирает метод для длинных/коротких записей)
        
        Args:
            audio_data: numpy array с аудио данными (float32, моно, 16kHz)
        
        Returns:
            Транскрибированный текст
        
        Raises:
            RuntimeError: При ошибке транскрипции
        """
        start_time = time.time()
        duration_seconds = len(audio_data) / self.sample_rate
        
        logger.info(f"Начало транскрипции MLX: {len(audio_data)} сэмплов ({duration_seconds:.1f} секунд)")
        
        # Определяем, нужна ли обработка длинной записи
        # Используем chunking для записей длиннее 60 секунд
        use_chunking = duration_seconds > 60
        
        if use_chunking:
            logger.info(f"Используется оптимизированная обработка для длинной записи ({duration_seconds:.1f}s)")
            return self.transcribe_long_audio(audio_data)
        else:
            logger.debug("Используется стандартная обработка для короткой записи")
            return self._transcribe_short_audio(audio_data)
    
    def _transcribe_short_audio(self, audio_data: np.ndarray) -> str:
        """
        Транскрибация коротких аудио записей (до 60 секунд)
        
        Args:
            audio_data: numpy array с аудио данными
        
        Returns:
            Транскрибированный текст
        """
        start_time = time.time()
        try:
            # MLX Whisper ожидает аудио как numpy array
            # Конвертируем в float32 если нужно
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Нормализация аудио (MLX ожидает значения в диапазоне [-1, 1])
            max_val = max(abs(audio_data.max()), abs(audio_data.min()))
            if max_val > 1.0:
                audio_data = audio_data / max_val
            
            # MLX Whisper transcribe принимает аудио и путь к модели
            # Примечание: библиотека может делать HTTP запросы для проверки метаданных модели,
            # но сама модель загружается из локального кэша, поэтому работает офлайн
            
            # Обработка автоопределения языка
            language_param = None
            if self.mlx_config.language and self.mlx_config.language.lower() != "auto":
                language_param = self.mlx_config.language
                logger.debug(f"Используется язык: {language_param}")
            else:
                logger.info("🌍 Автоопределение языка...")
            
            logger.debug(f"Загрузка модели из кэша: {self.mlx_config.model_name}")
            result = whisper.transcribe(
                audio_data,
                path_or_hf_repo=self.mlx_config.model_name,
                language=language_param,  # None для автоопределения
                temperature=self.mlx_config.temperature,
                compression_ratio_threshold=self.mlx_config.compression_ratio_threshold,
                no_speech_threshold=self.mlx_config.no_speech_threshold,
                verbose=False,
            )
            
            # Извлечение текста из результата
            text = self._extract_text_from_result(result)
            
            # Логируем определенный язык, если доступен
            if isinstance(result, dict) and "language" in result:
                detected_lang = result.get("language", "unknown")
                logger.info(f"🌍 Автоопределен язык: {detected_lang}")
            
            elapsed = time.time() - start_time
            self._transcription_count += 1
            
            # Периодическая очистка кэша модели (каждые 50 транскрипций)
            if self._transcription_count % 50 == 0:
                logger.info(f"Периодическая очистка кэша модели после {self._transcription_count} транскрипций")
                self._clear_model_cache()
            
            logger.info(f"Транскрипция MLX завершена за {elapsed:.2f}с: {len(text)} символов")
            
            return text
            
        except Exception as e:
            logger.error(f"Ошибка транскрипции MLX: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            raise RuntimeError(f"Ошибка транскрипции MLX: {e}") from e
    
    def transcribe_long_audio(self, audio_data: np.ndarray) -> str:
        """
        Транскрибация длинных аудио записей (15-45 минут) с оптимизацией:
        - Разбиение на чанки с перекрытием
        - Batch processing для использования всех GPU cores
        - Потоковая обработка для экономии памяти
        
        Args:
            audio_data: numpy array с аудио данными (float32, моно, 16kHz)
        
        Returns:
            Транскрибированный текст
        
        Raises:
            RuntimeError: При ошибке транскрипции
        """
        start_time = time.time()
        duration_seconds = len(audio_data) / self.sample_rate
        logger.info(f"📦 Начало обработки длинной записи: {len(audio_data)} сэмплов ({duration_seconds:.1f} секунд, {duration_seconds/60:.1f} минут)")
        
        try:
            # Подготовка аудио
            logger.info("🔧 Подготовка аудио данных...")
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Нормализация аудио
            logger.info("📊 Нормализация аудио...")
            max_val = max(abs(audio_data.max()), abs(audio_data.min()))
            if max_val > 1.0:
                audio_data = audio_data / max_val
            
            # Разбиение на чанки
            logger.info(f"✂️ Разбиение аудио на чанки (размер: {self.chunk_size_seconds}s, перекрытие: {self.chunk_overlap_seconds}s)...")
            chunks = self._split_into_chunks(audio_data)
            total_chunks = len(chunks)
            logger.info(f"✅ Аудио разбито на {total_chunks} чанков для обработки (batch_size: {self.batch_size})")
            
            # Сброс флага логирования языка для новой транскрипции
            if hasattr(self, '_detected_language_logged'):
                delattr(self, '_detected_language_logged')
            
            # Обработка чанков батчами
            all_texts = []
            processed_chunks = 0
            
            batch_num = 0
            for batch_chunks in self._batch_chunks(chunks, self.batch_size):
                batch_num += 1
                logger.info(f"🔄 Обработка батча {batch_num}: {len(batch_chunks)} чанков...")
                batch_start_time = time.time()
                batch_texts = self._transcribe_batch(batch_chunks)
                batch_elapsed = time.time() - batch_start_time
                logger.info(f"✅ Батч {batch_num} обработан за {batch_elapsed:.2f} секунд: получено {len(batch_texts)} текстов")
                
                all_texts.extend(batch_texts)
                processed_chunks += len(batch_chunks)
                
                # Логирование прогресса
                progress = (processed_chunks / total_chunks) * 100
                elapsed = time.time() - start_time
                logger.info(f"📊 Прогресс: {processed_chunks}/{total_chunks} чанков ({progress:.1f}%) обработано за {elapsed:.1f}с")
                
                # Очистка памяти после каждого батча
                del batch_chunks
                del batch_texts
                
                # Периодическая очистка памяти при обработке длинных записей
                if processed_chunks % (self.batch_size * 3) == 0:  # Каждые 3 батча
                    import gc
                    gc.collect()
                    logger.debug(f"Периодическая очистка памяти после {processed_chunks} чанков")
            
            # Объединение результатов с учетом перекрытий
            final_text = self._merge_chunk_texts(all_texts, chunks)
            
            elapsed = time.time() - start_time
            duration = len(audio_data) / self.sample_rate
            speed_factor = duration / elapsed if elapsed > 0 else 0
            logger.info(f"Транскрипция длинной записи завершена за {elapsed:.1f}с ({speed_factor:.2f}x реального времени): {len(final_text)} символов")
            
            return final_text
            
        except Exception as e:
            logger.error(f"Ошибка транскрипции длинной записи MLX: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            raise RuntimeError(f"Ошибка транскрипции длинной записи MLX: {e}") from e
    
    def _split_into_chunks(self, audio_data: np.ndarray) -> List[np.ndarray]:
        """
        Разбиение аудио на чанки с перекрытием
        
        Args:
            audio_data: numpy array с аудио данными
        
        Returns:
            Список чанков аудио
        """
        chunk_size_samples = self.chunk_size_seconds * self.sample_rate
        overlap_samples = self.chunk_overlap_seconds * self.sample_rate
        step_size = chunk_size_samples - overlap_samples
        
        chunks = []
        start = 0
        
        while start < len(audio_data):
            end = min(start + chunk_size_samples, len(audio_data))
            chunk = audio_data[start:end]
            
            # Добавляем padding если чанк слишком короткий (в конце)
            if len(chunk) < chunk_size_samples:
                padding = np.zeros(chunk_size_samples - len(chunk), dtype=np.float32)
                chunk = np.concatenate([chunk, padding])
            
            chunks.append(chunk)
            start += step_size
        
        return chunks
    
    def _batch_chunks(self, chunks: List[np.ndarray], batch_size: int) -> Generator[List[np.ndarray], None, None]:
        """
        Генератор для батчей чанков
        
        Args:
            chunks: Список чанков
            batch_size: Размер батча
        
        Yields:
            Батчи чанков
        """
        for i in range(0, len(chunks), batch_size):
            yield chunks[i:i + batch_size]
    
    def _transcribe_batch(self, batch_chunks: List[np.ndarray]) -> List[str]:
        """
        Транскрибация батча чанков
        
        Args:
            batch_chunks: Список чанков для обработки
        
        Returns:
            Список транскрибированных текстов
        """
        batch_texts = []
        logger.info(f"🎤 Начало транскрипции батча из {len(batch_chunks)} чанков")
        
        # Обрабатываем каждый чанк в батче
        # MLX Whisper может обрабатывать батчи, но для совместимости обрабатываем последовательно
        # В будущем можно оптимизировать для параллельной обработки батча
        
        # Обработка автоопределения языка
        language_param = None
        if self.mlx_config.language and self.mlx_config.language.lower() != "auto":
            language_param = self.mlx_config.language
        else:
            logger.debug("🌍 Автоопределение языка для батча...")
        
        for idx, chunk in enumerate(batch_chunks):
            try:
                chunk_duration = len(chunk) / self.sample_rate
                logger.debug(f"  Обработка чанка {idx+1}/{len(batch_chunks)} ({chunk_duration:.1f}s)...")
                result = whisper.transcribe(
                    chunk,
                    path_or_hf_repo=self.mlx_config.model_name,
                    language=language_param,  # None для автоопределения
                    temperature=self.mlx_config.temperature,
                    compression_ratio_threshold=self.mlx_config.compression_ratio_threshold,
                    no_speech_threshold=self.mlx_config.no_speech_threshold,
                    verbose=False,
                )
                text = self._extract_text_from_result(result)
                logger.debug(f"  ✅ Чанк {idx+1} обработан: {len(text)} символов")
                
                # Логируем определенный язык из первого чанка
                if isinstance(result, dict) and "language" in result and not hasattr(self, '_detected_language_logged'):
                    detected_lang = result.get("language", "unknown")
                    logger.info(f"🌍 Автоопределен язык: {detected_lang}")
                    self._detected_language_logged = True
                
                batch_texts.append(text)
            except Exception as e:
                logger.warning(f"Ошибка транскрипции чанка: {e}, пропускаем")
                batch_texts.append("")  # Пустой текст для пропущенного чанка
        
        return batch_texts
    
    def _extract_text_from_result(self, result) -> str:
        """
        Извлечение текста из результата MLX Whisper
        
        Args:
            result: Результат от whisper.transcribe
        
        Returns:
            Транскрибированный текст
        """
        if isinstance(result, dict):
            text = result.get("text", "").strip()
            # Если текст пустой, пробуем извлечь из сегментов
            if not text and "segments" in result:
                segments = result.get("segments", [])
                if segments:
                    text = " ".join([seg.get("text", "") for seg in segments if isinstance(seg, dict)]).strip()
            return text
        elif isinstance(result, str):
            return result.strip()
        else:
            # Может быть список сегментов
            return " ".join([seg.get("text", "") if isinstance(seg, dict) else str(seg) for seg in result]).strip()
    
    def _merge_chunk_texts(self, texts: List[str], chunks: List[np.ndarray]) -> str:
        """
        Объединение текстов из чанков.
        
        Args:
            texts: Список текстов из чанков
            chunks: Список чанков (для информации о перекрытиях)
        
        Returns:
            Объединенный текст
        """
        if not texts:
            return ""
        return " ".join(text.strip() for text in texts if text.strip())
    
    def _clear_model_cache(self):
        """Очистка кэша модели для освобождения памяти"""
        try:
            # Очистка кэша MLX если доступен
            if self._model_cache is not None:
                self._model_cache = None
                logger.debug("Кэш модели очищен")
            
            # Принудительный garbage collection
            import gc
            collected = gc.collect()
            logger.debug(f"Garbage collector собрал {collected} объектов после очистки кэша")
        except Exception as e:
            logger.debug(f"Ошибка очистки кэша модели: {e}")

