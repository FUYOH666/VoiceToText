# Platform Comparison

[🇷🇺 Русская версия](#русская-версия)

## Overview

VoiceToText supports three platforms, each optimized for different use cases and hardware configurations.

## Quick Comparison Table

| Feature | macOS | Linux | MLX |
|---------|-------|-------|-----|
| **Backend** | whisper.cpp + Core ML | FasterWhisper | MLX Whisper |
| **OS Support** | macOS 12+ | Linux (any distro) | macOS (Apple Silicon) |
| **Python Version** | 3.12 | 3.12 | 3.12 |
| **GPU Support** | Core ML | CUDA (optional) | MLX |
| **CPU Support** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Offline** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Memory Usage** | Low (~2GB) | Medium (~4GB) | Low (~1.5GB) |
| **Speed** | ~10x real-time | ~15x real-time (GPU) | ~12x real-time |
| **Best For** | macOS desktop users | Linux servers | M1 MacBook Air 8GB |
| **Installation** | `pip install` | `./install.sh` | `pip install` |
| **Model Size** | Medium | Large | Small |

## Detailed Platform Information

### 🍎 macOS Platform

**Technology Stack:**
- Backend: whisper.cpp with Core ML acceleration
- Framework: Native macOS integration
- Models: Optimized Whisper models

**Strengths:**
- ✅ Native Core ML integration
- ✅ Optimized for Apple hardware
- ✅ Low memory footprint
- ✅ Easy installation via pip
- ✅ Excellent performance on Apple Silicon

**Use Cases:**
- macOS desktop users
- Offline transcription needs
- Privacy-focused users
- Apple ecosystem integration

**Requirements:**
- macOS 12.0 or later
- Python 3.12
- Core ML compatible device (most modern Macs)

**Performance:**
- Speed: ~10x real-time
- Memory: ~2GB
- Accuracy: High (Whisper models)

### 🐧 Linux Platform

**Technology Stack:**
- Backend: FasterWhisper
- Framework: PyTorch/CUDA
- Models: Full Whisper models

**Strengths:**
- ✅ GPU acceleration with CUDA
- ✅ High performance on servers
- ✅ Flexible deployment options
- ✅ Supports both CPU and GPU
- ✅ Best for batch processing

**Use Cases:**
- Linux servers
- Batch processing
- GPU-accelerated transcription
- CI/CD pipelines
- Cloud deployments

**Requirements:**
- Linux (any distribution)
- Python 3.12
- CUDA (optional, for GPU acceleration)
- NVIDIA GPU (for GPU mode)

**Performance:**
- Speed: ~5x real-time (CPU), ~15x (GPU)
- Memory: ~4GB (CPU), ~6GB (GPU)
- Accuracy: High (Whisper models)

### ⚡ MLX Platform

**Technology Stack:**
- Backend: MLX Whisper
- Framework: MLX (Apple's ML framework)
- Models: Optimized for Apple Silicon

**Strengths:**
- ✅ Optimized for Apple Silicon
- ✅ Lowest memory usage
- ✅ Fast inference on M1/M2/M3
- ✅ Perfect for 8GB devices
- ✅ Native MLX framework

**Use Cases:**
- MacBook Air M1 8GB
- Apple Silicon devices
- Memory-constrained environments
- Fast local transcription
- Mobile-like performance

**Requirements:**
- macOS with Apple Silicon (M1/M2/M3)
- Python 3.12
- MLX framework
- 8GB+ RAM recommended

**Performance:**
- Speed: ~12x real-time
- Memory: ~1.5GB
- Accuracy: High (optimized Whisper models)

## Performance Benchmarks

### Transcription Speed (relative to real-time)

| Platform | CPU Mode | GPU/Accelerated Mode |
|----------|----------|----------------------|
| macOS | ~8x | ~10x (Core ML) |
| Linux | ~5x | ~15x (CUDA) |
| MLX | N/A | ~12x (MLX) |

### Memory Usage

| Platform | Minimum | Recommended | Maximum |
|----------|---------|-------------|---------|
| macOS | 2GB | 4GB | 8GB |
| Linux (CPU) | 4GB | 8GB | 16GB |
| Linux (GPU) | 6GB | 12GB | 24GB |
| MLX | 1.5GB | 4GB | 8GB |

### Accuracy

All platforms use Whisper models, so **accuracy is consistent** across platforms. The difference is in:
- Speed (processing time)
- Resource usage (memory, CPU/GPU)
- Platform-specific optimizations

## Choosing the Right Platform

### Choose macOS if:
- ✅ You're on macOS
- ✅ You want native integration
- ✅ You need low memory usage
- ✅ You prefer easy installation
- ✅ You use Apple ecosystem

### Choose Linux if:
- ✅ You're on Linux
- ✅ You have GPU available
- ✅ You need maximum performance
- ✅ You're running on servers
- ✅ You need batch processing

### Choose MLX if:
- ✅ You have MacBook Air M1 8GB
- ✅ You need lowest memory usage
- ✅ You want optimized Apple Silicon performance
- ✅ You're on Apple Silicon device
- ✅ Memory is a constraint

## Migration Guide

If you're currently using one of the separate repositories:

1. **From VoiceToText-MACos**: Use `platforms/macos/`
2. **From VoiceToText-Linux**: Use `platforms/linux/`
3. **From VoiceToText-MLX-M1-8Gb**: Use `platforms/mlx/`

The code structure remains the same, just organized under `platforms/` directory.

## Support

For platform-specific issues:
- 🍎 macOS: See [macOS README](platforms/macos/README.md)
- 🐧 Linux: See [Linux README](platforms/linux/README.md)
- ⚡ MLX: See [MLX README](platforms/mlx/README.md)

For general questions: Open an issue or contact [@ScanovichAI](https://t.me/ScanovichAI)

---

## 🇷🇺 Русская версия

## Обзор

VoiceToText поддерживает три платформы, каждая оптимизирована для различных случаев использования и конфигураций оборудования.

## Быстрая сравнительная таблица

| Функция | macOS | Linux | MLX |
|---------|-------|-------|-----|
| **Backend** | whisper.cpp + Core ML | FasterWhisper | MLX Whisper |
| **Поддержка ОС** | macOS 12+ | Linux (любой дистр.) | macOS (Apple Silicon) |
| **Версия Python** | 3.12 | 3.12 | 3.12 |
| **Поддержка GPU** | Core ML | CUDA (опционально) | MLX |
| **Поддержка CPU** | ✅ Да | ✅ Да | ✅ Да |
| **Офлайн** | ✅ Да | ✅ Да | ✅ Да |
| **Использование памяти** | Низкое (~2GB) | Среднее (~4GB) | Низкое (~1.5GB) |
| **Скорость** | ~10x реального времени | ~15x реального времени (GPU) | ~12x реального времени |
| **Лучше для** | Пользователи macOS | Linux серверы | MacBook Air M1 8GB |
| **Установка** | `pip install` | `./install.sh` | `pip install` |
| **Размер модели** | Средний | Большой | Малый |

## Детальная информация о платформах

### 🍎 Платформа macOS

**Технологический стек:**
- Backend: whisper.cpp с ускорением Core ML
- Фреймворк: Нативная интеграция macOS
- Модели: Оптимизированные модели Whisper

**Преимущества:**
- ✅ Нативная интеграция Core ML
- ✅ Оптимизировано для оборудования Apple
- ✅ Низкое использование памяти
- ✅ Простая установка через pip
- ✅ Отличная производительность на Apple Silicon

**Применение:**
- Пользователи macOS
- Потребность в офлайн транскрипции
- Пользователи, заботящиеся о приватности
- Интеграция с экосистемой Apple

**Требования:**
- macOS 12.0 или новее
- Python 3.12
- Устройство с поддержкой Core ML (большинство современных Mac)

**Производительность:**
- Скорость: ~10x реального времени
- Память: ~2GB
- Точность: Высокая (модели Whisper)

### 🐧 Платформа Linux

**Технологический стек:**
- Backend: FasterWhisper
- Фреймворк: PyTorch/CUDA
- Модели: Полные модели Whisper

**Преимущества:**
- ✅ Ускорение GPU с CUDA
- ✅ Высокая производительность на серверах
- ✅ Гибкие варианты развертывания
- ✅ Поддержка CPU и GPU
- ✅ Лучше для пакетной обработки

**Применение:**
- Linux серверы
- Пакетная обработка
- GPU-ускоренная транскрипция
- CI/CD пайплайны
- Облачные развертывания

**Требования:**
- Linux (любой дистрибутив)
- Python 3.12
- CUDA (опционально, для GPU ускорения)
- NVIDIA GPU (для GPU режима)

**Производительность:**
- Скорость: ~5x реального времени (CPU), ~15x (GPU)
- Память: ~4GB (CPU), ~6GB (GPU)
- Точность: Высокая (модели Whisper)

### ⚡ Платформа MLX

**Технологический стек:**
- Backend: MLX Whisper
- Фреймворк: MLX (ML фреймворк Apple)
- Модели: Оптимизированы для Apple Silicon

**Преимущества:**
- ✅ Оптимизировано для Apple Silicon
- ✅ Самое низкое использование памяти
- ✅ Быстрый вывод на M1/M2/M3
- ✅ Идеально для устройств 8GB
- ✅ Нативный фреймворк MLX

**Применение:**
- MacBook Air M1 8GB
- Устройства Apple Silicon
- Ограниченные памятью среды
- Быстрая локальная транскрипция
- Мобильная производительность

**Требования:**
- macOS с Apple Silicon (M1/M2/M3)
- Python 3.12
- Фреймворк MLX
- Рекомендуется 8GB+ RAM

**Производительность:**
- Скорость: ~12x реального времени
- Память: ~1.5GB
- Точность: Высокая (оптимизированные модели Whisper)

## Бенчмарки производительности

### Скорость транскрипции (относительно реального времени)

| Платформа | CPU режим | GPU/Ускоренный режим |
|-----------|-----------|---------------------|
| macOS | ~8x | ~10x (Core ML) |
| Linux | ~5x | ~15x (CUDA) |
| MLX | N/A | ~12x (MLX) |

### Использование памяти

| Платформа | Минимум | Рекомендуется | Максимум |
|-----------|---------|--------------|----------|
| macOS | 2GB | 4GB | 8GB |
| Linux (CPU) | 4GB | 8GB | 16GB |
| Linux (GPU) | 6GB | 12GB | 24GB |
| MLX | 1.5GB | 4GB | 8GB |

### Точность

Все платформы используют модели Whisper, поэтому **точность одинакова** на всех платформах. Разница в:
- Скорости (время обработки)
- Использовании ресурсов (память, CPU/GPU)
- Платформо-специфичных оптимизациях

## Выбор правильной платформы

### Выберите macOS если:
- ✅ Вы на macOS
- ✅ Хотите нативную интеграцию
- ✅ Нужно низкое использование памяти
- ✅ Предпочитаете простую установку
- ✅ Используете экосистему Apple

### Выберите Linux если:
- ✅ Вы на Linux
- ✅ Есть GPU
- ✅ Нужна максимальная производительность
- ✅ Работаете на серверах
- ✅ Нужна пакетная обработка

### Выберите MLX если:
- ✅ У вас MacBook Air M1 8GB
- ✅ Нужно самое низкое использование памяти
- ✅ Хотите оптимизированную производительность Apple Silicon
- ✅ Устройство Apple Silicon
- ✅ Память ограничена

## Руководство по миграции

Если вы используете один из отдельных репозиториев:

1. **Из VoiceToText-MACos**: Используйте `platforms/macos/`
2. **Из VoiceToText-Linux**: Используйте `platforms/linux/`
3. **Из VoiceToText-MLX-M1-8Gb**: Используйте `platforms/mlx/`

Структура кода остается той же, просто организована в директории `platforms/`.

## Поддержка

Для проблем, специфичных для платформы:
- 🍎 macOS: См. [README macOS](platforms/macos/README.md)
- 🐧 Linux: См. [README Linux](platforms/linux/README.md)
- ⚡ MLX: См. [README MLX](platforms/mlx/README.md)

Для общих вопросов: Откройте issue или свяжитесь с [@ScanovichAI](https://t.me/ScanovichAI)

