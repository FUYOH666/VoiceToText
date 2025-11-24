# Публикация на GitHub

## ✅ Текущий статус

Репозиторий готов к публикации:
- ✅ Git репозиторий инициализирован
- ✅ Все файлы закоммичены
- ✅ Версия: **v1.0.1**
- ✅ Ветка: **main**
- ✅ Тег: **v1.0.1**

## 🚀 Шаги для публикации

### 1. Создайте репозиторий на GitHub

1. Перейдите на https://github.com/new
2. Название репозитория: `VTT-MLX-M4` (или другое по вашему выбору)
3. Описание:
   ```
   Voice-to-Text для macOS с MLX Whisper, оптимизировано для MacBook Pro M4 Max. 
   Автоопределение языка, поддержка длинных записей (15-45 минут), работа 24/7.
   ```
4. **НЕ** инициализируйте с README, .gitignore или лицензией (у нас уже есть)
5. Нажмите "Create repository"

### 2. Подключите локальный репозиторий к GitHub

```bash
cd /Users/aleksandrmordvinov/development/VTT-MLX-m4

# Замените YOUR_USERNAME на ваш GitHub username
git remote add origin git@github.com:YOUR_USERNAME/VTT-MLX-M4.git

# Или через HTTPS:
# git remote add origin https://github.com/YOUR_USERNAME/VTT-MLX-M4.git
```

### 3. Отправьте код на GitHub

```bash
# Отправка основной ветки
git push -u origin main

# Отправка тегов
git push origin v1.0.1
```

### 4. Создайте релиз на GitHub

1. Перейдите в репозиторий на GitHub
2. Нажмите **Releases** → **Create a new release**
3. Выберите тег: **v1.0.1**
4. Заголовок: `VTT-MLX-M4 v1.0.1 - Optimized for M4 Max`
5. Описание (скопируйте из CHANGELOG.md):

```markdown
## [1.0.1] - 2025-11-24

### Fixed
- 🔧 **Fixed pynput GlobalHotKeys compatibility**: Updated hotkey handler to accept `injected` argument required by pynput 1.8.0+
- 🔧 **Improved error handling**: Added better exception handling for pynput compatibility issues
- 🔧 **Fallback mechanism**: Enhanced fallback to regular Listener when GlobalHotKeys fails

## [1.0.0] - 2025-11-23

### Added
- 🚀 **M4 Max optimization**: Optimized for MacBook Pro M4 Max with 128GB RAM
- 🌍 **Auto language detection**: Automatically detects language (Russian, Chinese, English, Japanese, etc.)
- 📦 **Long recordings support**: Optimized for 15-45 minute recordings with chunked processing
- ⚙️ **Batch processing**: Utilizes all 40 GPU cores on M4 Max (batch_size=6)
- 🔄 **24/7 operation**: Automatic memory management and error recovery
- 💾 **Memory Manager**: Automatic memory cleanup and monitoring
- 🧹 **Periodic cleanup**: Automatic memory cleanup every 10 transcriptions
- 📊 **Speed testing**: Added `test_transcription_speed.py` for performance testing
- 🎯 **Large-v3 model**: Default model changed to `whisper-large-v3-mlx` for maximum quality

### Performance
- **Speed**: ~42x real-time (tested on M4 Max)
  - 5-minute recording: ~6 seconds
  - 15-minute recording: ~20 seconds
  - 45-minute recording: ~1 minute
- **Memory**: Optimized memory usage with automatic cleanup
- **Stability**: Error recovery and automatic component reinitialization
```

6. Нажмите **Publish release**

### 5. Настройте репозиторий (опционально)

1. **Темы (Topics):**
   - `macos`
   - `apple-silicon`
   - `mlx`
   - `whisper`
   - `speech-to-text`
   - `voice-recognition`
   - `m4-max`
   - `python`

2. **Описание:**
   ```
   Voice-to-Text для macOS с MLX Whisper, оптимизировано для MacBook Pro M4 Max. 
   Автоопределение языка, поддержка длинных записей (15-45 минут), работа 24/7.
   Скорость: ~42x реального времени.
   ```

3. **Badges** (можно добавить в README.md):
   ```markdown
   ![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
   ![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon-green.svg)
   ![MLX](https://img.shields.io/badge/MLX-Whisper-orange.svg)
   ![Version](https://img.shields.io/badge/version-1.0.1-blue.svg)
   ```

## 📝 Быстрая команда для публикации

```bash
cd /Users/aleksandrmordvinov/development/VTT-MLX-m4

# После создания репозитория на GitHub:
git remote add origin git@github.com:YOUR_USERNAME/VTT-MLX-M4.git
git push -u origin main
git push origin v1.0.1
```

## ✅ Проверка после публикации

После публикации проверьте:
- ✅ Код доступен на GitHub
- ✅ README.md отображается корректно
- ✅ Тег v1.0.1 создан
- ✅ Релиз опубликован
- ✅ Все файлы на месте (особенно `.gitignore`)

## 🔄 Обновление репозитория в будущем

При внесении изменений:

```bash
# 1. Обновите CHANGELOG.md и версию в pyproject.toml
# 2. Закоммитьте изменения
git add .
git commit -m "Описание изменений"
git push origin main

# 3. Создайте новый тег (если новая версия)
git tag -a v1.0.2 -m "Release v1.0.2: Описание"
git push origin v1.0.2
```

