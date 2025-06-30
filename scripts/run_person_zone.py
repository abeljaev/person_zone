#!/usr/bin/env python3
"""
Скрипт для запуска системы детекции и трекинга людей в зонах.
"""

import argparse
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.person_zone_system import PersonZoneSystem
from src.utils.logger import logger
from src.utils.config import config


def parse_args():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Система детекции и трекинга людей в зонах"
    )

    parser.add_argument(
        "--video", "-v", type=str, help="Путь к видеофайлу или RTSP-поток"
    )

    parser.add_argument("--zones", "-z", type=str, help="Путь к файлу с зонами")

    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Включить режим отладки (эмуляция API + визуализация)",
    )

    parser.add_argument(
        "--production",
        "-p",
        action="store_true",
        help="Включить продакшн режим (реальная API + headless)",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config/config.yaml",
        help="Путь к файлу конфигурации",
    )

    return parser.parse_args()


def main():
    """Основная функция."""
    args = parse_args()

    # Загружаем конфигурацию, если указан путь
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            config.__init__(config_path)
            logger.info(f"Загружена конфигурация из {config_path}")
        else:
            logger.error(f"Файл конфигурации не найден: {config_path}")
            return 1

    # Устанавливаем режим работы
    if args.debug and args.production:
        logger.error("Нельзя одновременно включить debug и production режимы")
        return 1
    elif args.debug:
        config.set("debug.debug_mode", True)
        logger.info("Включен режим отладки: API эмуляция + визуализация")
    elif args.production:
        config.set("debug.debug_mode", False)
        logger.info("Включен продакшн режим: реальная API + headless")
    else:
        # Используем настройку из конфига
        debug_mode = config.get("debug.debug_mode", True)
        mode_text = "отладки" if debug_mode else "продакшн"
        logger.info(f"Используется режим из конфига: {mode_text}")

    # Создаем и запускаем систему
    system = PersonZoneSystem(video_source=args.video, zones_file=args.zones)

    try:
        system.start()
    except KeyboardInterrupt:
        logger.info("Работа системы прервана пользователем")
    except Exception as e:
        logger.error(f"Ошибка при работе системы: {str(e)}")
        return 1
    finally:
        system.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
