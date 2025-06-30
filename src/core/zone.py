"""
Модуль для работы с зонами на видео.
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Union, Optional

from shapely.geometry import Point, Polygon
from src.utils.logger import logger
from src.utils.config import config


class Zone:
    """Класс для представления зоны на видео."""

    def __init__(
        self,
        points: List[List[int]],
        name: str = "Zone",
        color: Tuple[int, int, int] = (0, 255, 0),
    ):
        """
        Инициализация зоны.

        Args:
            points: Список точек, определяющих полигон зоны [[x1, y1], [x2, y2], ...]
            name: Имя зоны
            color: Цвет зоны в формате BGR
        """
        self.points = points
        self.name = name
        self.color = color

        # Создаем полигон для проверки вхождения точек
        self.polygon = Polygon(points)

        logger.debug(f"Создана зона '{name}' с {len(points)} точками")

    def is_point_inside(self, point: Union[Tuple[int, int], List[int], Point]) -> bool:
        """
        Проверка, находится ли точка внутри зоны.

        Args:
            point: Точка для проверки (x, y)

        Returns:
            True, если точка внутри зоны, иначе False
        """
        if isinstance(point, (tuple, list)):
            point = Point(point)

        return self.polygon.contains(point)

    def draw(
        self,
        frame: np.ndarray,
        thickness: int = 2,
        fill: bool = False,
        alpha: float = 0.3,
    ) -> np.ndarray:
        """
        Отрисовка зоны на кадре.

        Args:
            frame: Кадр для отрисовки
            thickness: Толщина линии (если fill=False)
            fill: Заполнять ли полигон цветом
            alpha: Прозрачность заполнения (0-1), используется только если fill=True

        Returns:
            Кадр с отрисованной зоной
        """
        # Создаем копию кадра для отрисовки
        result = frame.copy()

        # Преобразуем точки в формат для OpenCV
        points = np.array(self.points, np.int32).reshape((-1, 1, 2))

        if fill:
            # Создаем маску для заполнения
            mask = np.zeros_like(frame)
            cv2.fillPoly(mask, [points], self.color)

            # Накладываем маску с прозрачностью
            cv2.addWeighted(mask, alpha, result, 1 - alpha, 0, result)

            # Рисуем контур поверх заполнения
            cv2.polylines(result, [points], True, self.color, thickness)
        else:
            # Рисуем только контур
            cv2.polylines(result, [points], True, self.color, thickness)

        # Добавляем название зоны
        if self.points:
            text_pos = (self.points[0][0], self.points[0][1] - 10)
            cv2.putText(
                result,
                self.name,
                text_pos,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                self.color,
                2,
                cv2.LINE_AA,
            )

        return result


class ZoneManager:
    """Класс для управления зонами."""

    def __init__(
        self,
        zones_file: Optional[str] = None,
        target_resolution: Optional[Tuple[int, int]] = None,
    ):
        """
        Инициализация менеджера зон.

        Args:
            zones_file: Путь к файлу с зонами. Если None, используется из конфигурации.
            target_resolution: Целевое разрешение (width, height) для автоматического масштабирования зон
        """
        self.zones_file = zones_file or config.get("zones.file", "config/zones.json")
        self.zones: List[Zone] = []
        self.target_resolution = target_resolution
        self.original_resolution: Optional[Tuple[int, int]] = None

        # Загружаем зоны, если файл существует
        self.load_zones()

    def load_zones(self) -> None:
        """Загрузка зон из файла."""
        try:
            zones_path = Path(self.zones_file)
            if not zones_path.exists():
                logger.warning(f"Файл зон не найден: {self.zones_file}")
                return

            with open(zones_path, "r") as f:
                data = json.load(f)

            # Загружаем метаданные о разрешении
            metadata = data.get("metadata", {})
            self.original_resolution = metadata.get("resolution")
            if self.original_resolution:
                self.original_resolution = tuple(self.original_resolution)
                logger.info(
                    f"Загружено исходное разрешение зон: {self.original_resolution}"
                )

            self.zones = []
            for zone_data in data.get("zones", []):
                points = zone_data.get("points", [])
                name = zone_data.get("name", "Zone")
                color = tuple(zone_data.get("color", [0, 255, 0]))

                # Масштабируем точки, если нужно
                if self.target_resolution and self.original_resolution:
                    points = self._scale_points(
                        points, self.original_resolution, self.target_resolution
                    )
                    logger.debug(
                        f"Зона '{name}' масштабирована с {self.original_resolution} на {self.target_resolution}"
                    )

                self.zones.append(Zone(points, name, color))

            logger.info(f"Загружено {len(self.zones)} зон из {self.zones_file}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке зон: {str(e)}")

    def save_zones(self, save_resolution: Optional[Tuple[int, int]] = None) -> bool:
        """
        Сохранение зон в файл.

        Args:
            save_resolution: Разрешение для сохранения (если None, используется текущее целевое разрешение)

        Returns:
            True, если сохранение успешно, иначе False
        """
        try:
            zones_path = Path(self.zones_file)
            zones_path.parent.mkdir(parents=True, exist_ok=True)

            # Определяем разрешение для сохранения
            resolution_to_save = (
                save_resolution or self.target_resolution or self.original_resolution
            )

            # Преобразуем зоны в формат для сохранения
            zones_data = {
                "metadata": {
                    "resolution": (
                        list(resolution_to_save) if resolution_to_save else None
                    ),
                    "created_at": str(np.datetime64("now")),
                    "zones_count": len(self.zones),
                },
                "zones": [
                    {
                        "name": zone.name,
                        "points": zone.points,
                        "color": list(zone.color),
                    }
                    for zone in self.zones
                ],
            }

            with open(zones_path, "w") as f:
                json.dump(zones_data, f, indent=4)

            logger.info(f"Сохранено {len(self.zones)} зон в {self.zones_file}")
            if resolution_to_save:
                logger.info(f"Разрешение зон: {resolution_to_save}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении зон: {str(e)}")
            return False

    def add_zone(
        self,
        points: List[List[int]],
        name: str = None,
        color: Tuple[int, int, int] = None,
    ) -> Zone:
        """
        Добавление новой зоны.

        Args:
            points: Список точек, определяющих полигон зоны [[x1, y1], [x2, y2], ...]
            name: Имя зоны (если None, генерируется автоматически)
            color: Цвет зоны в формате BGR (если None, выбирается случайный цвет)

        Returns:
            Созданная зона
        """
        # Генерируем имя, если не указано
        if name is None:
            name = f"Zone_{len(self.zones) + 1}"

        # Генерируем случайный цвет, если не указан
        if color is None:
            color = (
                np.random.randint(0, 255),
                np.random.randint(0, 255),
                np.random.randint(0, 255),
            )

        # Создаем и добавляем зону
        zone = Zone(points, name, color)
        self.zones.append(zone)

        logger.info(f"Добавлена зона '{name}' с {len(points)} точками")
        return zone

    def remove_zone(self, index: int) -> bool:
        """
        Удаление зоны по индексу.

        Args:
            index: Индекс зоны для удаления

        Returns:
            True, если зона успешно удалена, иначе False
        """
        if 0 <= index < len(self.zones):
            zone = self.zones.pop(index)
            logger.info(f"Удалена зона '{zone.name}'")
            return True
        else:
            logger.error(
                f"Невозможно удалить зону с индексом {index}, всего зон: {len(self.zones)}"
            )
            return False

    def draw_zones(self, frame: np.ndarray, fill: bool = True) -> np.ndarray:
        """
        Отрисовка всех зон на кадре.

        Args:
            frame: Кадр для отрисовки
            fill: Заполнять ли полигоны цветом

        Returns:
            Кадр с отрисованными зонами
        """
        result = frame.copy()
        for zone in self.zones:
            result = zone.draw(result, fill=fill)
        return result

    def check_point(
        self, point: Union[Tuple[int, int], List[int], Point]
    ) -> List[Zone]:
        """
        Проверка, в каких зонах находится точка.

        Args:
            point: Точка для проверки (x, y)

        Returns:
            Список зон, в которых находится точка
        """
        return [zone for zone in self.zones if zone.is_point_inside(point)]

    def _scale_points(
        self,
        points: List[List[int]],
        from_resolution: Tuple[int, int],
        to_resolution: Tuple[int, int],
    ) -> List[List[int]]:
        """
        Масштабирование точек зоны с одного разрешения на другое.

        Args:
            points: Исходные точки зоны
            from_resolution: Исходное разрешение (width, height)
            to_resolution: Целевое разрешение (width, height)

        Returns:
            Масштабированные точки
        """
        if from_resolution == to_resolution:
            return points

        from_width, from_height = from_resolution
        to_width, to_height = to_resolution

        scale_x = to_width / from_width
        scale_y = to_height / from_height

        scaled_points = []
        for point in points:
            x, y = point
            scaled_x = int(x * scale_x)
            scaled_y = int(y * scale_y)
            scaled_points.append([scaled_x, scaled_y])

        return scaled_points

    def set_target_resolution(self, resolution: Tuple[int, int]) -> None:
        """
        Установка целевого разрешения и автоматическое масштабирование существующих зон.

        Args:
            resolution: Целевое разрешение (width, height)
        """
        if self.target_resolution == resolution:
            return

        old_resolution = self.target_resolution
        self.target_resolution = resolution

        # Если есть исходное разрешение и зоны, масштабируем их
        if self.original_resolution and self.zones:
            logger.info(
                f"Масштабирование зон с {self.original_resolution} на {resolution}"
            )

            for zone in self.zones:
                # Масштабируем точки зоны
                if old_resolution:
                    # Сначала возвращаем к исходному разрешению
                    zone.points = self._scale_points(
                        zone.points, old_resolution, self.original_resolution
                    )

                # Затем масштабируем к новому разрешению
                zone.points = self._scale_points(
                    zone.points, self.original_resolution, resolution
                )

                # Пересоздаем полигон
                zone.polygon = Polygon(zone.points)
