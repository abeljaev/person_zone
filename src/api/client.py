from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from queue import Empty, Queue
from threading import Thread
from typing import Dict, Optional, Any

import requests
import urllib3

from src.utils.config import config
from src.utils.logger import logger

# Отключаем предупреждения о self-signed SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ApiClient:
    """Клиент, инкапсулирующий взаимодействие с внешним API."""

    def __init__(self) -> None:
        """Инициализирует клиент и запускает фоновый поток-обработчик."""
        self._base_url: str = config.get("api.base_url", "https://31.148.204.230")
        self._base_url_with_port: str = f"{self._base_url}:8443"
        self._username: str = config.get("api.username", "admin")
        self._password: str = config.get("api.password", "admin")
        self._audio_file: str = config.get("api.audio_file", "1.wav")
        self._timeout: float = config.get("api.timeout", 10.0)
        self._retry_count: int = config.get("api.retry_count", 3)
        self._retry_delay: float = config.get("api.retry_delay", 1.0)
        self._timer_duration: float = config.get("api.timer_duration", 20.0)
        self._debug_mode: bool = config.get("debug.debug_mode", True)

        self._zone_end_times: Dict[str, float] = {}
        self._jwt_token: Optional[str] = None
        self._lock = threading.Lock()

        # Очередь задач для фонового обработчика
        self._task_queue: Queue[Optional[tuple[str, Any]]] = Queue()
        self._worker_thread = Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

        api_mode = "эмуляция" if self._debug_mode else "реальная API"
        logger.info("Инициализация ApiClient: %s (%s)", self._base_url, api_mode)

    def send_zone_entry_request(self, zone_name: str, person_id: int) -> bool:
        """Помещает задачу на выполнение API-последовательности в очередь."""
        with self._lock:
            # Если зона уже заблокирована, игнорируем запрос
            if (
                zone_name in self._zone_end_times
                and time.time() < self._zone_end_times[zone_name]
            ):
                remaining = self._zone_end_times[zone_name] - time.time()
                logger.debug(
                    "Зона %s уже заблокирована, осталось %.1f с", zone_name, remaining
                )
                return False

            logger.info(
                "Человек %s вошёл в зону %s — ставим задачу в очередь",
                person_id,
                zone_name,
            )
            # блокируем зону, чтобы избежать дублирования задач
            self._zone_end_times[zone_name] = time.time() + self._timer_duration

        self._task_queue.put(("run_sequence", zone_name))
        return True

    def get_zone_timer_remaining(self, zone_name: str) -> float:
        """Возвращает, сколько секунд осталось до разблокировки зоны."""
        with self._lock:
            end_time = self._zone_end_times.get(zone_name)
            if end_time is None:
                return 0.0
            remaining = end_time - time.time()
            return max(0.0, remaining)

    def _start_zone_timer(self, zone_name: str) -> None:
        """Запускает таймер блокировки для зоны (для заглушки)."""
        with self._lock:
            self._zone_end_times[zone_name] = time.time() + self._timer_duration
            logger.debug(
                f"Таймер для зоны {zone_name} запущен на {self._timer_duration}s"
            )

    def reset(self) -> None:
        """Сбрасывает состояние клиента при завершении работы."""
        logger.info("Остановка ApiClient...")
        self._task_queue.put(None)  # Сигнал для завершения потока
        with self._lock:
            self._zone_end_times.clear()
            self._jwt_token = None
        self._worker_thread.join(timeout=2.0)
        logger.info("Состояние ApiClient сброшено")

    def _worker(self) -> None:
        """Главный цикл рабочего потока, обрабатывающий задачи из очереди."""
        while True:
            try:
                task = self._task_queue.get(timeout=1.0)
                if task is None:
                    break
                command, payload = task
                if command == "run_sequence":
                    self._run_sequence(payload)
            except Empty:
                continue  # Просто продолжаем ждать задачи
        logger.info("Поток ApiClient-worker завершил работу.")

    def _run_sequence(self, zone_name: str) -> None:
        """Выполняет последовательность запросов: login -> play_audio."""
        token = self._get_jwt_token()
        if token is None:
            logger.error("Не удалось получить JWT-токен, последовательность прервана")
            # Разблокируем зону, так как запрос не удался
            with self._lock:
                self._zone_end_times.pop(zone_name, None)
            return

        success = self._play_audio(token)
        if success:
            logger.info("API-последовательность для зоны %s завершена", zone_name)
        else:
            logger.error(
                "API-последовательность для зоны %s завершилась с ошибкой", zone_name
            )
            # Разблокируем зону, так как запрос не удался
            with self._lock:
                self._zone_end_times.pop(zone_name, None)

    def _get_jwt_token(self) -> Optional[str]:
        if self._debug_mode:
            self._jwt_token = "debug_token"
            return self._jwt_token
        if self._jwt_token is not None:
            return self._jwt_token
        login_url = f"{self._base_url}/login"
        auth_data = {"username": self._username, "password": self._password}
        logger.info("POST %s", login_url)
        response = self._make_request("POST", login_url, json=auth_data)
        if response is None or response.status_code != 200:
            logger.error(
                "Ошибка аутентификации: %s",
                response.status_code if response else "no response",
            )
            return None
        try:
            self._jwt_token = response.json().get("token")
        except Exception as exc:
            logger.exception("Ошибка парсинга JSON: %s", exc)
            return None
        return self._jwt_token

    def _play_audio(self, token: str) -> bool:
        if self._debug_mode:
            logger.info("[DEBUG] Эмуляция воспроизведения аудио")
            time.sleep(0.2)
            return True
        play_url = f"{self._base_url_with_port}/play/{self._audio_file}/1"
        headers = {"Authorization": f"Bearer {token}"}
        logger.info("GET %s", play_url)
        response = self._make_request("GET", play_url, headers=headers)
        if response is None or response.status_code != 200:
            logger.error(
                "Ошибка аудио-запроса: %s",
                response.status_code if response else "no response",
            )
            return False
        return True

    def _make_request(
        self, method: str, url: str, **kwargs: Any
    ) -> Optional[requests.Response]:
        kwargs.setdefault("verify", False)
        kwargs.setdefault("timeout", self._timeout)
        for attempt in range(1, self._retry_count + 1):
            try:
                response = requests.request(method, url, **kwargs)
                return response
            except requests.RequestException as exc:
                logger.warning(
                    "%s попытка %s/%s не удалась: %s",
                    method,
                    attempt,
                    self._retry_count,
                    exc,
                )
                if attempt < self._retry_count:
                    time.sleep(self._retry_delay)
        return None
