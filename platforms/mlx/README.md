# MLX Platform

[🇷🇺 Русская версия](#русская-версия)

Voice-to-Text application optimized for Apple Silicon using MLX Whisper framework.

## Features

- ⚡ **MLX optimized** for Apple Silicon
- 🚀 **Fast performance** (~12x real-time)
- 💾 **Lowest memory usage** (~1.5GB)
- 🔒 **100% offline** - no internet required
- 🆓 **Completely free** - no API keys needed
- 🎯 **Perfect for 8GB devices** - MacBook Air M1 8GB

## Requirements

- macOS with Apple Silicon (M1/M2/M3)
- Python 3.12
- MLX framework
- 8GB+ RAM recommended

## Installation

```bash
cd platforms/mlx
pip install -r requirements.txt
```

## Usage

```bash
python src/main.py
```

## Configuration

Edit `config.yaml` to customize settings:

```yaml
model: "large-v3"
language: "auto"
device: "mlx"
memory_limit: 8  # GB
```

## Performance

- **Speed**: ~12x real-time
- **Memory**: ~1.5GB
- **Accuracy**: High (optimized Whisper models)

## Optimizations

- Memory-efficient model loading
- Optimized for 8GB devices
- Native MLX framework integration
- Apple Silicon specific optimizations

## Troubleshooting

See [main README](../../README.md) for general troubleshooting.

## Documentation

For detailed documentation, see the original [VoiceToText-MLX-M1-8Gb repository](https://github.com/FUYOH666/VoiceToText-MLX-M1-8Gb).

---

## 🇷🇺 Русская версия

Приложение Voice-to-Text, оптимизированное для Apple Silicon с использованием фреймворка MLX Whisper.

## Возможности

- ⚡ **Оптимизировано MLX** для Apple Silicon
- 🚀 **Высокая производительность** (~12x реального времени)
- 💾 **Самое низкое использование памяти** (~1.5GB)
- 🔒 **100% офлайн** - интернет не требуется
- 🆓 **Полностью бесплатно** - API ключи не нужны
- 🎯 **Идеально для устройств 8GB** - MacBook Air M1 8GB

## Требования

- macOS с Apple Silicon (M1/M2/M3)
- Python 3.12
- Фреймворк MLX
- Рекомендуется 8GB+ RAM

## Установка

```bash
cd platforms/mlx
pip install -r requirements.txt
```

## Использование

```bash
python src/main.py
```

## Конфигурация

Отредактируйте `config.yaml` для настройки:

```yaml
model: "large-v3"
language: "auto"
device: "mlx"
memory_limit: 8  # GB
```

## Производительность

- **Скорость**: ~12x реального времени
- **Память**: ~1.5GB
- **Точность**: Высокая (оптимизированные модели Whisper)

## Оптимизации

- Эффективная загрузка моделей по памяти
- Оптимизировано для устройств 8GB
- Нативная интеграция фреймворка MLX
- Специфичные оптимизации Apple Silicon

## Устранение неполадок

См. [главный README](../../README.md) для общей помощи.

## Документация

Подробная документация доступна в оригинальном [репозитории VoiceToText-MLX-M1-8Gb](https://github.com/FUYOH666/VoiceToText-MLX-M1-8Gb).

