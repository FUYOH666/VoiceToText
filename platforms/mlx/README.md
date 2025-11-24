# MLX Platform

[🇷🇺 Русская версия](#русская-версия)

Voice-to-Text application optimized for Apple Silicon using MLX Whisper framework.

## 🚀 Быстрый запуск

```bash
cd platforms/mlx && uv run python src/src/main.py
```

Для health check:

```bash
cd platforms/mlx && uv run python src/src/main.py --health
```

## Features

- ⚡ **MLX optimized** for Apple Silicon (M1/M2/M3/M4)
- 🚀 **Fast performance** (~42x real-time, tested on M4 Max)
  - 5-minute recording: ~6 seconds
  - 15-minute recording: ~20 seconds
  - 45-minute recording: ~1 minute
- 💾 **Efficient memory usage** (~1.5GB for medium model, ~3-4GB for large-v3 model)
- 🔒 **100% offline** - no internet required after initial model download
- 🆓 **Completely free** - no API keys needed
- 🎯 **Optimized for M4 Max** - supports long recordings (15-45 minutes) with large-v3 model
- 📦 **Chunked processing** - automatic splitting for long recordings with overlap
- ⚙️ **Batch processing** - utilizes all 40 GPU cores on M4 Max
- 🌍 **Auto language detection** - automatically detects language (Russian, Chinese, English, etc.)
- 🔄 **24/7 operation** - automatic memory management and error recovery for continuous operation

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.12+
- MLX framework
- 8GB+ RAM recommended (16GB+ for large-v3 model on M4 Max)
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

## Installation

Using `uv` (recommended):

```bash
cd platforms/mlx
uv sync
```

Or using `pip`:

```bash
cd platforms/mlx
pip install -r requirements.txt
```

## Usage

Quick start:

```bash
cd platforms/mlx
uv run python src/src/main.py
```

Health check:

```bash
cd platforms/mlx
uv run python src/src/main.py --health
```

## Configuration

Edit `config.yaml` to customize settings:

```yaml
transcription:
  mlx_whisper:
    model_name: "mlx-community/whisper-large-v3-mlx"  # large-v3 for M4 Max
    language: "auto"  # "auto" for automatic language detection, or language code: "ru", "en", "zh" (Chinese), "ja" (Japanese), etc.
    chunk_size_seconds: 30  # Chunk size for long recordings
    chunk_overlap_seconds: 2  # Overlap between chunks
    batch_size: 6  # Batch size for parallel processing (optimal for large-v3 on M4 Max)

performance:
  memory_limit_mb: 16384  # 16GB for M4 Max (128GB RAM)
  auto_cleanup_enabled: true  # Automatic memory cleanup
  cleanup_threshold_percent: 75  # Cleanup threshold (75% of limit)
  periodic_cleanup_interval: 10  # Cleanup every N transcriptions

audio:
  max_recording_duration: 7200  # 2 hours (supports 15-45 minute recordings)
```

## Performance

- **Speed**: ~42x real-time (tested on M4 Max)
  - 5-minute recording: ~6 seconds
  - 15-minute recording: ~20 seconds
  - 45-minute recording: ~1 minute
- **Memory**: ~1.5GB (medium model), ~3-4GB (large-v3 model)
- **Accuracy**: High (large-v3 model provides best quality)
- **Long recordings**: Optimized for 15-45 minute recordings with chunked processing

### 24/7 Operation

The application is optimized for continuous operation:

- **Automatic memory management**: Monitors and cleans memory when threshold is exceeded
- **Periodic cleanup**: Automatic memory cleanup every 10 transcriptions
- **Model cache cleanup**: Model cache cleared every 50 transcriptions
- **Error recovery**: Automatic memory cleanup and component reinitialization on errors
- **Manual control**: Menu items "🧹 Clear Memory" and "💾 Memory Status"

Configuration in `config.yaml`:

```yaml
performance:
  auto_cleanup_enabled: true  # Automatic cleanup
  cleanup_threshold_percent: 75  # Cleanup threshold (75% of limit)
  periodic_cleanup_interval: 10  # Cleanup every N transcriptions
```

### Speed Testing

Run transcription speed test:

```bash
cd platforms/mlx
uv run python test_transcription_speed.py
```

## Optimizations

- Memory-efficient model loading
- Chunked processing for long recordings (15-45 minutes)
- Batch processing utilizing all 40 GPU cores on M4 Max
- Automatic chunking with overlap for seamless text merging
- Stream processing to minimize memory usage
- Native MLX framework integration
- Apple Silicon specific optimizations (M1/M2/M3/M4)

## Troubleshooting

### Горячие клавиши не работают

Если горячие клавиши Option+Space не работают:

1. **Добавьте Terminal в Accessibility:**
   - Системные настройки > Конфиденциальность > Управление компьютером
   - Добавьте Terminal (или Python, если запускаете через другой способ)
   - Перезапустите приложение

2. **Проверьте логи:**
   ```bash
   cd platforms/mlx
   uv run python src/src/main.py
   ```
   Ищите сообщения:
   - `✅ Горячие клавиши активированы` - все хорошо
   - `⚠️ This process is not trusted!` - нужно добавить в Accessibility
   - `🔥 Горячая клавиша нажата!` - горячие клавиши работают

3. **Проверьте разрешения:**
   ```bash
   cd platforms/mlx
   uv run python src/src/main.py --health
   ```

### Автовставка не работает

Если текст не вставляется автоматически:

1. **Проверьте разрешение Accessibility** (см. выше)
2. **Сохраните активное приложение перед записью:**
   - Установите курсор в нужное место
   - Запустите запись (Option+Space)
   - Приложение автоматически сохранит активное окно
3. **Проверьте логи** - должны быть сообщения о вставке текста

See [main README](../../README.md) for general troubleshooting.

## Documentation

For detailed documentation, see the original [VoiceToText-MLX-M1-8Gb repository](https://github.com/FUYOH666/VoiceToText-MLX-M1-8Gb).

---

## 🇷🇺 Русская версия

Приложение Voice-to-Text, оптимизированное для Apple Silicon с использованием фреймворка MLX Whisper.

## 🚀 Быстрый запуск

```bash
cd platforms/mlx && uv run python src/src/main.py
```

Для health check:

```bash
cd platforms/mlx && uv run python src/src/main.py --health
```

## Возможности

- ⚡ **Оптимизировано MLX** для Apple Silicon (M1/M2/M3/M4)
- 🚀 **Высокая производительность** (~42x реального времени, протестировано на M4 Max)
  - 5-минутная запись: ~6 секунд
  - 15-минутная запись: ~20 секунд
  - 45-минутная запись: ~1 минута
- 💾 **Эффективное использование памяти** (~1.5GB для medium модели, ~3-4GB для large-v3)
- 🔒 **100% офлайн** - интернет не требуется после первой загрузки модели
- 🆓 **Полностью бесплатно** - API ключи не нужны
- 🎯 **Оптимизировано для M4 Max** - поддержка длинных записей (15-45 минут) с моделью large-v3
- 📦 **Обработка чанками** - автоматическое разбиение длинных записей с перекрытием
- ⚙️ **Batch processing** - использует все 40 GPU cores на M4 Max
- 🌍 **Автоопределение языка** - автоматически определяет язык (русский, китайский, английский и т.д.)
- 🔄 **Работа 24/7** - автоматическое управление памятью и восстановление после ошибок для непрерывной работы

## Требования

- macOS с Apple Silicon (M1/M2/M3/M4)
- Python 3.12+
- Фреймворк MLX
- Рекомендуется 8GB+ RAM (16GB+ для модели large-v3 на M4 Max)
- Менеджер пакетов [uv](https://github.com/astral-sh/uv) (рекомендуется)

## Установка

Используя `uv` (рекомендуется):

```bash
cd platforms/mlx
uv sync
```

Или используя `pip`:

```bash
cd platforms/mlx
pip install -r requirements.txt
```

## Использование

Быстрый запуск:

```bash
cd platforms/mlx
uv run python src/src/main.py
```

Health check:

```bash
cd platforms/mlx
uv run python src/src/main.py --health
```

## Конфигурация

Отредактируйте `config.yaml` для настройки:

```yaml
transcription:
  mlx_whisper:
    model_name: "mlx-community/whisper-large-v3-mlx"  # large-v3 для M4 Max
    language: "auto"  # "auto" для автоопределения языка, или код языка: "ru", "en", "zh" (китайский), "ja" (японский) и т.д.
    chunk_size_seconds: 30  # Размер чанка для длинных записей
    chunk_overlap_seconds: 2  # Перекрытие между чанками
    batch_size: 6  # Размер батча для параллельной обработки (оптимально для large-v3 на M4 Max)

performance:
  memory_limit_mb: 16384  # 16GB для M4 Max (128GB RAM)

audio:
  max_recording_duration: 7200  # 2 часа (поддержка записей 15-45 минут)
```

## Производительность

- **Скорость**: ~42x реального времени (по результатам тестирования на M4 Max)
  - 5-минутная запись: ~6 секунд
  - 15-минутная запись: ~20 секунд
  - 45-минутная запись: ~1 минута
- **Память**: ~1.5GB (модель medium), ~3-4GB (модель large-v3)
- **Точность**: Высокая (модель large-v3 обеспечивает лучшее качество)
- **Длинные записи**: Оптимизировано для записей 15-45 минут с обработкой чанками

### Долгая работа (24/7)

Приложение оптимизировано для работы целыми сутками без перезапуска:

- **Автоматическое управление памятью**: Мониторинг и очистка при превышении порога
- **Периодическая очистка**: Каждые 10 транскрипций выполняется автоматическая очистка памяти
- **Очистка кэша модели**: Каждые 50 транскрипций очищается кэш модели
- **Восстановление после ошибок**: Автоматическая очистка памяти и переинициализация компонентов
- **Ручное управление**: Пункты меню "🧹 Очистить память" и "💾 Статус памяти"

Настройка в `config.yaml`:

```yaml
performance:
  auto_cleanup_enabled: true  # Автоматическая очистка
  cleanup_threshold_percent: 75  # Порог для очистки (75% от лимита)
  periodic_cleanup_interval: 10  # Очистка каждые N транскрипций
```

### Тестирование скорости

Запустите тест скорости транскрипции:

```bash
cd platforms/mlx
uv run python test_transcription_speed.py
```

## Оптимизации

- Эффективная загрузка моделей по памяти
- Обработка чанками для длинных записей (15-45 минут)
- Batch processing с использованием всех 40 GPU cores на M4 Max
- Автоматическое разбиение на чанки с перекрытием для плавного объединения текста
- Потоковая обработка для минимизации использования памяти
- Нативная интеграция фреймворка MLX
- Специфичные оптимизации Apple Silicon (M1/M2/M3/M4)

## Устранение неполадок

См. [главный README](../../README.md) для общей помощи.

## Документация

Подробная документация доступна в оригинальном [репозитории VoiceToText-MLX-M1-8Gb](https://github.com/FUYOH666/VoiceToText-MLX-M1-8Gb).
