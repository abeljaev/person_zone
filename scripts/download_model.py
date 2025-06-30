#!/usr/bin/env python3
"""
Скрипт для скачивания моделей YOLO в папку config.
"""

import argparse
import sys
from pathlib import Path
import shutil

sys.path.append(str(Path(__file__).parent.parent))

from ultralytics import YOLO


def main():

    parser = argparse.ArgumentParser(
        description="Скачивание моделей YOLO в папку config"
    )
    parser.add_argument(
        "--model",
        default="yolo11m.pt",
        help="Название модели для скачивания (по умолчанию: yolo11m.pt)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Перезаписать существующую модель"
    )

    args = parser.parse_args()

    config_dir = Path(__file__).parent.parent / "config"
    config_dir.mkdir(exist_ok=True)

    model_path = config_dir / args.model

    if model_path.exists() and not args.force:
        size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"Модель {args.model} уже существует ({size_mb:.1f} MB)")
        print(f"Путь: {model_path}")
        print("Используйте --force для перезаписи")
        return 0

    print(f"Скачивание модели {args.model} в {model_path}...")

    try:
        model = YOLO(args.model)

        possible_paths = [
            Path.home() / ".cache" / "ultralytics" / args.model,
            Path(args.model),
            Path.cwd() / args.model,
        ]

        source_path = None
        for path in possible_paths:
            if path.exists():
                source_path = path
                break

        if source_path:
            shutil.copy2(source_path, model_path)
            print(f"Модель успешно скопирована в {model_path}")

            size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"Размер модели: {size_mb:.1f} MB")

            if source_path.name == args.model and source_path.parent == Path.cwd():
                source_path.unlink()
                print(f"Временный файл удален")

        else:
            print(f"Не удалось найти скачанную модель {args.model}")
            return 1

    except Exception as e:
        print(f"Ошибка при скачивании модели: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
