# Управление F9 ASR Service

## Статус установки

Сервис установлен как systemd user service и работает в фоновом режиме.

## Основные команды

### Проверка статуса

```bash
systemctl --user status f9-asr.service
```

### Просмотр логов

```bash
# Последние 50 строк
journalctl --user -u f9-asr.service -n 50

# В реальном времени (следить за логами)
journalctl --user -u f9-asr.service -f

# Логи за сегодня
journalctl --user -u f9-asr.service --since today

# Логи с определенного времени
journalctl --user -u f9-asr.service --since "2026-02-09 14:00:00"
```

### Управление сервисом

```bash
# Запустить
systemctl --user start f9-asr.service

# Остановить
systemctl --user stop f9-asr.service

# Перезапустить
systemctl --user restart f9-asr.service

# Включить автозапуск (уже включен после установки)
systemctl --user enable f9-asr.service

# Отключить автозапуск
systemctl --user disable f9-asr.service

# Перезагрузить конфигурацию (после изменения service файла)
systemctl --user daemon-reload
systemctl --user restart f9-asr.service
```

## Автозапуск

Сервис автоматически запускается при входе в систему благодаря `WantedBy=default.target`.

Для проверки:

```bash
# Проверить, включен ли автозапуск
systemctl --user is-enabled f9-asr.service

# Должно вывести: enabled
```

## Автоматический перезапуск

Сервис настроен на автоматический перезапуск при сбоях:
- `Restart=always` - перезапуск всегда
- `RestartSec=5` - задержка 5 секунд перед перезапуском

## Расположение файлов

- **Service файл**: `~/.config/systemd/user/f9-asr.service`
- **Логи**: `journalctl --user -u f9-asr.service`
- **Рабочая директория**: определяется автоматически при установке (директория проекта)

## Troubleshooting

### Сервис не запускается

1. Проверьте логи:
   ```bash
   journalctl --user -u f9-asr.service --no-pager -n 50
   ```

2. Проверьте, что ASR сервис доступен:
   ```bash
   curl http://localhost:8001/healthz
   ```

3. Проверьте права доступа:
   ```bash
   ls -la ~/.config/systemd/user/f9-asr.service
   ```

### Сервис падает при запуске

1. Проверьте, что `uv` доступен:
   ```bash
   which uv
   ```

2. Проверьте рабочую директорию (замените на путь к вашему проекту):
   ```bash
   # Проверьте путь в service файле
   systemctl --user show f9-asr.service | grep WorkingDirectory
   ls <путь_к_проекту>/config.yaml
   ```

3. Проверьте переменные окружения:
   ```bash
   systemctl --user show f9-asr.service | grep Environment
   ```

### Горячая клавиша F9 не работает

1. Убедитесь, что сервис запущен:
   ```bash
   systemctl --user is-active f9-asr.service
   ```

2. Проверьте логи на ошибки:
   ```bash
   journalctl --user -u f9-asr.service -f
   ```

3. Возможно, нужны права доступа к клавиатуре:
   ```bash
   # Добавить пользователя в группу input
   sudo usermod -a -G input $USER
   # Перелогиньтесь
   ```

### Сервис не запускается после перезагрузки

1. Проверьте, что включен автозапуск:
   ```bash
   systemctl --user is-enabled f9-asr.service
   ```

2. Проверьте логи systemd:
   ```bash
   journalctl --user -u f9-asr.service --since "1 hour ago"
   ```

3. Убедитесь, что `graphical-session.target` доступен:
   ```bash
   systemctl --user list-dependencies default.target
   ```

## Редактирование service файла

Если нужно изменить настройки сервиса:

1. Отредактируйте файл:
   ```bash
   nano ~/.config/systemd/user/f9-asr.service
   ```

2. Перезагрузите конфигурацию:
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart f9-asr.service
   ```

## Удаление сервиса

Если нужно удалить сервис:

```bash
# Остановить и отключить
systemctl --user stop f9-asr.service
systemctl --user disable f9-asr.service

# Удалить файл
rm ~/.config/systemd/user/f9-asr.service

# Перезагрузить systemd
systemctl --user daemon-reload
```
