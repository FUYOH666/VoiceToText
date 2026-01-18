# VTTv2 - Быстрый старт для MacBook Air M1 (8GB RAM)

## ✅ Что нужно установить

1. ✅ Клонировать репозиторий
2. ✅ Установить Python зависимости (MLX Whisper включен)
3. ✅ Настроить разрешения macOS

**Примечание:** MLX Whisper автоматически скачает модель при первом использовании. Whisper.cpp опционален (только для fallback).

## 🚀 Быстрая установка

```bash
# 1. Клонирование репозитория
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText/platforms/macos

**Примечание:** Проект находится в поддиректории `platforms/macos` основного репозитория [VoiceToText](https://github.com/FUYOH666/VoiceToText).

# 2. Создание виртуального окружения и установка зависимостей
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip==25.3
pip install -r requirements.txt
```

Готово! MLX Whisper настроен по умолчанию и автоматически скачает модель `mlx-community/whisper-medium` при первом использовании (оптимально для M1 с 8GB RAM).

## 🚀 Запуск

### Проверка системы (Health Check)

```bash
source venv/bin/activate
python src/main.py --health
```

**Ожидаемый результат:**
```
=== Результаты Health Check ===
config: ✅
permissions_mic: ❌ (или ✅ после настройки)
permissions_accessibility: ✅
mlx_whisper: ✅
```

Если видите предупреждения о разрешениях - это нормально для первого запуска.

### Запуск приложения

```bash
source venv/bin/activate
python src/main.py
```

Приложение появится в виде иконки 🎤 в строке меню macOS.

## ⚙️ Настройка разрешений macOS

**ВАЖНО:** Перед запуском нужно настроить разрешения:

1. **Микрофон:**
   - Системные настройки > Конфиденциальность > Микрофон
   - Добавьте Terminal (или приложение, которое запускает VTTv2)

2. **Accessibility (Управление компьютером):**
   - Системные настройки > Конфиденциальность > Управление компьютером
   - Добавьте Terminal (или приложение, которое запускает VTTv2)

## 📝 Использование

1. Откройте любое текстовое приложение (TextEdit, Notes, и т.д.)
2. Установите курсор в нужное место
3. Запустите VTTv2 (`python src/main.py`)
4. Нажмите **Option+Space** для начала записи (иконка изменится на 🔴)
5. Говорите в микрофон
6. Нажмите **Option+Space** еще раз для остановки и транскрипции
7. Текст автоматически вставится в место курсора через несколько секунд

## 🎯 Иконки в menu bar

- 🎤 - Готов к записи
- 🔴 - Идет запись
- Иконка показывает статус в реальном времени

## 🔧 Конфигурация (опционально)

Основные параметры в `config.yaml`:

- `transcription.engine` - движок: `"mlx_whisper"` (рекомендуется) или `"whisper_cpp"`
- `transcription.mlx_whisper.model_name` - модель MLX: `"mlx-community/whisper-medium"` (оптимально для M1 8GB)
- `ui.hotkey` - горячие клавиши (по умолчанию: `"option+space"`)
- `ui.auto_paste_enabled` - автовставка текста (по умолчанию: `true`)

## ⚠️ Важно

- **MLX Whisper** - основной движок, оптимизирован для Apple Silicon (M1/M2/M3/M4)
- Модель **Medium** обеспечивает оптимальный баланс качества и скорости для M1 с 8GB RAM
- Модель скачивается автоматически при первом использовании (требуется интернет только один раз)
- После установки приложение работает полностью офлайн
- Все проверки выполняются при старте (fail fast подход)

## 🔄 Whisper.cpp (опционально, для fallback)

Если вы хотите использовать whisper.cpp как альтернативный движок:

```bash
# Клонирование и компиляция whisper.cpp
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
mkdir build && cd build
cmake .. -DBUILD_SHARED_LIBS=ON -DWHISPER_COREML=ON
make -j4
cd ../..

# Скачивание модели Medium Q5_0 (опционально)
mkdir -p models
cd models
curl -L "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q5_0.bin" -o ggml-medium-q5_0.bin
cd ..

# Переключение на whisper.cpp в config.yaml
# Измените: transcription.engine: whisper_cpp
```

## 📚 Полная документация

См. [README.md](README.md) для полной документации, решения проблем и дополнительных настроек.
