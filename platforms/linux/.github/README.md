# F9 ASR - Voice Transcription on F9 Keypress

Система транскрипции голоса по нажатию клавиши F9 с использованием ASR сервиса.

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd F9-asr

# 2. Установить зависимости
sudo apt install -y alsa-utils libnotify-bin xclip
uv sync

# 3. Настроить config.yaml (при необходимости)
# 4. Установить как сервис
./scripts/install-service.sh

# Готово! Нажмите F9 для начала записи
```

## 📚 Документация

- [README.md](README.md) - Полная документация
- [QUICKSTART.md](QUICKSTART.md) - Быстрый старт
- [INSTALL.md](INSTALL.md) - Подробная установка
- [SERVICE.md](SERVICE.md) - Управление сервисом
- [PRIVACY.md](PRIVACY.md) - Конфиденциальность
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Решение проблем

## ✨ Особенности

- 🎤 Запись голоса по F9
- 🚀 Интеграция с ASR сервисом (Whisper Large v3 Turbo)
- 📋 Автокопирование в буфер обмена
- 🔔 Уведомления о статусе
- 🧹 Автоматическая очистка файлов
- 🔒 Конфиденциальность - данные не сохраняются
- 🔄 Стабильная работа через systemd

## 📋 Требования

- Linux (Ubuntu 24.04+)
- Python 3.12+
- ASR сервис на порту 8001
- `alsa-utils`, `libnotify-bin`, `xclip`

## 📝 Лицензия

MIT
