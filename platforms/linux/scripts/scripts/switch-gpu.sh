#!/bin/bash

# VoiceToText-Linux-F9: Switch GPU/CPU Script
# Переключение между GPU и CPU для транскрибации

CONFIG_FILE="/home/ai/Документы/dev/VTT-Linux/config.yaml"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_gpu() {
    echo -e "${PURPLE}[GPU]${NC} $1"
}

# Проверка существования конфиг файла
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Конфигурационный файл не найден: $CONFIG_FILE"
    exit 1
fi

# Проверка аргументов
if [ $# -eq 0 ]; then
    echo "VoiceToText-Linux-F9: GPU/CPU Switch Tool"
    echo ""
    echo "Использование:"
    echo "  $0 on      - Включить GPU режим"
    echo "  $0 off     - Включить CPU режим"
    echo "  $0 toggle  - Переключить режим"
    echo "  $0 status  - Показать текущий режим"
    echo ""
    echo "GPU режим значительно ускоряет транскрибацию!"
    echo ""
    exit 0
fi

# Проверка GPU доступности
check_gpu_availability() {
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            return 0  # GPU доступен
        fi
    fi
    return 1  # GPU недоступен
}

# Показать статус
if [ "$1" = "status" ]; then
    current_gpu=$(grep "^use_gpu:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')

    echo "VoiceToText-Linux-F9: GPU Status"
    echo "================================"

    if [ "$current_gpu" = "true" ]; then
        print_gpu "GPU режим: ВКЛЮЧЕН"
        print_info "Транскрибация будет использовать GPU автоматически"
        print_info "Ожидаемая скорость: 2-5x быстрее CPU"
    else
        print_warning "GPU режим: ОТКЛЮЧЕН"
        print_info "Транскрибация будет использовать CPU"
        print_info "Рекомендуется включить GPU для максимальной скорости"
    fi

    echo ""
    if check_gpu_availability; then
        print_success "✅ NVIDIA GPU найден в системе"
        gpu_info=$(nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits | head -1)
        print_info "GPU: $gpu_info"
    else
        print_warning "⚠️  NVIDIA GPU не найден или драйверы не установлены"
        print_info "Убедитесь, что установлены NVIDIA драйверы и CUDA"
    fi

    echo ""
    print_info "Для изменения режима используйте:"
    echo "  $0 on    - Включить GPU"
    echo "  $0 off   - Включить CPU"
    echo "  $0 toggle - Переключить"
    exit 0
fi

# Переключение режима
case "$1" in
    "on")
        NEW_GPU="true"
        MODE_TEXT="GPU режим"
        ;;
    "off")
        NEW_GPU="false"
        MODE_TEXT="CPU режим"
        ;;
    "toggle")
        CURRENT_GPU=$(grep "^use_gpu:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
        if [ "$CURRENT_GPU" = "true" ]; then
            NEW_GPU="false"
            MODE_TEXT="CPU режим"
        else
            NEW_GPU="true"
            MODE_TEXT="GPU режим"
        fi
        ;;
    *)
        print_error "Неверный аргумент: $1"
        echo "Используйте: $0 on, off, toggle, или status"
        exit 1
        ;;
esac

# Проверка GPU доступности при включении GPU режима
if [ "$NEW_GPU" = "true" ]; then
    if ! check_gpu_availability; then
        print_error "GPU недоступен в системе!"
        print_info "Убедитесь, что:"
        print_info "  1. Установлены NVIDIA драйверы"
        print_info "  2. Установлена CUDA"
        print_info "  3. GPU поддерживает CUDA"
        exit 1
    fi
fi

# Чтение текущего режима
CURRENT_GPU=$(grep "^use_gpu:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')

# Проверка, нужно ли менять
if [ "$CURRENT_GPU" = "$NEW_GPU" ]; then
    if [ "$NEW_GPU" = "true" ]; then
        print_warning "GPU режим уже включен"
    else
        print_warning "CPU режим уже включен"
    fi
    exit 0
fi

# Переключение режима в конфиге
sed -i "s/^use_gpu: .*/use_gpu: $NEW_GPU/" "$CONFIG_FILE"

if [ $? -eq 0 ]; then
    print_success "Режим переключен на: $MODE_TEXT"

    if [ "$NEW_GPU" = "true" ]; then
        print_gpu "🚀 GPU режим активирован!"
        print_info "GPU будет использоваться автоматически при наличии оборудования"
        print_info "Ожидаемая производительность: 2-5x быстрее"
        print_info "Особенно эффективно для моделей large-v3 и medium"
    else
        print_warning "🐌 CPU режим активирован"
        print_info "Транскрибация будет медленнее, но совместима со всеми системами"
    fi

    echo ""
    print_warning "🔄 Перезапустите приложение для применения изменений!"
    print_info "Команда перезапуска:"
    print_info "  /home/ai/Документы/dev/VTT-Linux/scripts/restart.sh"
    echo ""
    print_info "Или запустите вручную:"
    echo "  cd /home/ai/Projects/whisper.cpp && ./whisper-toggle.sh"
else
    print_error "Ошибка при изменении конфигурации"
    exit 1
fi
