"""
Интеграция с MLX Whisper для транскрипции (оптимизировано для Apple Silicon)

MLX Whisper работает полностью локально после первой загрузки модели:
- Модель скачивается один раз из Hugging Face Hub при первом использовании
- Сохраняется в локальный кэш: ~/.cache/huggingface/hub/
- Все последующие транскрипции работают полностью офлайн без интернета
- Обработка аудио происходит 100% локально на вашем Mac
"""
import logging
import numpy as np
from typing import Optional
import os

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
        
        logger.info("MLXWhisperTranscriber инициализирован")
        logger.info(f"Модель MLX: {self.mlx_config.model_name}")
    
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
                logger.info(f"ℹ️ Модель будет скачана при первом использовании (требуется интернет)")
                logger.info(f"После первой загрузки модель будет работать полностью офлайн")
                logger.debug(f"Ожидаемый путь к кэшу: {model_cache_path}")
        except Exception as e:
            logger.debug(f"Не удалось проверить кэш модели: {e}")
    
    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Транскрибация аудио данных
        
        Args:
            audio_data: numpy array с аудио данными (float32, моно, 16kHz)
        
        Returns:
            Транскрибированный текст
        
        Raises:
            RuntimeError: При ошибке транскрипции
        """
        import time
        start_time = time.time()
        
        logger.info(f"Начало транскрипции MLX: {len(audio_data)} сэмплов")
        
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
            # Модель загружается из локального кэша (если уже скачана) или из Hugging Face (только при первом использовании)
            # После первой загрузки модель работает полностью локально без интернета
            logger.debug(f"Загрузка модели из кэша или Hugging Face: {self.mlx_config.model_name}")
            result = whisper.transcribe(
                audio_data,
                path_or_hf_repo=self.mlx_config.model_name,
                language=self.mlx_config.language,
                temperature=self.mlx_config.temperature,
                compression_ratio_threshold=self.mlx_config.compression_ratio_threshold,
                no_speech_threshold=self.mlx_config.no_speech_threshold,
                verbose=False,
            )
            
            # Извлечение текста из результата
            # MLX Whisper возвращает словарь с ключом "text"
            if isinstance(result, dict):
                text = result.get("text", "").strip()
                # Если текст пустой, пробуем извлечь из сегментов
                if not text and "segments" in result:
                    segments = result.get("segments", [])
                    if segments:
                        text = " ".join([seg.get("text", "") for seg in segments if isinstance(seg, dict)]).strip()
            elif isinstance(result, str):
                text = result.strip()
            else:
                # Может быть список сегментов
                text = " ".join([seg.get("text", "") if isinstance(seg, dict) else str(seg) for seg in result]).strip()
            
            elapsed = time.time() - start_time
            logger.info(f"Транскрипция MLX завершена за {elapsed:.2f}с: {len(text)} символов")
            
            return text
            
        except Exception as e:
            logger.error(f"Ошибка транскрипции MLX: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            raise RuntimeError(f"Ошибка транскрипции MLX: {e}") from e

