from __future__ import annotations

"""
Основной модуль для работы с системой детекции и трекинга людей в зонах.
"""

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Dict, Set, Tuple, Optional

import cv2
import numpy as np
from ultralytics import YOLO

from src.api.client import ApiClient
from src.core.video import VideoReader
from src.core.zone import ZoneManager
from src.utils.config import config
from src.utils.logger import logger


@dataclass
class Track:
    """Класс для хранения данных об отслеживаемом объекте."""

    track_id: int
    box: Tuple[int, int, int, int]
    bottom_point: Tuple[int, int]
    color: Tuple[int, int, int]

    def draw(self, frame: np.ndarray) -> np.ndarray:
        """Отрисовка трека на кадре."""
        x1, y1, x2, y2 = self.box
        cv2.rectangle(frame, (x1, y1), (x2, y2), self.color, 2)
        cv2.circle(frame, self.bottom_point, 5, (0, 0, 255), -1)
        label = f"ID: {self.track_id}"
        cv2.putText(
            frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color, 2
        )
        return frame


class PersonZoneSystem:
    """Основной класс для работы с системой детекции и трекинга людей в зонах."""

    def __init__(
        self,
        video_source: Optional[str] = None,
        zones_file: Optional[str] = None,
    ):
        self.video_reader = VideoReader(source=video_source)
        self.zone_manager = ZoneManager(zones_file=zones_file)
        self.api_client = ApiClient()

        model_path = config.get("detection.model_path", "config/yolo11m.pt")
        try:
            self.model = YOLO(model_path)
            logger.info(f"Модель YOLO загружена из {model_path}")
        except Exception as e:
            logger.warning(f"Не удалось загрузить модель {model_path}: {e}")
            logger.info("Попытка загрузки совместимой модели yolov8m.pt...")
            try:
                self.model = YOLO("yolov8m.pt")  # Автоматически скачается
                logger.info("Загружена совместимая модель yolov8m.pt")
            except Exception as e2:
                logger.error(f"Не удалось загрузить ни одну модель: {e2}")
                raise

        self.bottom_point_offset = config.get("detection.bottom_point_offset", 0.05)
        self.frame_window_size = config.get("detection.frame_window_size", 10)
        self.min_frames_in_zone = config.get("detection.min_frames_in_zone", 5)

        self.debug_mode = config.get("debug.debug_mode", True)

        self.frame_skip = config.get("detection.frame_skip", 2)
        self.resize_for_detection = config.get("detection.resize_for_detection", True)
        self.detection_size = config.get("detection.detection_size", 640)

        self.zone_history: Deque[bool] = deque(maxlen=self.frame_window_size)

        self.is_running = False
        self._video_resolution_set = False
        self.current_frame: Optional[np.ndarray] = None
        self.current_tracks: List[Track] = []
        self.fps: float = 0.0
        self.prev_frame_time: float = 0.0
        self.zone_status: Dict[str, bool] = {
            zone.name: False for zone in self.zone_manager.zones
        }
        self.frame_counter = 0

        self.fps_log_interval = config.get("debug.fps_log_interval", 100)
        self.processed_frames_count = 0
        self.fps_samples: Deque[float] = deque(maxlen=self.fps_log_interval)
        self.fps_log_start_time = 0.0

        mode_text = (
            "ДЕБАГ (эмуляция API + видео)"
            if self.debug_mode
            else "ПРОДАКШН (реальная API + headless)"
        )
        logger.info(f"Система PersonZoneSystem инициализирована в режиме: {mode_text}")
        logger.info(
            f"Логирование FPS каждые {self.fps_log_interval} обработанных кадров"
        )

    def start(self) -> None:
        if not self.video_reader.open():
            return
        self.is_running = True
        self.fps_log_start_time = time.time()
        logger.info("Система запущена")

        skip_counter = 0

        try:
            while self.is_running:
                ret, frame = self.video_reader.read_frame()
                if not ret:
                    break

                skip_counter += 1
                if skip_counter < self.frame_skip:
                    continue

                skip_counter = 0
                self.frame_counter += 1

                if not self._video_resolution_set:
                    self._set_video_resolution(frame)

                processed_frame = self.process_frame(frame)

                if self.debug_mode and config.get("debug.enable_keys", False):
                    self._show_debug_frame(processed_frame)
                    if cv2.waitKey(1) & 0xFF == 27:
                        break
        finally:
            self.stop()

    def stop(self) -> None:
        self.is_running = False
        self.video_reader.close()
        self.api_client.reset()

        if self.debug_mode:
            cv2.destroyAllWindows()

        if self.processed_frames_count > 0:
            total_time = time.time() - self.fps_log_start_time
            overall_avg_fps = (
                self.processed_frames_count / total_time if total_time > 0 else 0
            )
            logger.info(
                f"Система остановлена. Общая статистика: {self.processed_frames_count} кадров за {total_time:.1f}с, средний FPS: {overall_avg_fps:.1f}"
            )
        else:
            logger.info("Система остановлена")

    def _set_video_resolution(self, frame: np.ndarray) -> None:
        video_resolution = (frame.shape[1], frame.shape[0])
        self.zone_manager.set_target_resolution(video_resolution)
        self._video_resolution_set = True
        logger.info(f"Установлено разрешение видео для зон: {video_resolution}")

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        current_time = time.time()
        self.fps = (
            1 / (current_time - self.prev_frame_time) if self.prev_frame_time > 0 else 0
        )
        self.prev_frame_time = current_time

        self.processed_frames_count += 1

        if self.fps > 0 and len(self.fps_samples) < self.fps_log_interval:
            self.fps_samples.append(self.fps)

        if len(self.fps_samples) >= self.fps_log_interval:
            self._log_fps_statistics()

        original_height, original_width = frame.shape[:2]

        detection_frame, scale_factor = self._prepare_detection_frame(
            frame, original_width, original_height
        )

        results = self.model.track(
            source=detection_frame,
            persist=True,
            classes=[0],
            conf=config.get("detection.confidence", 0.7),
            verbose=False,
            tracker="bytetrack.yaml",
        )

        self._process_detection_results(results, scale_factor)

        self._check_zones()

        if self.debug_mode:
            return self._visualize_frame(frame)
        return frame

    def _prepare_detection_frame(
        self, frame: np.ndarray, width: int, height: int
    ) -> tuple[np.ndarray, float]:
        """Подготавливает кадр для детекции с оптимизацией размера."""
        if not self.resize_for_detection or max(width, height) <= self.detection_size:
            return frame, 1.0

        scale_factor = self.detection_size / max(width, height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        detection_frame = cv2.resize(frame, (new_width, new_height))

        return detection_frame, scale_factor

    def _process_detection_results(self, results, scale_factor: float) -> None:
        """Обрабатывает результаты детекции и создает треки."""
        self.current_tracks.clear()

        if results[0].boxes.id is None:
            return

        boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
        track_ids = results[0].boxes.id.cpu().numpy().astype(int)

        if scale_factor != 1.0:
            boxes = (boxes / scale_factor).astype(int)

        for box, track_id in zip(boxes, track_ids):
            x1, y1, x2, y2 = box
            bottom_y = int(y2 - (y2 - y1) * self.bottom_point_offset)
            self.current_tracks.append(
                Track(
                    track_id,
                    tuple(box),
                    ((x1 + x2) // 2, bottom_y),
                    colors(track_id, True),
                )
            )

    def _log_fps_statistics(self) -> None:
        """Логирует статистику FPS за последний период."""
        if not self.fps_samples:
            return

        current_time = time.time()
        period_duration = current_time - self.fps_log_start_time

        avg_fps = sum(self.fps_samples) / len(self.fps_samples)
        min_fps = min(self.fps_samples)
        max_fps = max(self.fps_samples)
        current_fps = self.fps_samples[-1] if self.fps_samples else 0

        sorted_samples = sorted(self.fps_samples)
        p25 = sorted_samples[len(sorted_samples) // 4] if sorted_samples else 0
        p75 = sorted_samples[3 * len(sorted_samples) // 4] if sorted_samples else 0

        logger.info(
            f"FPS за {self.fps_log_interval} кадров ({period_duration:.1f}с): "
            f"средний={avg_fps:.1f}, текущий={current_fps:.1f}, "
            f"мин={min_fps:.1f}, макс={max_fps:.1f}, "
            f"25%={p25:.1f}, 75%={p75:.1f}"
        )

        if avg_fps < 10:
            logger.warning(f"Низкая производительность: средний FPS {avg_fps:.1f} < 10")
        elif avg_fps < 15:
            logger.warning(
                f"Производительность ниже оптимальной: средний FPS {avg_fps:.1f} < 15"
            )

        self.fps_samples.clear()
        self.fps_log_start_time = current_time

    def _check_zones(self) -> None:
        """Проверяет наличие людей в зонах и принимает решение о вызове API."""
        person_in_any_zone = any(
            self.zone_manager.check_point(track.bottom_point)
            for track in self.current_tracks
        )

        self.zone_history.append(person_in_any_zone)

        for zone in self.zone_status:
            self.zone_status[zone] = False
        if person_in_any_zone:
            for track in self.current_tracks:
                for zone in self.zone_manager.check_point(track.bottom_point):
                    self.zone_status[zone.name] = True

        if sum(self.zone_history) >= self.min_frames_in_zone:

            active_zone_name = next(
                (name for name, status in self.zone_status.items() if status),
                "default_zone",
            )

            if self.debug_mode:
                logger.info(
                    f"[ЗАГЛУШКА] Условие выполнено ({sum(self.zone_history)}/{len(self.zone_history)} кадров), "
                    f"API запрос к зоне '{active_zone_name}' ИМИТИРОВАН (реальная отправка отключена)"
                )

                self.api_client._start_zone_timer(active_zone_name)
                self.zone_history.clear()
            else:
                success = self.api_client.send_zone_entry_request(
                    active_zone_name, person_id=-1
                )
                if success:
                    logger.info(
                        f"Условие выполнено ({sum(self.zone_history)}/{len(self.zone_history)} кадров), API вызван."
                    )
                    self.zone_history.clear()
                else:
                    logger.debug(
                        "Условие для вызова API выполнено, но вызов заблокирован таймером."
                    )

    def _visualize_frame(self, frame: np.ndarray) -> np.ndarray:
        """Визуализация результатов на кадре."""
        result = frame.copy()
        result = self.zone_manager.draw_zones(result)
        for track in self.current_tracks:
            result = track.draw(result)
        cv2.putText(
            result,
            f"FPS: {self.fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

        # Показываем текущий режим работы
        mode_text = "[DEBUG MODE]" if self.debug_mode else "[PRODUCTION MODE]"
        mode_color = (0, 255, 255) if self.debug_mode else (255, 255, 255)
        cv2.putText(
            result,
            mode_text,
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            mode_color,
            2,
        )

        # Визуализация счетчика кадров
        history_count = sum(self.zone_history)
        history_text = f"Frames in Zone: {history_count}/{self.frame_window_size}"
        history_color = (
            (0, 255, 0) if history_count >= self.min_frames_in_zone else (255, 255, 255)
        )
        cv2.putText(
            result,
            history_text,
            (10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            history_color,
            2,
        )

        y_offset = 120
        for zone_name, is_danger in self.zone_status.items():
            remaining_time = self.api_client.get_zone_timer_remaining(zone_name)
            is_zone_active = remaining_time > 0
            if is_danger:
                status, color = (
                    (f"DANGER - API BLOCKED ({remaining_time:.1f}s)", (0, 165, 255))
                    if is_zone_active
                    else ("DANGER - API READY", (0, 0, 255))
                )
            else:
                status, color = (
                    (f"SAFE - API BLOCKED ({remaining_time:.1f}s)", (0, 255, 255))
                    if is_zone_active
                    else ("SAFE - API READY", (0, 255, 0))
                )
            cv2.putText(
                result,
                f"Zone {zone_name}: {status}",
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )
            y_offset += 25

        return result

    def _show_debug_frame(self, frame: np.ndarray) -> None:
        if frame is not None:
            cv2.imshow("PersonZoneSystem", frame)


def colors(idx: int, bgr: bool = False) -> Tuple[int, int, int]:
    np.random.seed(idx)
    hsv = (np.random.randint(0, 180), 255, 255)
    color_bgr = cv2.cvtColor(np.array([[hsv]], dtype=np.uint8), cv2.COLOR_HSV2BGR)[0][0]
    return (
        tuple(map(int, color_bgr))
        if bgr
        else (int(color_bgr[2]), int(color_bgr[1]), int(color_bgr[0]))
    )
