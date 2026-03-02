#!/usr/bin/env python3
"""
Тест скорости транскрипции для разных длин записей
"""
import sys
import time
import numpy as np
from pathlib import Path

sys.path.insert(0, 'src/vtt2')

from config.loader import Config
from transcription.mlx_engine import MLXWhisperTranscriber

def generate_test_audio(duration_seconds: int, sample_rate: int = 16000) -> np.ndarray:
    """Генерация тестового аудио (белый шум с тоном)"""
    samples = duration_seconds * sample_rate
    # Генерируем простой тон + шум для имитации речи
    t = np.linspace(0, duration_seconds, samples)
    audio = np.sin(2 * np.pi * 440 * t) * 0.3 + np.random.randn(samples).astype(np.float32) * 0.1
    # Нормализация
    audio = audio / np.max(np.abs(audio))
    return audio.astype(np.float32)

def test_transcription_speed(config_path: str = "config.yaml"):
    """Тест скорости транскрипции"""
    print("=" * 60)
    print("ТЕСТ СКОРОСТИ ТРАНСКРИПЦИИ")
    print("=" * 60)
    
    # Загрузка конфигурации
    project_root = Path.cwd()
    config = Config.from_yaml(config_path, project_root)
    
    # Инициализация транскрибера
    print("\n📦 Инициализация транскрибера...")
    transcriber = MLXWhisperTranscriber(config)
    print(f"✅ Модель: {config.transcription.mlx_whisper.model_name}")
    print(f"✅ Язык: {config.transcription.mlx_whisper.language}")
    print(f"✅ Chunk size: {config.transcription.mlx_whisper.chunk_size_seconds}s")
    print(f"✅ Batch size: {config.transcription.mlx_whisper.batch_size}")
    
    # Тестовые длительности
    test_durations = [5, 15, 30, 60, 120, 300]  # 5 сек, 15 сек, 30 сек, 1 мин, 2 мин, 5 мин
    
    results = []
    
    for duration in test_durations:
        print(f"\n{'='*60}")
        print(f"Тест: {duration} секунд ({duration/60:.1f} минут)")
        print(f"{'='*60}")
        
        # Генерация тестового аудио
        print(f"📝 Генерация тестового аудио...")
        audio = generate_test_audio(duration)
        print(f"✅ Сгенерировано: {len(audio)} сэмплов ({len(audio)/16000:.1f}s)")
        
        # Транскрипция
        print(f"🎤 Начало транскрипции...")
        start_time = time.time()
        
        try:
            text = transcriber.transcribe(audio)
            elapsed = time.time() - start_time
            
            # Расчет метрик
            speed_factor = duration / elapsed if elapsed > 0 else 0
            chars_per_second = len(text) / elapsed if elapsed > 0 else 0
            
            results.append({
                'duration': duration,
                'transcription_time': elapsed,
                'speed_factor': speed_factor,
                'text_length': len(text),
                'chars_per_second': chars_per_second,
                'success': True
            })
            
            print(f"✅ Транскрипция завершена!")
            print(f"   Время транскрипции: {elapsed:.2f} секунд")
            print(f"   Скорость: {speed_factor:.2f}x реального времени")
            print(f"   Длина текста: {len(text)} символов")
            print(f"   Скорость: {chars_per_second:.1f} символов/сек")
            
        except Exception as e:
            elapsed = time.time() - start_time
            results.append({
                'duration': duration,
                'transcription_time': elapsed,
                'speed_factor': 0,
                'text_length': 0,
                'chars_per_second': 0,
                'success': False,
                'error': str(e)
            })
            print(f"❌ Ошибка: {e}")
        
        # Небольшая пауза между тестами
        if duration < test_durations[-1]:
            print("⏸️  Пауза 2 секунды...")
            time.sleep(2)
    
    # Итоговая статистика
    print(f"\n{'='*60}")
    print("ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'='*60}")
    print(f"{'Длительность':<15} {'Время транскрипции':<20} {'Скорость':<15} {'Статус':<10}")
    print("-" * 60)
    
    for r in results:
        duration_str = f"{r['duration']}s ({r['duration']/60:.1f}м)"
        time_str = f"{r['transcription_time']:.2f}s"
        speed_str = f"{r['speed_factor']:.2f}x" if r['success'] else "N/A"
        status_str = "✅" if r['success'] else "❌"
        
        print(f"{duration_str:<15} {time_str:<20} {speed_str:<15} {status_str:<10}")
    
    # Средняя скорость
    successful = [r for r in results if r['success']]
    if successful:
        avg_speed = sum(r['speed_factor'] for r in successful) / len(successful)
        print(f"\n📊 Средняя скорость транскрипции: {avg_speed:.2f}x реального времени")
    
    return results

if __name__ == "__main__":
    test_transcription_speed()

