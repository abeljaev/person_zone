#!/usr/bin/env python3
"""Скрипт для измерения FPS с разными настройками оптимизации."""

import time
import cv2
import numpy as np
from typing import Dict, List, Tuple
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.core.person_zone_system import PersonZoneSystem
from src.utils.config import config
from src.utils.logger import logger


def benchmark_configuration(
    name: str,
    settings: Dict[str, any],
    duration: float = 10.0,
    video_source: str = "test_video/video.mkv",
) -> Tuple[float, int]:
    """
    Запускает бенчмарк с заданными настройками.

    Args:
        name: Название конфигурации
        settings: Словарь с настройками
        duration: Длительность теста в секундах
        video_source: Путь к видео файлу

    Returns:
        Кортеж (средний FPS, количество обработанных кадров)
    """

    for key, value in settings.items():
        config.set(key, value)

    system = PersonZoneSystem(video_source=video_source)

    if not system.video_reader.open():
        logger.error(f"Не удалось открыть видео для конфигурации {name}")
        return 0.0, 0

    config.set("debug.show_video", False)

    logger.info(f"Запуск бенчмарка: {name}")

    frames_processed = 0
    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            ret, frame = system.video_reader.read_frame()
            if not ret:

                system.video_reader.close()
                system.video_reader.open()
                continue

            system.frame_counter += 1
            if system.frame_counter % system.frame_skip == 0:
                system.process_frame(frame)
                frames_processed += 1

    except Exception as e:
        logger.error(f"Ошибка в бенчмарке {name}: {str(e)}")
    finally:
        system.stop()

    elapsed_time = time.time() - start_time
    avg_fps = frames_processed / elapsed_time if elapsed_time > 0 else 0

    return avg_fps, frames_processed


def main():

    video_path = "test_video/video.mkv"
    if not Path(video_path).exists():
        print(f"Ошибка: Не найден видеофайл {video_path}")
        print("Пожалуйста, поместите тестовый видеофайл в папку test_video/")
        return

    configurations = [
        {
            "name": "Базовая (без оптимизаций)",
            "settings": {
                "detection.frame_skip": 1,
                "detection.resize_for_detection": False,
                "debug.enable_visualization": True,
                "video.target_fps": 0,
            },
        },
        {
            "name": "Пропуск кадров (каждый 2-й)",
            "settings": {
                "detection.frame_skip": 2,
                "detection.resize_for_detection": False,
                "debug.enable_visualization": True,
                "video.target_fps": 0,
            },
        },
        {
            "name": "Изменение размера для детекции",
            "settings": {
                "detection.frame_skip": 1,
                "detection.resize_for_detection": True,
                "detection.detection_size": 640,
                "debug.enable_visualization": True,
                "video.target_fps": 0,
            },
        },
        {
            "name": "Без визуализации",
            "settings": {
                "detection.frame_skip": 1,
                "detection.resize_for_detection": False,
                "debug.enable_visualization": False,
                "video.target_fps": 0,
            },
        },
        {
            "name": "Все оптимизации",
            "settings": {
                "detection.frame_skip": 2,
                "detection.resize_for_detection": True,
                "detection.detection_size": 640,
                "debug.enable_visualization": False,
                "video.target_fps": 0,
            },
        },
        {
            "name": "Агрессивная оптимизация",
            "settings": {
                "detection.frame_skip": 3,
                "detection.resize_for_detection": True,
                "detection.detection_size": 480,
                "debug.enable_visualization": False,
                "video.target_fps": 0,
                "detection.confidence": 0.8,
            },
        },
    ]

    results = []

    print("\nБЕНЧМАРК ПРОИЗВОДИТЕЛЬНОСТИ PERSON ZONE SYSTEM\n")
    print(f"Используется видео: {video_path}")
    print("Каждый тест выполняется 10 секунд...\n")

    for cfg in configurations:
        fps, frames = benchmark_configuration(
            cfg["name"], cfg["settings"], duration=10.0, video_source=video_path
        )
        results.append({"name": cfg["name"], "fps": fps, "frames": frames})

        print(f"✓ {cfg['name']}: {fps:.1f} FPS ({frames} кадров)")
        time.sleep(1)

    best = max(results, key=lambda x: x["fps"])
    baseline_fps = results[0]["fps"] if results else 1.0

    print("\nИТОГОВЫЕ РЕЗУЛЬТАТЫ:\n")
    print(f"{'Конфигурация':<40} {'FPS':>8} {'Прирост':>10}")
    print("-" * 60)

    for result in results:
        improvement = (
            ((result["fps"] - baseline_fps) / baseline_fps * 100)
            if baseline_fps > 0
            else 0
        )
        print(f"{result['name']:<40} {result['fps']:>8.1f} {improvement:>9.1f}%")

    print(f"\nЛучший результат: {best['name']} с {best['fps']:.1f} FPS")

    print("\nРЕКОМЕНДАЦИИ ДЛЯ ПОВЫШЕНИЯ FPS:\n")
    print(
        "1. Используйте более легкую модель YOLO (например, yolov8n.pt вместо yolo11.pt)"
    )
    print("2. Увеличьте frame_skip для пропуска большего количества кадров")
    print("3. Уменьшите detection_size для более быстрой детекции")
    print("4. Отключите визуализацию в production (enable_visualization: false)")
    print("5. Используйте GPU для ускорения YOLO (если доступен)")
    print(
        "6. Рассмотрите использование более простого трекера (botsort вместо bytetrack)"
    )


if __name__ == "__main__":
    main()
