# Migration Guide: Moving Code to VoiceToText Monorepo

[🇷🇺 Русская версия](#русская-версия)

This guide explains how to migrate code from the old separate repositories into the unified VoiceToText monorepo.

## Overview

The three separate VoiceToText repositories have been unified into a single monorepo:
- `VoiceToText-MACos` → `platforms/macos/`
- `VoiceToText-Linux` → `platforms/linux/`
- `VoiceToText-MLX-M1-8Gb` → `platforms/mlx/`

## Migration Steps

### Step 1: Clone Old Repositories

```bash
# Create temporary directory
mkdir -p /tmp/voicetotext-migration
cd /tmp/voicetotext-migration

# Clone old repositories
git clone https://github.com/FUYOH666/VoiceToText-MACos.git
git clone https://github.com/FUYOH666/VoiceToText-Linux.git
git clone https://github.com/FUYOH666/VoiceToText-MLX-M1-8Gb.git
```

### Step 2: Clone New Monorepo

```bash
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText
```

### Step 3: Copy Code from Old Repositories

#### macOS Platform

```bash
# Copy source code
cp -r ../VoiceToText-MACos/src platforms/macos/
cp -r ../VoiceToText-MACos/models platforms/macos/ 2>/dev/null || true

# Copy configuration files
cp ../VoiceToText-MACos/config.yaml platforms/macos/ 2>/dev/null || true
cp ../VoiceToText-MACos/requirements.txt platforms/macos/ 2>/dev/null || true

# Copy other important files
cp ../VoiceToText-MACos/QUICKSTART.md platforms/macos/ 2>/dev/null || true
```

#### Linux Platform

```bash
# Copy source code
cp -r ../VoiceToText-Linux/scripts platforms/linux/ 2>/dev/null || true
cp -r ../VoiceToText-Linux/src platforms/linux/ 2>/dev/null || true

# Copy configuration files
cp ../VoiceToText-Linux/config.yaml platforms/linux/ 2>/dev/null || true
cp ../VoiceToText-Linux/install.sh platforms/linux/ 2>/dev/null || true

# Copy documentation
cp -r ../VoiceToText-Linux/docs platforms/linux/ 2>/dev/null || true
```

#### MLX Platform

```bash
# Copy source code
cp -r ../VoiceToText-MLX-M1-8Gb/src platforms/mlx/
cp -r ../VoiceToText-MLX-M1-8Gb/models platforms/mlx/ 2>/dev/null || true
cp -r ../VoiceToText-MLX-M1-8Gb/tests platforms/mlx/ 2>/dev/null || true

# Copy configuration files
cp ../VoiceToText-MLX-M1-8Gb/config.yaml platforms/mlx/ 2>/dev/null || true
cp ../VoiceToText-MLX-M1-8Gb/config.m1-8gb.yaml.example platforms/mlx/ 2>/dev/null || true
cp ../VoiceToText-MLX-M1-8Gb/config.m4-128gb.yaml.example platforms/mlx/ 2>/dev/null || true
cp ../VoiceToText-MLX-M1-8Gb/requirements.txt platforms/mlx/ 2>/dev/null || true

# Copy other files
cp ../VoiceToText-MLX-M1-8Gb/QUICKSTART.md platforms/mlx/ 2>/dev/null || true
```

### Step 4: Update Import Paths (if needed)

If the code uses absolute imports, you may need to update them:

```python
# Old (if existed)
from src.module import something

# New (if needed)
from platforms.macos.src.module import something
# or use relative imports
```

### Step 5: Test Each Platform

```bash
# Test macOS
cd platforms/macos
python src/main.py --help

# Test Linux
cd ../linux
./install.sh --help  # or python src/main.py --help

# Test MLX
cd ../mlx
python src/main.py --help
```

### Step 6: Commit and Push

```bash
cd /path/to/VoiceToText

# Add all files
git add .

# Commit
git commit -m "Migrate code from separate repositories to monorepo structure"

# Push
git push origin main
```

## File Structure After Migration

```
VoiceToText/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── CHANGELOG.md
├── pyproject.toml
├── platforms/
│   ├── macos/
│   │   ├── src/
│   │   ├── models/
│   │   ├── config.yaml
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── linux/
│   │   ├── src/ (or scripts/)
│   │   ├── docs/
│   │   ├── config.yaml
│   │   ├── install.sh
│   │   └── README.md
│   └── mlx/
│       ├── src/
│       ├── models/
│       ├── tests/
│       ├── config.yaml
│       ├── requirements.txt
│       └── README.md
└── docs/
    └── PLATFORMS.md
```

## Notes

- Keep platform-specific README files updated
- Maintain platform-specific requirements.txt files
- Update import paths if necessary
- Test each platform after migration
- Update documentation links

## Troubleshooting

### Import Errors

If you encounter import errors, check:
1. Python path is set correctly
2. Relative imports are used where possible
3. Platform-specific dependencies are installed

### Missing Files

Some files may not exist in all repositories. Use `2>/dev/null || true` to handle missing files gracefully.

### Configuration Differences

Each platform may have different configuration formats. Keep them separate in `platforms/{platform}/config.yaml`.

---

## 🇷🇺 Русская версия

Это руководство объясняет, как мигрировать код из старых отдельных репозиториев в единый монорепозиторий VoiceToText.

## Обзор

Три отдельных репозитория VoiceToText объединены в единый монорепозиторий:
- `VoiceToText-MACos` → `platforms/macos/`
- `VoiceToText-Linux` → `platforms/linux/`
- `VoiceToText-MLX-M1-8Gb` → `platforms/mlx/`

## Шаги миграции

### Шаг 1: Клонировать старые репозитории

```bash
# Создать временную директорию
mkdir -p /tmp/voicetotext-migration
cd /tmp/voicetotext-migration

# Клонировать старые репозитории
git clone https://github.com/FUYOH666/VoiceToText-MACos.git
git clone https://github.com/FUYOH666/VoiceToText-Linux.git
git clone https://github.com/FUYOH666/VoiceToText-MLX-M1-8Gb.git
```

### Шаг 2: Клонировать новый монорепозиторий

```bash
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText
```

### Шаг 3: Скопировать код из старых репозиториев

См. команды выше в английской версии.

### Шаг 4: Обновить пути импорта (если нужно)

Если код использует абсолютные импорты, может потребоваться их обновление.

### Шаг 5: Протестировать каждую платформу

```bash
# Тест macOS
cd platforms/macos
python src/main.py --help

# Тест Linux
cd ../linux
./install.sh --help

# Тест MLX
cd ../mlx
python src/main.py --help
```

### Шаг 6: Закоммитить и запушить

```bash
cd /path/to/VoiceToText
git add .
git commit -m "Migrate code from separate repositories to monorepo structure"
git push origin main
```

## Структура файлов после миграции

См. структуру выше в английской версии.

## Примечания

- Обновляйте README файлы для каждой платформы
- Поддерживайте platform-specific requirements.txt файлы
- Обновляйте пути импорта при необходимости
- Тестируйте каждую платформу после миграции
- Обновляйте ссылки в документации

## Устранение неполадок

### Ошибки импорта

Если возникают ошибки импорта, проверьте:
1. Python path установлен правильно
2. Используются относительные импорты где возможно
3. Установлены platform-specific зависимости

### Отсутствующие файлы

Некоторые файлы могут отсутствовать во всех репозиториях. Используйте `2>/dev/null || true` для обработки отсутствующих файлов.

### Различия в конфигурации

Каждая платформа может иметь разные форматы конфигурации. Держите их отдельно в `platforms/{platform}/config.yaml`.

