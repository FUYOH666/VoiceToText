# F9 ASR - Voice Transcription on F9 Keypress

Система транскрипции голоса по нажатию клавиши F9 с использованием ASR сервиса на порту 8001.

## Особенности

- 🎤 **Запись голоса** по нажатию F9
- 🚀 **Использование ASR сервиса** (Qwen3-ASR-0.6B на порту 8001)
- 📋 **Автоматическое копирование** результата в буфер обмена
- 🔔 **Уведомления** о статусе транскрипции
- ⚙️ **Гибкая конфигурация** через YAML
- 🧹 **Автоматическая очистка** временных файлов (не накапливаются)
- 🔒 **Конфиденциальность** - данные не сохраняются, только временная обработка
- 🔄 **Стабильная работа** - автоперезапуск при сбоях через systemd

## Требования

- Linux (Ubuntu 24.04+)
- Python 3.12+
- ASR сервис на порту 8001 (Qwen3-ASR-0.6B)
- Системные зависимости:
  - `alsa-utils` (для `arecord`)
  - `libnotify-bin` (для уведомлений)
  - `xclip` или `xsel` (для буфера обмена)

## Установка

### Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText/platforms/linux

# 2. Установить системные зависимости
sudo apt update
sudo apt install -y alsa-utils libnotify-bin xclip

# 3. Установить Python зависимости
uv sync

# 4. Установить как сервис (рекомендуется)
./scripts/install-service.sh
```

### Подробная установка

#### 1. Установка системных зависимостей

```bash
sudo apt update
sudo apt install -y alsa-utils libnotify-bin xclip
```

#### 2. Установка Python зависимостей

```bash
cd platforms/linux  # Перейдите в директорию проекта
uv sync
```

#### 3. Настройка конфигурации

Отредактируйте `config.yaml` при необходимости:

```yaml
asr:
  base_url: "http://localhost:8001"
  language: null  # null для автоопределения, или "Russian", "English"
  
hotkey:
  key: "f9"  # Клавиша для записи
```

#### 4. Установка как systemd service (рекомендуется)

Для постоянной работы и автозапуска:

```bash
./scripts/install-service.sh
```

Сервис будет:
- ✅ Автоматически запускаться при входе в систему
- ✅ Автоматически перезапускаться при сбоях
- ✅ Работать постоянно в фоновом режиме

**Управление сервисом:**
```bash
# Статус
systemctl --user status f9-asr.service

# Логи
journalctl --user -u f9-asr.service -f

# Перезапуск
systemctl --user restart f9-asr.service
```

Подробнее см. [SERVICE.md](SERVICE.md)

#### 5. Запуск вручную (альтернатива)

Если не используете systemd service:

```bash
uv run python -m f9_asr.main
```

## Использование

После установки systemd service приложение работает автоматически в фоне:

1. Нажмите **F9** для начала записи (появится уведомление)
2. Говорите четко в микрофон
3. Нажмите **F9** снова для остановки и транскрипции
4. Результат автоматически скопируется в буфер обмена
5. Вставьте текст куда нужно (Ctrl+V)

**Примечание:** Если сервис не установлен, запустите вручную: `uv run python -m f9_asr.main`

## Конфигурация

Основные параметры в `config.yaml`:

- **asr.base_url**: URL ASR сервиса (по умолчанию: http://localhost:8001)
- **asr.language**: Язык транскрипции (null для автоопределения)
- **asr.response_format**: Формат ответа (json, text, srt, verbose_json, vtt)
- **audio.sample_rate**: Частота дискретизации (16000 Hz)
- **audio.cleanup_max_age_hours**: Автоочистка файлов старше N часов (24 по умолчанию)
- **hotkey.key**: Горячая клавиша (f9)
- **ui.copy_to_clipboard**: Копировать в буфер обмена
- **ui.show_notifications**: Показывать уведомления
- **logging.level**: Уровень логирования (INFO, DEBUG, WARNING, ERROR)

## Архитектура

```
f9_asr/
├── config.py          # Конфигурация (Pydantic Settings)
├── audio_recorder.py  # Запись аудио (arecord)
├── asr_client.py      # Клиент ASR API
├── hotkey_handler.py  # Обработчик горячей клавиши F9
└── main.py            # Точка входа
```

## Сравнение с VoiceToText

### Преимущества нашего решения:

1. ✅ **Использует существующий ASR сервис** вместо локального whisper.cpp
2. ✅ **Современный стек**: Python 3.12, Pydantic, uv
3. ✅ **Гибкая конфигурация**: YAML + Pydantic Settings
4. ✅ **Лучшая обработка ошибок**: структурированное логирование
5. ✅ **Проще в поддержке**: чистый Python код вместо bash-скриптов

### VoiceToText использует:

- whisper.cpp (локальная модель)
- Bash-скрипты
- Требует компиляцию C++ кода

## Документация

- [QUICKSTART.md](QUICKSTART.md) - Быстрый старт
- [INSTALL.md](INSTALL.md) - Подробная инструкция по установке
- [SERVICE.md](SERVICE.md) - Управление systemd service
- [PRIVACY.md](PRIVACY.md) - Конфиденциальность и очистка данных
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Решение проблем

## Troubleshooting

См. подробное руководство в [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Быстрая проверка

```bash
# Статус сервиса
systemctl --user status f9-asr.service

# Логи
journalctl --user -u f9-asr.service -f

# Проверка ASR сервиса
curl http://localhost:8001/healthz
```

## Разработка

### Установка dev-зависимостей

```bash
uv sync --dev
```

### Запуск тестов

```bash
uv run pytest
```

## Лицензия

MIT
