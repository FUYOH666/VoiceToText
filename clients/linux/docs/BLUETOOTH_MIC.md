# Bluetooth микрофон и F9 ASR

F9 ASR поддерживает Bluetooth-гарнитуры с микрофоном. Настройка проверена на Ubuntu 24.04 с PipeWire + WirePlumber.

## Быстрая настройка (3 шага)

### 1. Конфиг WirePlumber

Создайте файл `~/.config/wireplumber/bluetooth.lua.d/51-headset-profile.lua`:

```lua
-- Режим гарнитуры (HFP) — включает микрофон Bluetooth-устройства
table.insert(bluez_monitor.rules, {
  matches = { { { "device.name", "matches", "bluez_card.*" } } },
  apply_properties = { ["device.profile"] = "headset-head-unit" },
})
```

### 2. Переподключить гарнитуру

```bash
systemctl --user restart wireplumber
bluetoothctl disconnect <MAC>
bluetoothctl connect <MAC>
```

Или через Параметры → Bluetooth: отключить и подключить гарнитуру заново.

### 3. Установить микрофон по умолчанию (опционально)

```bash
wpctl status   # найти ID источника (Source) вашей гарнитуры
wpctl set-default <ID>
```

Готово. F9 ASR с `device: null` будет записывать с Bluetooth-микрофона.

## Настройка F9 ASR

В `config.yaml` используйте системный default:

```yaml
audio:
  device: null
```

## Почему микрофон не виден

Bluetooth по умолчанию подключается в режиме **A2DP** (только воспроизведение):
- ✅ Звук в наушниках
- ❌ Микрофон недоступен

Решение: конфиг WirePlumber выше переключает устройство в режим **Headset (HFP)** при подключении.

**Важно:** в HFP качество звука может быть ниже, зато микрофон работает.

## Альтернатива: встроенный микрофон

Если нужен встроенный микрофон вместо Bluetooth:

```yaml
audio:
  device: "plughw:CARD=Generic_1,DEV=0"
```

Или вручную: `wpctl set-default <ID_встроенного_микрофона>`

## Проверка

```bash
# Список устройств
arecord -l
wpctl status

# Тест записи (3 сек)
timeout 3 arecord -f S16_LE -r 16000 -c 1 /tmp/test.wav
aplay /tmp/test.wav
```

## Требования

- Ubuntu 24.04+ (PipeWire, WirePlumber)
- libspa-0.2-bluetooth (обычно ставится с pipewire-audio)
