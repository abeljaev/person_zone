#!/usr/bin/env python3
"""
Скрипт для захвата кадра из видео.
"""
import argparse
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.video import VideoReader
from src.utils.logger import logger


def parse_args():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(description="Захват кадра из видео")

    parser.add_argument(
        "-s",
        "--source",
        type=str,
        default=None,
        help="Путь к видеофайлу или RTSP-потоку",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="captured_frame.jpg",
        help="Путь для сохранения кадра",
    )

    parser.add_argument(
        "-p",
        "--position",
        type=float,
        default=0.0,
        help="Позиция кадра в видео (в секундах)",
    )

    return parser.parse_args()


def main():
    """Основная функция скрипта."""
    args = parse_args()

    # Создаем экземпляр VideoReader
    video_reader = VideoReader(args.source)

    # Открываем видеопоток
    if not video_reader.open():
        logger.error("Не удалось открыть видеопоток")
        return 1

    # Получаем кадр в указанной позиции
    success, frame = video_reader.get_frame_at_position(args.position)

    # Закрываем видеопоток
    video_reader.close()

    if not success:
        logger.error(f"Не удалось получить кадр в позиции {args.position} секунд")
        return 1

    # Сохраняем кадр
    output_path = Path(args.output)
    try:
        # Создаем директорию, если её нет
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Сохраняем кадр с помощью OpenCV
        import cv2

        if cv2.imwrite(str(output_path), frame):
            logger.info(f"Кадр успешно сохранен в {output_path}")
        else:
            logger.error(f"Не удалось сохранить кадр в {output_path}")
            return 1
    except Exception as e:
        logger.error(f"Ошибка при сохранении кадра: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
