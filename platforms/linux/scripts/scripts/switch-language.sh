#!/bin/bash

# VoiceToText-Linux-F9: Switch Language Script
# Переключение языка распознавания речи

CONFIG_FILE="/home/ai/Документы/dev/VTT-Linux/config.yaml"

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
    echo "VoiceToText-Linux-F9: Switch Language Tool"
    echo ""
    echo "Использование:"
    echo "  $0 <language>     - Переключиться на указанный язык"
    echo "  $0 --list         - Показать доступные языки"
    echo "  $0 --current      - Показать текущий язык"
    echo ""
    echo "Доступные языки:"
    echo "  ru    - Русский язык (принудительно)"
    echo "  en    - Английский язык (принудительно)"
    echo "  auto  - Автоопределение языка"
    echo ""
    exit 0
fi

# Показать доступные языки
if [ "$1" = "--list" ]; then
    print_info "Доступные языки:"
    echo ""
    echo -e "  ${GREEN}ru${NC}    - Русский язык (рекомендуется для максимальной точности)"
    echo -e "  ${GREEN}en${NC}    - Английский язык (как было изначально)"
    echo -e "  ${GREEN}auto${NC}  - Автоопределение языка по содержимому"
    echo ""
    exit 0
fi

# Показать текущий язык
if [ "$1" = "--current" ]; then
    current_lang=$(grep "^language:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
    print_info "Текущий язык: $current_lang"
    exit 0
fi

# Переключение на новый язык
NEW_LANG="$1"

# Проверка допустимости языка
case $NEW_LANG in
    "ru"|"en"|"auto")
        ;;
    *)
        print_error "Недопустимый язык: $NEW_LANG"
        print_info "Используйте '$0 --list' для просмотра доступных языков"
        exit 1
        ;;
esac

# Проверка текущего языка
CURRENT_LANG=$(grep "^language:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')

if [ "$CURRENT_LANG" = "$NEW_LANG" ]; then
    print_warning "Язык '$NEW_LANG' уже активен"
    exit 0
fi

# Переключение языка в конфиге
sed -i "s/^language: .*/language: \"$NEW_LANG\"/" "$CONFIG_FILE"

if [ $? -eq 0 ]; then
    print_success "Язык переключен: $CURRENT_LANG → $NEW_LANG"

    case $NEW_LANG in
        "ru")
            print_info "Режим: Принудительное распознавание русского языка"
            print_info "Рекомендуется использовать модель large-v3 для максимальной точности"
            ;;
        "en")
            print_info "Режим: Принудительное распознавание английского языка"
            print_info "Любая модель будет работать хорошо"
            ;;
        "auto")
            print_info "Режим: Автоопределение языка по содержимому"
            print_info "Модель сама выберет подходящий язык"
            ;;
    esac

    print_warning "Перезапустите приложение для применения изменений!"
    print_info "Команда перезапуска: /home/ai/Документы/dev/VTT-Linux/scripts/restart.sh"
else
    print_error "Ошибка при изменении конфигурации"
    exit 1
fi
