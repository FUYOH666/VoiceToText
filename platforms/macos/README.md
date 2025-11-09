# macOS Platform

[🇷🇺 Русская версия](#русская-версия)

Voice-to-Text application for macOS using whisper.cpp and Core ML acceleration.

## Features

- 🍎 **Native macOS integration** with Core ML
- 🚀 **Fast performance** (~10x real-time)
- 💾 **Low memory usage** (~2GB)
- 🔒 **100% offline** - no internet required
- 🆓 **Completely free** - no API keys needed

## Requirements

- macOS 12.0 or later
- Python 3.12
- Core ML compatible device

## Installation

```bash
cd platforms/macos
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
device: "cpu"  # or "coreml"
```

## Performance

- **Speed**: ~10x real-time
- **Memory**: ~2GB
- **Accuracy**: High (Whisper models)

## Troubleshooting

See [main README](../../README.md) for general troubleshooting.

## Documentation

For detailed documentation, see the original [VoiceToText-MACos repository](https://github.com/FUYOH666/VoiceToText-MACos).

---

## 🇷🇺 Русская версия

Приложение Voice-to-Text для macOS с использованием whisper.cpp и ускорения Core ML.

## Возможности

- 🍎 **Нативная интеграция macOS** с Core ML
- 🚀 **Высокая производительность** (~10x реального времени)
- 💾 **Низкое использование памяти** (~2GB)
- 🔒 **100% офлайн** - интернет не требуется
- 🆓 **Полностью бесплатно** - API ключи не нужны

## Требования

- macOS 12.0 или новее
- Python 3.12
- Устройство с поддержкой Core ML

## Установка

```bash
cd platforms/macos
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
device: "cpu"  # или "coreml"
```

## Производительность

- **Скорость**: ~10x реального времени
- **Память**: ~2GB
- **Точность**: Высокая (модели Whisper)

## Устранение неполадок

См. [главный README](../../README.md) для общей помощи.

## Документация

Подробная документация доступна в оригинальном [репозитории VoiceToText-MACos](https://github.com/FUYOH666/VoiceToText-MACos).

