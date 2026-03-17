# VoiceToText

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Linux%20%7C%20MLX-lightgrey)](README.md)

**Turn speech into text instantly — on your Mac, Linux server, or Apple Silicon. Fully offline, private, and free.**

---

## The Problem

You type notes, emails, docs for hours. Your voice is 3x faster.

Cloud transcription costs $10–20/month and sends your data elsewhere. Built-in dictation is slow, unreliable, and doesn't work across all your devices.

## The Solution

VoiceToText runs on macOS, Linux, and Apple Silicon (MLX). Choose the platform that fits your setup — desktop, server, or MacBook. 99+ languages, auto-detected. No subscription, no API keys. Your data never leaves your device.

## Results

- **Before:** 5 min typing a 2-min voice note, or $20/mo for cloud ASR, or vendor lock-in
- **After:** 2 min voice → instant text. ~10–15x real-time. 100% offline. Free.

---

## Quick Start

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

---

## Deploy This For Your Business

This is open-source. You can run it yourself.

Or I can deploy, customize, and integrate it for your team — custom voice workflows, enterprise integrations, deployment on your infrastructure.

→ **Email:** iamfuyoh@gmail.com  
→ **Telegram:** [@ScanovichAI](https://t.me/ScanovichAI)

---

## Tech Stack

### Platforms

| Platform | Backend | Best For | Status |
|----------|---------|----------|--------|
| **macOS** | whisper.cpp + Core ML | macOS users, offline processing | ✅ Stable |
| **Linux** | FasterWhisper (CPU/GPU) | Linux servers, GPU acceleration | ✅ Stable |
| **MLX** | MLX Whisper | MacBook Air M1 8GB, Apple Silicon | ✅ Stable |

### Features

- 🎤 **High-quality transcription** using Whisper models
- 🔒 **100% offline** — no data leaves your device
- 🆓 **Completely free** — no subscriptions or API keys
- 🚀 **Fast performance** — optimized for each platform
- 🌍 **Multilingual support** — 99+ languages

### Requirements

**macOS:** macOS 12.0+, Python 3.12, Core ML  
**Linux:** Any distro, Python 3.12, CUDA (optional for GPU)  
**MLX:** Apple Silicon (M1/M2/M3), Python 3.12, MLX framework

### Performance

| Platform | Speed | Memory | GPU Support |
|----------|-------|--------|-------------|
| macOS | ~10x real-time | Low | Core ML |
| Linux | ~15x real-time | Medium | CUDA |
| MLX | ~12x real-time | Low | MLX |

### Use Cases

- 📝 **Transcription** — Convert audio to text
- 🎙️ **Voice notes** — Record and transcribe voice memos
- 📞 **Call transcription** — Transcribe phone calls
- 🎬 **Video subtitles** — Generate subtitles for videos
- 📚 **Accessibility** — Make audio content accessible

### Documentation

- 📊 [Platform Comparison](docs/PLATFORMS.md) — Compare features across platforms
- 🍎 [macOS Guide](platforms/macos/README.md) — macOS installation and usage
- 🐧 [Linux Guide](platforms/linux/README.md) — Linux installation and usage
- ⚡ [MLX Guide](platforms/mlx/README.md) — MLX installation and usage
- 🤝 [Contributing](CONTRIBUTING.md) — How to contribute
- 📝 [Changelog](CHANGELOG.md) — Version history

### License

MIT License — see [LICENSE](LICENSE) for details.

### Related Projects

- [Cleaner-OS](https://github.com/FUYOH666/Cleaner-OS) — System cleanup tool
- [telegram-ai](https://github.com/FUYOH666/telegram-ai) — AI platform for Telegram
- [Scanovich.ai-audio-call](https://github.com/FUYOH666/Scanovich.ai-audio-call) — Call analysis system

### Author

**Aleksandr Mordvinov**  
💬 Telegram: [@ScanovichAI](https://t.me/ScanovichAI)  
🌐 Website: [scanovich.ai](https://scanovich.ai)

---

## 🇷🇺 Русская версия

**Превращайте речь в текст мгновенно** — на Mac, Linux-сервере или Apple Silicon. Полностью офлайн, приватно и бесплатно.

### Проблема

Вы часами печатаете заметки, письма, документы. Голос в 3 раза быстрее.

Облачная транскрипция стоит $10–20/мес и отправляет ваши данные на сторону. Встроенный диктант медленный, ненадёжный и не работает на всех устройствах.

### Решение

VoiceToText работает на macOS, Linux и Apple Silicon (MLX). Выберите платформу под вашу задачу — десктоп, сервер или MacBook. 99+ языков, автоопределение. Без подписки и API-ключей. Данные не покидают ваше устройство.

### Результаты

- **Было:** 5 мин набора 2-минутной голосовой заметки, или $20/мес за облачный ASR
- **Стало:** 2 мин голоса → мгновенный текст. ~10–15x реального времени. 100% офлайн. Бесплатно.

### Быстрый старт

См. [Quick Start](#quick-start) выше. Документация: [docs/PLATFORMS.md](docs/PLATFORMS.md).

---

⭐️ *If you find this project useful, please consider giving it a star!*

*Если проект вам полезен, пожалуйста, поставьте звезду!*
