# Быстрый старт F9 ASR

## Установка и запуск (5 минут)

### 1. Проверка зависимостей

```bash
# Проверить, что установлены
which arecord xclip notify-send

# Если нет - установить
sudo apt install -y alsa-utils libnotify-bin xclip
```

### 2. Установка Python зависимостей

```bash
cd /path/to/F9-asr  # Перейдите в директорию проекта
uv sync
```

### 3. Проверка ASR сервиса

```bash
curl http://localhost:8001/healthz
```

Должен вернуть JSON с информацией о сервисе.

### 4. Установка как сервис (автозапуск)

```bash
./scripts/install-service.sh
```

Готово! Приложение работает в фоне.

## Использование

1. **Нажмите F9** - начнется запись (появится уведомление)
2. **Говорите** в микрофон
3. **Нажмите F9** снова - запись остановится и начнется транскрипция
4. **Результат** автоматически скопируется в буфер обмена
5. **Вставьте** текст куда нужно (Ctrl+V)

## Проверка работы

```bash
# Проверить статус сервиса
systemctl --user status f9-asr.service

# Посмотреть логи
journalctl --user -u f9-asr.service -f
```

## Что дальше?

- Настройка: отредактируйте `config.yaml`
- Управление сервисом: см. [SERVICE.md](SERVICE.md)
- Подробная документация: см. [README.md](README.md)
- Установка: см. [INSTALL.md](INSTALL.md)

## Troubleshooting

### Сервис не запускается

```bash
# Проверить логи
journalctl --user -u f9-asr.service --no-pager -n 50

# Проверить ASR сервис
curl http://localhost:8001/healthz
```

### F9 не работает

1. Убедитесь, что сервис запущен: `systemctl --user is-active f9-asr.service`
2. Проверьте логи: `journalctl --user -u f9-asr.service -f`
3. Возможно нужны права: `sudo usermod -a -G input $USER` (затем перелогиньтесь)
