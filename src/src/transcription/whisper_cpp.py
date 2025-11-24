"""
Интеграция с whisper.cpp для транскрипции
"""
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


class WhisperCppTranscriber:
    """Транскрипция через whisper.cpp"""
    
    def __init__(self, config):
        """
        Инициализация whisper.cpp транскрибатора
        
        Args:
            config: Конфигурация приложения
        
        Raises:
            FileNotFoundError: Если бинарник или модель не найдены (fail fast)
        """
        self.config = config
        self.whisper_config = config.transcription.whisper_cpp
        
        # Guard-проверки при инициализации
        self._check_binary()
        self._check_model()
        
        logger.info("WhisperCppTranscriber инициализирован")
    
    def _check_binary(self):
        """Проверка наличия бинарника whisper (guard-проверка)"""
        binary_path = Path(self.whisper_config.binary_path)
        
        if not binary_path.exists():
            logger.error(f"❌ Бинарник whisper.cpp не найден: {binary_path}")
            logger.error("Скомпилируйте whisper.cpp или укажите правильный путь в config.yaml")
            sys.exit(1)
        
        if not binary_path.is_file():
            logger.error(f"❌ Путь не является файлом: {binary_path}")
            sys.exit(1)
        
        # Проверка исполняемости
        if not (binary_path.stat().st_mode & 0o111):
            logger.warning(f"Файл не исполняемый: {binary_path}")
        
        logger.info(f"✅ Бинарник найден: {binary_path}")
    
    def _check_model(self):
        """Проверка наличия модели (guard-проверка)"""
        model_path = Path(self.whisper_config.model_path)
        
        if not model_path.exists():
            logger.error(f"❌ Модель не найдена: {model_path}")
            logger.error("Скачайте модель ggml-large-v3.bin и разместите в models/")
            logger.error("Или укажите правильный путь в config.yaml")
            sys.exit(1)
        
        if not model_path.is_file():
            logger.error(f"❌ Путь не является файлом: {model_path}")
            sys.exit(1)
        
        logger.info(f"✅ Модель найдена: {model_path} ({model_path.stat().st_size / 1024 / 1024:.1f} MB)")
    
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
        
        logger.info(f"Начало транскрипции: {len(audio_data)} сэмплов")
        
        # Сохранение аудио во временный WAV файл
        temp_wav = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                temp_wav = tmp.name
                # Сохранение как WAV файл
                sf.write(temp_wav, audio_data, self.config.audio.sample_rate, subtype='PCM_16')
                logger.debug(f"Аудио сохранено во временный файл: {temp_wav}")
            
            # Построение команды whisper.cpp
            cmd, output_file = self._build_command(temp_wav)
            
            logger.debug(f"Выполнение команды: {' '.join(cmd)}")
            
            # Запуск whisper.cpp
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.audio.max_recording_duration * 2  # Таймаут = 2x длительности записи
            )
            
            # Детальное логирование для отладки
            logger.debug(f"whisper.cpp stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"whisper.cpp stderr: {result.stderr}")
            
            if result.returncode != 0:
                logger.error(f"Ошибка whisper.cpp (код {result.returncode})")
                logger.error(f"Команда: {' '.join(cmd)}")
                logger.error(f"stderr: {result.stderr}")
                logger.error(f"stdout: {result.stdout}")
                
                # Попытка диагностики
                if "failed to initialize" in result.stderr.lower():
                    logger.error("Возможные причины:")
                    logger.error("1. Модель повреждена или несовместима")
                    logger.error("2. Недостаточно памяти")
                    logger.error("3. Core ML encoder не найден (если use_coreml=true)")
                    logger.error("Попробуйте отключить Core ML: use_coreml: false")
                
                raise RuntimeError(f"Ошибка транскрипции: {result.stderr}")
            
            # Парсинг результата из файла
            text = self._parse_output(output_file)
            
            # Удаление временного файла результата
            if Path(output_file).exists():
                Path(output_file).unlink()
                logger.debug(f"Временный файл результата удален: {output_file}")
            
            elapsed = time.time() - start_time
            logger.info(f"Транскрипция завершена за {elapsed:.2f}с: {len(text)} символов")
            
            return text.strip()
            
        except subprocess.TimeoutExpired:
            logger.error("Таймаут транскрипции")
            raise RuntimeError("Таймаут транскрипции")
        except Exception as e:
            logger.error(f"Ошибка транскрипции: {e}")
            raise
        finally:
            # Очистка временного файла
            if temp_wav and Path(temp_wav).exists():
                Path(temp_wav).unlink()
                logger.debug(f"Временный файл удален: {temp_wav}")
    
    def _build_command(self, wav_file: str) -> list:
        """Построение команды для whisper.cpp"""
        binary_path = Path(self.whisper_config.binary_path)
        cmd = [str(binary_path.resolve())]
        
        # Основные параметры
        cmd.extend(['-m', str(Path(self.whisper_config.model_path).resolve())])
        cmd.extend(['-l', self.whisper_config.language])
        cmd.extend(['-f', wav_file])
        
        # Опции производительности
        # Core ML и Metal автоматически используются если доступны
        # Флаги --coreml и --metal не поддерживаются в whisper-cli
        
        cmd.extend(['-t', str(self.whisper_config.threads)])
        
        # Параметры качества
        cmd.extend(['-tp', str(self.whisper_config.temperature)])
        cmd.extend(['-bs', str(self.whisper_config.beam_size)])
        cmd.extend(['-bo', str(self.whisper_config.best_of)])
        cmd.extend(['-nth', str(self.whisper_config.no_speech_threshold)])
        cmd.extend(['-et', str(self.whisper_config.compression_ratio_threshold)])
        
        # Вывод только текста в файл
        # Определяем имя выходного файла (без расширения)
        output_file = Path(wav_file).stem
        output_dir = Path(wav_file).parent
        output_path = output_dir / output_file
        
        cmd.append('-otxt')
        cmd.append('-nt')
        cmd.append('-np')  # Не печатать прогресс
        cmd.extend(['-of', str(output_path)])
        
        return cmd, str(output_path) + '.txt'
    
    def _parse_output(self, output_file: str) -> str:
        """
        Парсинг результата из файла whisper.cpp
        
        Args:
            output_file: Путь к файлу с результатом
        
        Returns:
            Транскрибированный текст
        """
        output_path = Path(output_file)
        
        if not output_path.exists():
            logger.error(f"Файл результата не найден: {output_file}")
            return ""
        
        # Чтение текста из файла
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            
            logger.debug(f"Прочитано {len(text)} символов из {output_file}")
            return text
        except Exception as e:
            logger.error(f"Ошибка чтения файла результата: {e}")
            return ""

