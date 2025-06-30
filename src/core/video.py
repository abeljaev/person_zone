"""
Модуль для работы с видеопотоком.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Iterator, Union, List, Dict, Any
import time
from collections import deque

from src.utils.logger import logger
from src.utils.config import config


class VideoReader:
    """Класс для чтения видеопотока."""

    def __init__(self, source: Optional[str] = None):
        """
        Инициализация VideoReader.

        Args:
            source: Источник видео (путь к файлу или RTSP-поток)
        """
        self.source = source
        self.cap = None
        self.frame_count = 0
        self.fps = 0
        self.width = 0
        self.height = 0
        self.is_rtsp = False
        self.is_open = False
        self.buffer_size = config.get("video.buffer_size", 64)
        self.frame_buffer = deque(maxlen=self.buffer_size)
        self.current_frame_index = 0
        self.loop_video = config.get(
            "video.loop", True
        )  # Параметр для зацикливания видео
        self.target_fps = config.get(
            "video.target_fps", 0
        )  # Целевой FPS (0 - без ограничения)
        self.last_frame_time = 0  # Время последнего кадра для ограничения FPS

        # Проверяем, является ли источник RTSP-потоком
        if source and source.lower().startswith("rtsp://"):
            self.is_rtsp = True
            # Настраиваем OpenCV для работы с RTSP через TCP
            import os

            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;tcp|stimeout;30000000"
            )
            logger.info("Настроен RTSP транспорт через TCP с увеличенным таймаутом")

        logger.info(f"Инициализация VideoReader с источником: {source}")
        if self.target_fps > 0:
            logger.info(f"Установлено жесткое ограничение FPS: {self.target_fps}")

    def open(self) -> bool:
        """
        Открытие видеопотока.

        Returns:
            True, если поток успешно открыт, иначе False
        """
        if self.source is None:
            logger.error("Не указан источник видео")
            return False

        try:
            # Для RTSP используем FFmpeg backend
            if self.is_rtsp:
                self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            else:
                self.cap = cv2.VideoCapture(self.source)

            if not self.cap.isOpened():
                logger.error(f"Не удалось открыть видеопоток: {self.source}")
                return False

            # Получаем информацию о видеопотоке
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # is_rtsp уже определен в __init__

            # Если это файл и количество кадров неизвестно, пытаемся определить
            if not self.is_rtsp and self.frame_count <= 0:
                logger.warning(
                    "Не удалось определить количество кадров, попытка подсчета..."
                )
                self.frame_count = self._count_frames()

            self.is_open = True
            self.current_frame_index = 0
            self.last_frame_time = (
                time.time()
            )  # Инициализируем время сразу при открытии

            # Если задан целевой FPS, принудительно устанавливаем его
            if self.target_fps > 0:
                logger.info(f"Принудительное ограничение FPS до {self.target_fps}")
                # Устанавливаем свойство CAP_PROP_FPS, если это поддерживается
                self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

            logger.info(
                f"Видеопоток открыт. Размер: {self.width}x{self.height}, "
                f"FPS: {self.fps}, Всего кадров: {self.frame_count}, "
                f"Целевой FPS: {self.target_fps if self.target_fps > 0 else 'не ограничен'}"
            )

            return True
        except Exception as e:
            logger.error(f"Ошибка при открытии видеопотока: {str(e)}")
            return False

    def read_frame(self) -> Tuple[bool, np.ndarray]:
        """
        Чтение следующего кадра из видеопотока.

        Returns:
            Кортеж (успех, кадр)
        """
        if not self.is_open or self.cap is None:
            logger.error("Видеопоток не открыт")
            return False, np.zeros((480, 640, 3), dtype=np.uint8)

        # Жесткое ограничение FPS
        if self.target_fps > 0:
            current_time = time.time()
            frame_interval = 1.0 / self.target_fps
            elapsed = current_time - self.last_frame_time

            # Если прошло меньше времени, чем нужно для соблюдения FPS, ждем
            if elapsed < frame_interval:
                sleep_time = frame_interval - elapsed
                time.sleep(sleep_time)
                # Логируем информацию о задержке (раз в 100 кадров)
                if self.current_frame_index % 100 == 0:
                    logger.debug(f"Задержка для соблюдения FPS: {sleep_time:.4f} с")

            self.last_frame_time = time.time()  # Обновляем время после сна

        try:
            ret, frame = self.cap.read()

            # Если достигнут конец видео и включено зацикливание
            if (
                not ret
                and self.loop_video
                and not self.is_rtsp
                and self.frame_count > 0
            ):
                logger.info("Достигнут конец видео, перезапуск с начала")
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                self.current_frame_index = 0

            if ret:
                # Изменяем размер кадра, если указаны параметры
                resize_width = config.get("video.resize_width", 0)
                resize_height = config.get("video.resize_height", 0)

                if resize_width > 0 and resize_height > 0:
                    frame = cv2.resize(frame, (resize_width, resize_height))

                # Добавляем кадр в буфер
                self.frame_buffer.append(frame.copy())

                # Увеличиваем счетчик кадров
                self.current_frame_index += 1

                return True, frame
            else:
                logger.debug("Не удалось прочитать кадр")
                return False, np.zeros((480, 640, 3), dtype=np.uint8)
        except Exception as e:
            logger.error(f"Ошибка при чтении кадра: {str(e)}")
            return False, np.zeros((480, 640, 3), dtype=np.uint8)

    def get_frame_at_position(self, position_seconds: float) -> Tuple[bool, np.ndarray]:
        """
        Получение кадра на указанной позиции в секундах.

        Args:
            position_seconds: Позиция в секундах

        Returns:
            Кортеж (успех, кадр)
        """
        if not self.is_open or self.cap is None:
            logger.error("Видеопоток не открыт")
            return False, np.zeros((480, 640, 3), dtype=np.uint8)

        if self.is_rtsp:
            logger.warning("Невозможно перемотать RTSP-поток")
            return False, np.zeros((480, 640, 3), dtype=np.uint8)

        try:
            # Вычисляем номер кадра
            frame_number = int(position_seconds * self.fps)

            # Устанавливаем позицию
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

            # Читаем кадр
            ret, frame = self.cap.read()

            if ret:
                return True, frame
            else:
                logger.error(
                    f"Не удалось получить кадр на позиции {position_seconds} с"
                )
                return False, np.zeros((480, 640, 3), dtype=np.uint8)
        except Exception as e:
            logger.error(f"Ошибка при получении кадра на позиции: {str(e)}")
            return False, np.zeros((480, 640, 3), dtype=np.uint8)

    def get_frame_by_index(self, frame_index: int) -> Tuple[bool, np.ndarray]:
        """
        Получение кадра по индексу.

        Args:
            frame_index: Индекс кадра

        Returns:
            Кортеж (успех, кадр)
        """
        if not self.is_open or self.cap is None:
            logger.error("Видеопоток не открыт")
            return False, np.zeros((480, 640, 3), dtype=np.uint8)

        if self.is_rtsp:
            logger.warning("Невозможно перемотать RTSP-поток")
            return False, np.zeros((480, 640, 3), dtype=np.uint8)

        try:
            # Устанавливаем позицию
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

            # Читаем кадр
            ret, frame = self.cap.read()

            if ret:
                return True, frame
            else:
                logger.error(f"Не удалось получить кадр с индексом {frame_index}")
                return False, np.zeros((480, 640, 3), dtype=np.uint8)
        except Exception as e:
            logger.error(f"Ошибка при получении кадра по индексу: {str(e)}")
            return False, np.zeros((480, 640, 3), dtype=np.uint8)

    def get_buffered_frame(self, offset: int = 0) -> Tuple[bool, np.ndarray]:
        """
        Получение кадра из буфера с указанным смещением от текущего.

        Args:
            offset: Смещение от текущего кадра (-1 для предыдущего, -2 для пред-предыдущего и т.д.)

        Returns:
            Кортеж (успех, кадр)
        """
        if not self.frame_buffer:
            return False, np.zeros((480, 640, 3), dtype=np.uint8)

        try:
            # Вычисляем индекс в буфере
            buffer_index = len(self.frame_buffer) + offset if offset < 0 else offset

            # Проверяем границы
            if 0 <= buffer_index < len(self.frame_buffer):
                return True, self.frame_buffer[buffer_index].copy()
            else:
                logger.error(f"Индекс {buffer_index} выходит за границы буфера")
                return False, np.zeros((480, 640, 3), dtype=np.uint8)
        except Exception as e:
            logger.error(f"Ошибка при получении кадра из буфера: {str(e)}")
            return False, np.zeros((480, 640, 3), dtype=np.uint8)

    def close(self) -> None:
        """Закрытие видеопотока."""
        if self.cap is not None:
            self.cap.release()
            self.is_open = False
            self.frame_buffer.clear()
            logger.info("Видеопоток закрыт")

    def _count_frames(self) -> int:
        """
        Подсчет количества кадров в видео.

        Returns:
            Количество кадров
        """
        if not self.is_open or self.cap is None:
            return 0

        try:
            # Сохраняем текущую позицию
            current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

            # Переходим в конец видео
            self.cap.set(cv2.CAP_PROP_POS_AVI_RATIO, 1)

            # Получаем номер последнего кадра
            frame_count = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

            # Возвращаемся на исходную позицию
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

            return frame_count
        except Exception as e:
            logger.error(f"Ошибка при подсчете кадров: {str(e)}")
            return 0

    def get_video_info(self) -> Dict[str, Any]:
        """
        Получение информации о видео.

        Returns:
            Словарь с информацией о видео
        """
        return {
            "source": self.source,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "is_rtsp": self.is_rtsp,
            "is_open": self.is_open,
            "current_frame": self.current_frame_index,
            "buffer_size": self.buffer_size,
            "loop_video": self.loop_video,
            "target_fps": self.target_fps,
        }


def get_video_info(source: str) -> dict:
    """
    Получение информации о видеофайле.

    Args:
        source: Путь к видеофайлу

    Returns:
        Словарь с информацией о видео (ширина, высота, fps, количество кадров)
    """
    try:
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error(f"Не удалось открыть видео: {source}")
            return {}

        info = {
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        }

        cap.release()
        return info
    except Exception as e:
        logger.error(f"Ошибка при получении информации о видео: {str(e)}")
        return {}
