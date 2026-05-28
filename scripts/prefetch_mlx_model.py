#!/usr/bin/env python3
"""Скачать веса MLX Whisper в Hugging Face Hub cache (~/.cache/huggingface/hub).
Читает transcription.mlx_whisper.model_name из config.yaml в корне проекта.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

_PROJECT = Path(__file__).resolve().parents[1]


def main() -> int:
    cfg_path = _PROJECT / "config.yaml"
    if not cfg_path.exists():
        print(f"Нет {cfg_path}", file=sys.stderr)
        return 1
    with cfg_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    repo = data.get("transcription", {}).get("mlx_whisper", {}).get("model_name")
    if not repo:
        print("В config.yaml не задан transcription.mlx_whisper.model_name", file=sys.stderr)
        return 1
    from huggingface_hub import snapshot_download

    print(f"Загрузка в HF cache: {repo}")
    path = snapshot_download(repo_id=repo)
    print(f"Готово: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
