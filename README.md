# VoiceToText

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Linux%20%7C%20MLX-lightgrey)](README.md)

**Cross-platform Voice-to-Text application** with support for macOS, Linux, and Apple Silicon (MLX). Fully offline, private, and free.

[🇷🇺 Русская версия](#русская-версия)

## 🌟 Features

- 🎤 **High-quality transcription** using Whisper models
- 🔒 **100% offline** - no data leaves your device
- 🆓 **Completely free** - no subscriptions or API keys
- 🚀 **Fast performance** - optimized for each platform
- 📱 **Multiple platforms** - choose the best version for your system
- 🌍 **Multilingual support** - supports 99+ languages

## 📦 Platforms

| Platform | Backend | Best For | Status |
|----------|---------|----------|--------|
| **macOS** | whisper.cpp + Core ML | macOS users, offline processing | ✅ Stable |
| **Linux** | FasterWhisper (CPU/GPU) | Linux servers, GPU acceleration | ✅ Stable |
| **MLX** | MLX Whisper | MacBook Air M1 8GB, Apple Silicon | ✅ Stable |

## 🚀 Quick Start

### macOS

```bash
cd platforms/macos
pip install -r requirements.txt
python src/main.py
```

📖 See [macOS Platform Documentation](platforms/macos/README.md) for details.

### Linux

```bash
cd platforms/linux
./install.sh
# Follow platform-specific instructions
```

📖 See [Linux Platform Documentation](platforms/linux/README.md) for details.

### MLX (Apple Silicon)

```bash
cd platforms/mlx
pip install -r requirements.txt
python src/main.py
```

📖 See [MLX Platform Documentation](platforms/mlx/README.md) for details.

## 📚 Documentation

- 📊 [Platform Comparison](docs/PLATFORMS.md) - Compare features across platforms
- 🍎 [macOS Guide](platforms/macos/README.md) - macOS installation and usage
- 🐧 [Linux Guide](platforms/linux/README.md) - Linux installation and usage
- ⚡ [MLX Guide](platforms/mlx/README.md) - MLX installation and usage
- 🤝 [Contributing](CONTRIBUTING.md) - How to contribute
- 📝 [Changelog](CHANGELOG.md) - Version history

## 🛠️ Requirements

### macOS
- macOS 12.0 or later
- Python 3.12
- Core ML support

### Linux
- Linux (any distribution)
- Python 3.12
- CUDA (optional, for GPU acceleration)

### MLX
- macOS with Apple Silicon (M1/M2/M3)
- Python 3.12
- MLX framework

## 📊 Performance

| Platform | Speed | Memory | GPU Support |
|----------|-------|--------|-------------|
| macOS | ~10x real-time | Low | Core ML |
| Linux | ~15x real-time | Medium | CUDA |
| MLX | ~12x real-time | Low | MLX |

## 🎯 Use Cases

- 📝 **Transcription** - Convert audio to text
- 🎙️ **Voice notes** - Record and transcribe voice memos
- 📞 **Call transcription** - Transcribe phone calls
- 🎬 **Video subtitles** - Generate subtitles for videos
- 📚 **Accessibility** - Make audio content accessible

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [Cleaner-OS](https://github.com/FUYOH666/Cleaner-OS) - System cleanup tool
- [telegram-ai](https://github.com/FUYOH666/telegram-ai) - AI platform for Telegram
- [Scanovich.ai-audio-call](https://github.com/FUYOH666/Scanovich.ai-audio-call) - Call analysis system

## 👤 Author

**Aleksandr Mordvinov**
- 💬 Telegram: [@ScanovichAI](https://t.me/ScanovichAI)
- 🌐 Website: [scanovich.ai](https://scanovich.ai)

---

## 🇷🇺 Русская версия

**Кроссплатформенное приложение Voice-to-Text** с поддержкой macOS, Linux и Apple Silicon (MLX). Полностью офлайн, приватно и бесплатно.

## 🌟 Возможности

- 🎤 **Высококачественная транскрипция** с использованием моделей Whisper
- 🔒 **100% офлайн** - данные не покидают ваше устройство
- 🆓 **Полностью бесплатно** - без подписок и API ключей
- 🚀 **Высокая производительность** - оптимизировано для каждой платформы
- 📱 **Несколько платформ** - выберите лучшую версию для вашей системы
- 🌍 **Многоязычная поддержка** - поддерживает 99+ языков

## 📦 Платформы

| Платформа | Backend | Лучше для | Статус |
|-----------|---------|-----------|--------|
| **macOS** | whisper.cpp + Core ML | Пользователи macOS, офлайн обработка | ✅ Стабильно |
| **Linux** | FasterWhisper (CPU/GPU) | Linux серверы, GPU ускорение | ✅ Стабильно |
| **MLX** | MLX Whisper | MacBook Air M1 8GB, Apple Silicon | ✅ Стабильно |

## 🚀 Быстрый старт

### macOS

```bash
cd platforms/macos
pip install -r requirements.txt
python src/main.py
```

📖 Подробности в [документации macOS](platforms/macos/README.md).

### Linux

```bash
cd platforms/linux
./install.sh
# Следуйте инструкциям для вашей платформы
```

📖 Подробности в [документации Linux](platforms/linux/README.md).

### MLX (Apple Silicon)

```bash
cd platforms/mlx
pip install -r requirements.txt
python src/main.py
```

📖 Подробности в [документации MLX](platforms/mlx/README.md).

## 📚 Документация

- 📊 [Сравнение платформ](docs/PLATFORMS.md) - Сравнение функций платформ
- 🍎 [Руководство macOS](platforms/macos/README.md) - Установка и использование macOS
- 🐧 [Руководство Linux](platforms/linux/README.md) - Установка и использование Linux
- ⚡ [Руководство MLX](platforms/mlx/README.md) - Установка и использование MLX
- 🤝 [Участие в разработке](CONTRIBUTING.md) - Как внести вклад
- 📝 [История изменений](CHANGELOG.md) - История версий

## 🛠️ Требования

### macOS
- macOS 12.0 или новее
- Python 3.12
- Поддержка Core ML

### Linux
- Linux (любой дистрибутив)
- Python 3.12
- CUDA (опционально, для GPU ускорения)

### MLX
- macOS с Apple Silicon (M1/M2/M3)
- Python 3.12
- Фреймворк MLX

## 📊 Производительность

| Платформа | Скорость | Память | Поддержка GPU |
|-----------|----------|--------|---------------|
| macOS | ~10x реального времени | Низкая | Core ML |
| Linux | ~15x реального времени | Средняя | CUDA |
| MLX | ~12x реального времени | Низкая | MLX |

## 🎯 Применение

- 📝 **Транскрипция** - Преобразование аудио в текст
- 🎙️ **Голосовые заметки** - Запись и транскрипция голосовых мемо
- 📞 **Транскрипция звонков** - Транскрипция телефонных звонков
- 🎬 **Субтитры для видео** - Генерация субтитров для видео
- 📚 **Доступность** - Сделать аудио контент доступным

## 🤝 Участие в разработке

Вклад приветствуется! См. [CONTRIBUTING.md](CONTRIBUTING.md) для руководства.

## 📝 Лицензия

MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🔗 Связанные проекты

- [Cleaner-OS](https://github.com/FUYOH666/Cleaner-OS) - Инструмент очистки системы
- [telegram-ai](https://github.com/FUYOH666/telegram-ai) - AI платформа для Telegram
- [Scanovich.ai-audio-call](https://github.com/FUYOH666/Scanovich.ai-audio-call) - Система анализа звонков

## 👤 Автор

**Александр Мордвинов**
- 💬 Telegram: [@ScanovichAI](https://t.me/ScanovichAI)
- 🌐 Сайт: [scanovich.ai](https://scanovich.ai)

---

⭐️ *If you find this project useful, please consider giving it a star!*

*Если проект вам полезен, пожалуйста, поставьте звезду!*

