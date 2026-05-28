#!/bin/bash

# VoiceToText-Linux-F9: Switch Model Script
# Переключение модели распознавания речи

CONFIG_FILE="/home/ai/Документы/dev/VTT-Linux/config.yaml"
WHISPER_MODELS_DIR="/home/ai/Projects/whisper.cpp/models"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода цветного текста
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка существования конфиг файла
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Конфигурационный файл не найден: $CONFIG_FILE"
    exit 1
fi

# Проверка аргументов
if [ $# -eq 0 ]; then
    echo "VoiceToText-Linux-F9: Switch Model Tool"
    echo ""
    echo "Использование:"
    echo "  $0 <model_name>    - Переключиться на указанную модель"
    echo "  $0 --list          - Показать доступные модели"
    echo "  $0 --current       - Показать текущую модель"
    echo ""
    echo "Доступные модели:"
    echo "  tiny              - Быстрая, низкая точность (39MB)"
    echo "  base              - Хороший баланс (74MB)"
    echo "  small             - Лучшая точность (244MB)"
    echo "  medium            - Высокая точность (769MB)"
    echo "  large-v3          - Максимальная точность (2.9GB, GPU)"
    echo "  large-v3-turbo-f16- Оптимальная large-модель для CPU (12 потоков)"
    echo ""
    exit 0
fi

# Показать доступные модели
if [ "$1" = "--list" ]; then
    print_info "Доступные модели в системе:"
    echo ""

    for model in tiny base small medium large-v3 large-v3-turbo-f16; do
        model_file="$WHISPER_MODELS_DIR/ggml-${model}.bin"
        if [ -f "$model_file" ]; then
            size=$(ls -lh "$model_file" | awk '{print $5}')
            echo -e "  ${GREEN}✓${NC} $model - $size"
        else
            echo -e "  ${RED}✗${NC} $model - не найден"
        fi
    done
    echo ""
    exit 0
fi

# Показать текущую модель
if [ "$1" = "--current" ]; then
    current_model=$(grep "^model:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
    print_info "Текущая модель: $current_model"
    case $current_model in
        "tiny")
            print_info "Особенности: Быстрая обработка, низкая точность"
            ;;
        "base")
            print_info "Особенности: Хороший баланс скорости и точности"
            ;;
        "small")
            print_info "Особенности: Повышенная точность"
            ;;
        "medium")
            print_info "Особенности: Высокая точность для общего использования"
            ;;
        "large-v3")
            print_info "Особенности: Максимальная точность, требует GPU"
            ;;
        "large-v3-turbo-f16")
            print_info "Особенности: Large-модель, оптимизированная для CPU (12 потоков)"
            ;;
    esac
    exit 0
fi

# Переключение на новую модель
NEW_MODEL="$1"

# Проверка доступности модели
MODEL_FILE="$WHISPER_MODELS_DIR/ggml-${NEW_MODEL}.bin"
if [ ! -f "$MODEL_FILE" ]; then
    print_error "Модель '$NEW_MODEL' не найдена в $WHISPER_MODELS_DIR"
    print_info "Используйте '$0 --list' для просмотра доступных моделей"
    exit 1
fi

# Проверка текущей модели
CURRENT_MODEL=$(grep "^model:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')

if [ "$CURRENT_MODEL" = "$NEW_MODEL" ]; then
    print_warning "Модель '$NEW_MODEL' уже активна"
    exit 0
fi

# Переключение модели в конфиге
sed -i "s/^model: .*/model: \"$NEW_MODEL\"/" "$CONFIG_FILE"

if [ $? -eq 0 ]; then
    print_success "Модель переключена: $CURRENT_MODEL → $NEW_MODEL"

    # Показать информацию о новой модели
    MODEL_SIZE=$(ls -lh "$MODEL_FILE" | awk '{print $5}')
    print_info "Размер модели: $MODEL_SIZE"

    case $NEW_MODEL in
        "tiny")
            print_info "Особенности: Быстрая обработка, низкая точность"
            ;;
        "base")
            print_info "Особенности: Хороший баланс скорости и точности"
            ;;
        "small")
            print_info "Особенности: Повышенная точность"
            ;;
        "medium")
            print_info "Особенности: Высокая точность для общего использования"
            ;;
        "large-v3")
            print_info "Особенности: Максимальная точность, требуется GPU"
            ;;
        "large-v3-turbo-f16")
            print_info "Особенности: Large-модель, оптимизированная для CPU (12 потоков)"
            ;;
    esac

    print_warning "Перезапустите приложение для применения изменений!"
    print_info "Команда перезапуска: $0 --restart"
else
    print_error "Ошибка при изменении конфигурации"
    exit 1
fi
