# Troubleshooting F9 ASR

## Проблема: Пустой результат транскрипции

### Симптомы
- F9 работает, запись начинается и останавливается
- Но в буфере обмена нет текста
- В логах: "Empty transcription result"

### Причины и решения

#### 1. Тихий звук или отсутствие звука

**Проверка:**
```bash
# Проверить уровень микрофона
alsamixer
# Нажмите F4 для выбора Capture, увеличьте уровень
```

**Решение:**
- Говорите громче и ближе к микрофону
- Проверьте настройки микрофона в системе
- Убедитесь, что микрофон не отключен

#### 2. Неправильный формат аудио

**Проверка:**
```bash
# Проверить формат записанного файла
file /tmp/f9-asr-recordings/*.wav
```

**Решение:**
- Формат должен быть: WAVE audio, 16 bit, mono, 16000 Hz
- Если формат неправильный, проверьте настройки в `config.yaml`

#### 3. ASR сервис не обрабатывает файл

**Проверка:**
```bash
# Проверить логи ASR сервиса
# (команда зависит от вашей конфигурации ASR сервиса)

# Проверить доступность
curl http://localhost:8001/healthz
```

**Решение:**
- Убедитесь, что ASR сервис запущен
- Проверьте логи ASR сервиса на ошибки
- Попробуйте перезапустить ASR сервис

#### 4. Проблемы с правами доступа

**Проверка:**
```bash
# Проверить логи F9 ASR
journalctl --user -u f9-asr.service -f
```

**Решение:**
- Убедитесь, что сервис имеет доступ к микрофону
- Проверьте права на `/tmp/f9-asr-recordings/`

#### 5. Bluetooth-гарнитура / микрофон не виден

**Симптомы:** При подключенной Bluetooth-гарнитуре запись идёт, но результат пустой. Или система не видит микрофон гарнитуры.

**Причина:** Bluetooth подключается в режиме A2DP (только воспроизведение), без микрофона.

**Решение:** Настроить WirePlumber на режим Headset (HFP). См. подробную инструкцию: [docs/BLUETOOTH_MIC.md](docs/BLUETOOTH_MIC.md)

Кратко:
1. Создать `~/.config/wireplumber/bluetooth.lua.d/51-headset-profile.lua` с `device.profile = "headset-head-unit"`
2. Перезапустить WirePlumber, переподключить гарнитуру
3. В `config.yaml`: `audio.device: null`

## Проблема: сервис f9-asr постоянно перезапускается / ImportError pynput

### Симптомы
- В логах: `Can't connect to display ":0"` или `Connection refused`

### Причина
Жёстко заданный `DISPLAY=:0`, а сессия GDM часто использует **:1**.

### Решение
Запуск через `scripts/f9-asr-launch.sh` (подставляется при `./scripts/install-service.sh`). Переустановите сервис из каталога проекта.

## Проблема: F9 не запускает запись

### Симптомы
- Нажатие F9 не дает реакции
- Нет уведомлений

### Решения

#### 1. Сервис не запущен

```bash
# Проверить статус
systemctl --user status f9-asr.service

# Запустить
systemctl --user start f9-asr.service
```

#### 2. Конфликт горячих клавиш

- Проверьте, не используется ли F9 другим приложением
- Отключите другие приложения, использующие F9

#### 3. Проблемы с pynput

```bash
# Проверить логи
journalctl --user -u f9-asr.service -f

# Если ошибки доступа к клавиатуре:
sudo usermod -a -G input $USER
# Перелогиньтесь
```

## Проблема: Текст не копируется в буфер обмена

### Решения

#### 1. xclip не установлен

```bash
sudo apt install xclip
```

#### 2. Проблемы с X11

```bash
# Проверить DISPLAY
echo $DISPLAY

# Должно быть :0 или :1
```

## Отладка

### Включить детальное логирование

1. Отредактируйте `config.yaml`:
```yaml
logging:
  level: "DEBUG"
```

2. Перезапустите сервис:
```bash
systemctl --user restart f9-asr.service
```

3. Смотрите логи:
```bash
journalctl --user -u f9-asr.service -f
```

### Сохранение файлов для отладки

При пустом результате файлы сохраняются в `/tmp/f9-asr-recordings/debug_*.wav`

Проверьте файл:
```bash
# Воспроизвести
aplay /tmp/f9-asr-recordings/debug_*.wav

# Проверить формат
file /tmp/f9-asr-recordings/debug_*.wav
```

### Тестирование API напрямую

```bash
# Записать тестовый файл (3 секунды, говорите четко)
timeout 3 arecord -f S16_LE -r 16000 -c 1 /tmp/test.wav

# Отправить на транскрипцию
curl -X POST http://localhost:8001/v1/audio/transcriptions \
  -F "file=@/tmp/test.wav" \
  -F "model=whisper" \
  -F "response_format=json"
```

## Получение помощи

Если проблема не решена:

1. Соберите информацию:
```bash
# Статус сервиса
systemctl --user status f9-asr.service

# Последние логи
journalctl --user -u f9-asr.service -n 100 --no-pager

# Версия Python и uv
python3 --version
uv --version

# Статус ASR сервиса
curl http://localhost:8001/healthz
```

2. Проверьте конфигурацию:
```bash
cat config.yaml
```

3. Проверьте формат записанного файла (если есть):
```bash
file /tmp/f9-asr-recordings/debug_*.wav
```
