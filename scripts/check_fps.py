#!/usr/bin/env python3
"""Скрипт для проверки FPS системы."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.core.person_zone_system import PersonZoneSystem
from src.utils.config import config
from src.utils.logger import logger


def main():

    video_path = "test_video/video.mkv"
    if not Path(video_path).exists():
        print(f"Ошибка: Не найден видеофайл {video_path}")
        return

    print("\nПРОВЕРКА FPS СИСТЕМЫ PERSON ZONE\n")
    print(f"Видео: {video_path}")
    print("\nТекущие настройки оптимизации:")
    print(
        f"- Режим работы: {'ДЕБАГ' if config.get('debug.debug_mode', True) else 'ПРОДАКШН'}"
    )
    print(f"- Пропуск кадров: каждый {config.get('detection.frame_skip', 1)}-й кадр")
    print(
        f"- Изменение размера: {'Да' if config.get('detection.resize_for_detection', False) else 'Нет'}"
    )
    print(f"- Размер детекции: {config.get('detection.detection_size', 640)}")
    print(f"- Порог уверенности: {config.get('detection.confidence', 0.7)}")
    print(f"- Ограничение FPS: {config.get('video.target_fps', 0) or 'Нет'}")

    print("\nНажмите ESC для выхода...\n")

    config.set("debug.debug_mode", True)
    config.set("debug.enable_keys", True)

    system = PersonZoneSystem(video_source=video_path)

    try:
        system.start()
    except KeyboardInterrupt:
        print("\n\nОстановлено пользователем")
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
    finally:
        if hasattr(system, "fps"):
            print(f"\nСредний FPS: {system.fps:.1f}")


if __name__ == "__main__":
    main()
