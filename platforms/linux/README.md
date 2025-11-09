# Linux Platform

[🇷🇺 Русская версия](#русская-версия)

Voice-to-Text application for Linux using FasterWhisper with CPU and GPU support.

## Features

- 🐧 **Linux optimized** for servers and desktops
- 🚀 **High performance** (~15x real-time with GPU)
- 💪 **GPU acceleration** with CUDA support
- 🔒 **100% offline** - no internet required
- 🆓 **Completely free** - no API keys needed

## Requirements

- Linux (any distribution)
- Python 3.12
- CUDA (optional, for GPU acceleration)
- NVIDIA GPU (for GPU mode)

## Installation

### Quick Install

```bash
cd platforms/linux
./install.sh
```

### Manual Install

```bash
cd platforms/linux
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
device: "cuda"  # or "cpu"
```

## Performance

- **Speed (CPU)**: ~5x real-time
- **Speed (GPU)**: ~15x real-time
- **Memory (CPU)**: ~4GB
- **Memory (GPU)**: ~6GB
- **Accuracy**: High (Whisper models)

## GPU Setup

For GPU acceleration, install CUDA:

```bash
# Ubuntu/Debian
sudo apt-get install nvidia-cuda-toolkit

# Verify installation
nvidia-smi
```

## Troubleshooting

See [main README](../../README.md) for general troubleshooting.

## Documentation

For detailed documentation, see the original [VoiceToText-Linux repository](https://github.com/FUYOH666/VoiceToText-Linux).

---

## 🇷🇺 Русская версия

Приложение Voice-to-Text для Linux с использованием FasterWhisper с поддержкой CPU и GPU.

## Возможности

- 🐧 **Оптимизировано для Linux** для серверов и десктопов
- 🚀 **Высокая производительность** (~15x реального времени с GPU)
- 💪 **Ускорение GPU** с поддержкой CUDA
- 🔒 **100% офлайн** - интернет не требуется
- 🆓 **Полностью бесплатно** - API ключи не нужны

## Требования

- Linux (любой дистрибутив)
- Python 3.12
- CUDA (опционально, для GPU ускорения)
- NVIDIA GPU (для GPU режима)

## Установка

### Быстрая установка

```bash
cd platforms/linux
./install.sh
```

### Ручная установка

```bash
cd platforms/linux
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
device: "cuda"  # или "cpu"
```

## Производительность

- **Скорость (CPU)**: ~5x реального времени
- **Скорость (GPU)**: ~15x реального времени
- **Память (CPU)**: ~4GB
- **Память (GPU)**: ~6GB
- **Точность**: Высокая (модели Whisper)

## Настройка GPU

Для GPU ускорения установите CUDA:

```bash
# Ubuntu/Debian
sudo apt-get install nvidia-cuda-toolkit

# Проверка установки
nvidia-smi
```

## Устранение неполадок

См. [главный README](../../README.md) для общей помощи.

## Документация

Подробная документация доступна в оригинальном [репозитории VoiceToText-Linux](https://github.com/FUYOH666/VoiceToText-Linux).

