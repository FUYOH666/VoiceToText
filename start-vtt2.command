#!/bin/bash
cd "$(dirname "$0")"
# Используем .venv напрямую (uv run падает на rumps)
exec .venv/bin/python src/vtt2/main.py
