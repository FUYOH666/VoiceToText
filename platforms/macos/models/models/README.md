# Модели Whisper для VTTv2

Эта директория предназначена для хранения моделей Whisper для локальной транскрипции.

## Модель Large v3 (рекомендуется)

Для максимальной точности транскрипции рекомендуется использовать модель **ggml-large-v3.bin** (~2.9 GB).

### Скачивание модели

#### Вариант 1: Через curl (рекомендуется)

```bash
mkdir -p models
cd models
curl -L "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin" -o ggml-large-v3.bin
cd ..
```

#### Вариант 2: Через браузер

1. Откройте ссылку: https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin
2. Скачайте файл `ggml-large-v3.bin`
3. Переместите его в директорию `models/`

#### Вариант 3: Через официальный скрипт whisper.cpp

```bash
cd whisper.cpp
bash models/download-ggml-model.sh large-v3
mv models/ggml-large-v3.bin ../models/
cd ..
```

### Проверка установки

После скачивания проверьте:

```bash
ls -lh models/ggml-large-v3.bin
# Должен показать размер ~2.9 GB
```

### Альтернативные модели

Если модель Large слишком большая, можно использовать более легкие варианты:

- **ggml-medium-v3.bin** (~1.5 GB) - хороший баланс скорости и точности
- **ggml-small-v3.bin** (~500 MB) - быстрее, но менее точно
- **ggml-base-v3.bin** (~150 MB) - самая быстрая, но наименее точная

Скачать их можно аналогично, заменив `large-v3` на нужную модель в URL.

### Конфигурация

После скачивания модели путь в `config.yaml` должен быть:

```yaml
transcription:
  whisper_cpp:
    model_path: "./models/ggml-large-v3.bin"
```

### Примечания

- Модель не включена в репозиторий из-за размера (~2.9 GB)
- Модель нужно скачать один раз после клонирования репозитория
- После установки приложение работает полностью офлайн
- Модель Large v3 обеспечивает максимальную точность для русского языка
