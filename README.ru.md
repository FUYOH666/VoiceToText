# VoiceToText — голос в текст (бесплатно, локально)

**Бесплатный** клиент для macOS и Linux: нажали горячую клавишу — получили текст в активном приложении.  
По умолчанию **Whisper на вашем Mac** (MLX, Apple Silicon), без облака и без аккаунта.

[English README](README.md)

## Быстрый старт (Mac M1, локально)

```bash
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText
git checkout product-unified
uv sync --extra mac --extra local-mlx
./.venv/bin/python src/vtt2/main.py
```

Опционально — скачать модель заранее:

```bash
uv run python scripts/prefetch_mlx_model.py
```

**Option+Space** — запись; повторное нажатие — транскрипция и вставка текста.

## Профили

| Профиль | Режим |
|---------|--------|
| `mac-m1-local` | MLX на Mac (по умолчанию) |
| `mac-m1-remote` | ASR на вашем сервере (Tailscale) |
| `mac-m4-local` / `mac-m4-remote` | M4 |
| `linux-f9-local` / `linux-f9-edge` | Linux, клавиша F9 |

Файл `.env.local` нужен **только** для remote-профилей (`*-remote`, `linux-f9-edge`).

## Устранение неполадок

[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — если в логе `remote_asr_engine`, а нужен локальный MLX: перезапустите приложение с `mac-m1-local`.

## Участие

[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md)

## Лицензия

MIT
