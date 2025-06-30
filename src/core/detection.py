import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

from src.utils.logger import logger
from src.utils.config import config


class Detection:
    """Класс для представления результата детекции объекта."""

    def __init__(
        self,
        box: Tuple[int, int, int, int],
        confidence: float,
        class_id: int,
        frame_id: int = 0,
    ):
        """
        Инициализация детекции.

        Args:
            box: Ограничивающая рамка в формате (x1, y1, x2, y2)
            confidence: Уверенность детекции (0-1)
            class_id: Идентификатор класса объекта
            frame_id: Идентификатор кадра
        """
        self.box = box
        self.confidence = confidence
        self.class_id = class_id
        self.frame_id = frame_id

        # Вычисляем центр объекта
        self.center = (
            (box[0] + box[2]) // 2,
            (box[1] + box[3]) // 2,
        )

        # Вычисляем площадь объекта
        self.area = (box[2] - box[0]) * (box[3] - box[1])

    def __str__(self) -> str:
        """Строковое представление детекции."""
        return f"Detection(box={self.box}, confidence={self.confidence:.2f}, class_id={self.class_id})"

    def draw(
        self,
        frame: np.ndarray,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
        show_confidence: bool = True,
    ) -> np.ndarray:
        """
        Отрисовка детекции на кадре.

        Args:
            frame: Кадр для отрисовки
            color: Цвет рамки в формате BGR
            thickness: Толщина линии
            show_confidence: Показывать ли уверенность

        Returns:
            Кадр с отрисованной детекцией
        """
        # Копируем кадр
        result = frame.copy()

        # Рисуем ограничивающую рамку
        cv2.rectangle(
            result,
            (self.box[0], self.box[1]),
            (self.box[2], self.box[3]),
            color,
            thickness,
        )

        # Рисуем центр объекта
        cv2.circle(result, self.center, 3, color, -1)

        # Добавляем метку с уверенностью
        if show_confidence:
            label = f"Person: {self.confidence:.2f}"
            cv2.putText(
                result,
                label,
                (self.box[0], self.box[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )

        return result


class PersonDetector:
    """Класс для детекции людей на видео."""

    def __init__(self):
        """Инициализация детектора."""
        self.confidence_threshold = config.get("detection.confidence", 0.5)
        self.classes = config.get("detection.classes", [0])  # 0 - человек в COCO
        self.model_path = config.get(
            "detection.model_path",
            "/home/abelyaev/Documents/CODE/Person_Zone/config/yolo11.pt",
        )

        try:
            # Импортируем библиотеку ultralytics
            from ultralytics import YOLO

            # Загружаем модель YOLO
            self.model = YOLO(self.model_path)
            self.model.conf = (
                self.confidence_threshold
            )  # Устанавливаем порог уверенности
            self.model.classes = self.classes  # Фильтруем только людей
            logger.info(f"Модель YOLO успешно загружена из {self.model_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели YOLO: {str(e)}")
            logger.info("Используем заглушку для детекции")
            self.model = None

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Детекция людей на кадре.

        Args:
            frame: Кадр для детекции

        Returns:
            Список объектов Detection
        """
        if self.model is None:
            return self._detect_stub(frame)

        try:
            # Выполняем инференс с помощью ultralytics
            results = self.model(frame, verbose=False)

            # Извлекаем результаты
            detections = []

            # Обрабатываем результаты для каждого кадра
            for result in results:
                # Получаем боксы
                boxes = result.boxes

                # Если есть обнаружения
                if len(boxes) > 0:
                    # Для каждого бокса создаем объект Detection
                    for box in boxes:
                        # Получаем координаты бокса в формате xyxy
                        xyxy = box.xyxy.cpu().numpy()[0]

                        # Получаем уверенность
                        conf = float(box.conf.cpu().numpy()[0])

                        # Получаем класс
                        cls = int(box.cls.cpu().numpy()[0])

                        # Проверяем класс и уверенность
                        if cls in self.classes and conf >= self.confidence_threshold:
                            # Создаем объект Detection
                            detection = Detection(
                                (
                                    int(xyxy[0]),
                                    int(xyxy[1]),
                                    int(xyxy[2]),
                                    int(xyxy[3]),
                                ),
                                conf,
                                cls,
                            )
                            detections.append(detection)

            return detections
        except Exception as e:
            logger.error(f"Ошибка при детекции: {str(e)}")
            return self._detect_stub(frame)

    def _detect_stub(self, frame: np.ndarray) -> List[Detection]:
        """
        Заглушка для детекции (используется при ошибках или отсутствии модели).

        Args:
            frame: Кадр для детекции

        Returns:
            Список объектов Detection
        """
        # Создаем несколько случайных детекций для демонстрации
        height, width = frame.shape[:2]
        detections = []

        # Генерируем случайное количество детекций (0-3)
        num_detections = np.random.randint(0, 4)

        for _ in range(num_detections):
            # Генерируем случайную ограничивающую рамку
            x1 = np.random.randint(0, width - 100)
            y1 = np.random.randint(0, height - 200)
            x2 = x1 + np.random.randint(50, 100)
            y2 = y1 + np.random.randint(100, 200)

            # Генерируем случайную уверенность
            confidence = np.random.uniform(self.confidence_threshold, 1.0)

            # Создаем объект Detection
            detection = Detection((x1, y1, x2, y2), confidence, 0)
            detections.append(detection)

        return detections
