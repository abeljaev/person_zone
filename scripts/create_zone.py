#!/usr/bin/env python3
"""
Скрипт для создания зоны на кадре.
"""
import argparse
import sys
import cv2
import numpy as np
from pathlib import Path

# Добавляем корневую директорию проекта в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.zone import ZoneManager, Zone
from src.utils.logger import logger


class ZoneCreator:
    """Класс для создания зоны на изображении с помощью GUI."""

    def __init__(self, image_path: str, output_file: str = None):
        """
        Инициализация создателя зон.

        Args:
            image_path: Путь к изображению
            output_file: Путь для сохранения зон (если None, используется из конфигурации)
        """
        self.image_path = image_path
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError(f"Не удалось загрузить изображение: {image_path}")

        # Создаем копию изображения для отрисовки
        self.drawing_image = self.image.copy()

        # Инициализируем менеджер зон
        self.zone_manager = ZoneManager(output_file)

        # Точки текущей зоны
        self.current_points = []

        # Имя окна
        self.window_name = "Zone Creator"

        # Флаг завершения создания зоны
        self.zone_completed = False

        # Текущее имя зоны
        self.current_zone_name = f"Zone_{len(self.zone_manager.zones) + 1}"

        # Текущий цвет зоны (BGR)
        self.current_color = (0, 255, 0)  # Зеленый по умолчанию

    def mouse_callback(self, event, x, y, flags, param):
        """Обработчик событий мыши."""
        if self.zone_completed:
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            # Добавляем точку
            self.current_points.append([x, y])

            # Обновляем изображение
            self.update_drawing()

        elif event == cv2.EVENT_RBUTTONDOWN:
            # Завершаем создание зоны, если есть хотя бы 3 точки
            if len(self.current_points) >= 3:
                self.complete_zone()
            else:
                logger.warning("Для создания зоны нужно не менее 3 точек")

    def update_drawing(self):
        """Обновление изображения с отрисовкой текущей зоны."""
        # Копируем исходное изображение
        self.drawing_image = self.image.copy()

        # Отрисовываем существующие зоны
        self.drawing_image = self.zone_manager.draw_zones(self.drawing_image)

        # Отрисовываем текущие точки
        for i, point in enumerate(self.current_points):
            cv2.circle(self.drawing_image, tuple(point), 5, self.current_color, -1)
            cv2.putText(
                self.drawing_image,
                str(i + 1),
                (point[0] + 10, point[1] + 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                self.current_color,
                2,
            )

        # Соединяем точки линиями
        if len(self.current_points) > 1:
            for i in range(len(self.current_points) - 1):
                cv2.line(
                    self.drawing_image,
                    tuple(self.current_points[i]),
                    tuple(self.current_points[i + 1]),
                    self.current_color,
                    2,
                )

            # Если есть хотя бы 3 точки, соединяем последнюю с первой
            if len(self.current_points) >= 3:
                cv2.line(
                    self.drawing_image,
                    tuple(self.current_points[-1]),
                    tuple(self.current_points[0]),
                    self.current_color,
                    2,
                    cv2.LINE_AA,
                )

        # Обновляем окно
        cv2.imshow(self.window_name, self.drawing_image)

    def complete_zone(self):
        """Завершение создания текущей зоны."""
        # Добавляем зону в менеджер
        self.zone_manager.add_zone(
            self.current_points, name=self.current_zone_name, color=self.current_color
        )

        # Сбрасываем текущие точки
        self.current_points = []

        # Обновляем имя для следующей зоны
        self.current_zone_name = f"Zone_{len(self.zone_manager.zones) + 1}"

        # Генерируем новый случайный цвет
        self.current_color = (
            np.random.randint(0, 255),
            np.random.randint(0, 255),
            np.random.randint(0, 255),
        )

        # Обновляем изображение
        self.update_drawing()

        logger.info(f"Зона '{self.current_zone_name}' создана")

    def save_zones(self):
        """Сохранение всех зон."""
        # Получаем разрешение изображения
        image_resolution = (self.image.shape[1], self.image.shape[0])  # (width, height)

        if self.zone_manager.save_zones(save_resolution=image_resolution):
            logger.info(f"Зоны сохранены в {self.zone_manager.zones_file}")
            logger.info(f"Разрешение изображения: {image_resolution}")
            return True
        return False

    def run(self):
        """Запуск интерфейса для создания зон."""
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        # Отображаем инструкции
        print("Инструкции:")
        print("- Левая кнопка мыши: добавить точку")
        print("- Правая кнопка мыши: завершить текущую зону")
        print("- 'c': очистить текущие точки")
        print("- 'r': удалить последнюю зону")
        print("- 's': сохранить зоны и выйти")
        print("- 'q' или ESC: выйти без сохранения")

        # Отрисовываем начальное изображение
        self.update_drawing()

        while True:
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:  # q или ESC
                break

            elif key == ord("c"):  # Очистить текущие точки
                self.current_points = []
                self.update_drawing()
                logger.info("Текущие точки очищены")

            elif key == ord("r"):  # Удалить последнюю зону
                if self.zone_manager.zones:
                    self.zone_manager.remove_zone(len(self.zone_manager.zones) - 1)
                    self.update_drawing()
                    self.current_zone_name = f"Zone_{len(self.zone_manager.zones) + 1}"
                else:
                    logger.warning("Нет зон для удаления")

            elif key == ord("s"):  # Сохранить и выйти
                if self.save_zones():
                    break

        cv2.destroyAllWindows()


def parse_args():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(description="Создание зон на изображении")

    parser.add_argument(
        "-i", "--image", type=str, required=True, help="Путь к изображению"
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Путь для сохранения файла зон (JSON)",
    )

    return parser.parse_args()


def main():
    """Основная функция скрипта."""
    args = parse_args()

    try:
        # Создаем экземпляр ZoneCreator
        zone_creator = ZoneCreator(args.image, args.output)

        # Запускаем интерфейс
        zone_creator.run()

        return 0
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
