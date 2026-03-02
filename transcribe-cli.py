#!/usr/bin/env python3
"""
CLI транскрипции для OpenClaw
Использует MLX Whisper (large-v3) оптимизированный для Apple Silicon

Usage:
    transcribe-cli.py <audio_file>
    
Выводит транскрипцию на stdout.
"""
import sys
import os

# Добавляем путь к модулям VTT-MLX-m4
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import soundfile as sf
import mlx_whisper

# Конфигурация (такая же как в твоём config.yaml)
MODEL_NAME = "mlx-community/whisper-large-v3-mlx"
SAMPLE_RATE = 16000


def load_audio(file_path: str) -> np.ndarray:
    """Загрузка и подготовка аудио файла"""
    # Читаем аудио
    audio_data, sr = sf.read(file_path, dtype='float32')
    
    # Конвертируем в моно если стерео
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)
    
    # Ресемплируем если нужно (MLX ожидает 16kHz)
    if sr != SAMPLE_RATE:
        try:
            import librosa
            audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=SAMPLE_RATE)
        except ImportError:
            # Простой ресемплинг без librosa
            ratio = SAMPLE_RATE / sr
            new_length = int(len(audio_data) * ratio)
            indices = np.linspace(0, len(audio_data) - 1, new_length).astype(int)
            audio_data = audio_data[indices]
    
    # Нормализация
    max_val = max(abs(audio_data.max()), abs(audio_data.min()))
    if max_val > 1.0:
        audio_data = audio_data / max_val
    
    return audio_data.astype(np.float32)


def transcribe(audio_data: np.ndarray) -> str:
    """Транскрипция через MLX Whisper"""
    result = mlx_whisper.transcribe(
        audio_data,
        path_or_hf_repo=MODEL_NAME,
        language=None,  # Автоопределение
        temperature=0.0,
        verbose=False,
    )
    
    # Извлечение текста
    if isinstance(result, dict):
        return result.get("text", "").strip()
    return str(result).strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: transcribe-cli.py <audio_file>", file=sys.stderr)
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    if not os.path.exists(audio_file):
        print(f"Error: File not found: {audio_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Загрузка аудио
        audio_data = load_audio(audio_file)
        
        # Транскрипция
        text = transcribe(audio_data)
        
        # Вывод результата
        print(text)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
