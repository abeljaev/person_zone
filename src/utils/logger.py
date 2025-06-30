"""
Модуль для логирования в проекте.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str, log_file: Optional[str] = None, level: int = logging.INFO
) -> logging.Logger:
    """
    Настройка логгера.

    Args:
        name: Имя логгера
        log_file: Путь к файлу логов (если None, логи выводятся только в консоль)
        level: Уровень логирования

    Returns:
        Настроенный логгер
    """
    # Создаем логгер
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Очищаем существующие обработчики
    logger.handlers = []

    # Формат сообщений
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Обработчик для записи в файл, если указан
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Создаем основной логгер приложения
logger = setup_logger("person_zone", "logs/app.log")
