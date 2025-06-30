"""
Модуль для работы с конфигурацией проекта.
"""

from pathlib import Path
import yaml
import json
from typing import Dict, Any, Optional, Union


class Config:
    """Класс для работы с конфигурацией проекта."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Инициализация конфигурации.

        Args:
            config_path: Путь к файлу конфигурации. Если None, используется стандартный путь.
        """
        self.config_dir = Path("config")
        self.config_path = (
            Path(config_path) if config_path else self.config_dir / "config.yaml"
        )
        self.config: Dict[str, Any] = {}

        # Создаем директорию конфигурации, если она не существует
        self.config_dir.mkdir(exist_ok=True)

        # Загружаем конфигурацию, если файл существует
        if self.config_path.exists():
            self.load()
        else:
            # Создаем базовую конфигурацию
            self.config = {
                "video": {
                    "source": str(Path("test_video/video.mp4").absolute()),
                    "width": 640,
                    "height": 480,
                    "fps": 30,
                },
                "detection": {
                    "model": "yolov11m",
                    "confidence": 0.5,
                    "classes": [0],  # 0 - человек в COCO
                },
                "zones": {"file": "config/zones.json"},
                "api": {
                    "base_url": "https://192.168.10.89",
                    "username": "admin",
                    "password": "admin",
                    "timeout": 10,
                    "timer_duration": 20,  # секунды
                },
            }
            self.save()

    def load(self) -> None:
        """Загрузка конфигурации из файла."""
        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f)

    def save(self) -> None:
        """Сохранение конфигурации в файл."""
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Получение значения из конфигурации.

        Args:
            key: Ключ в формате "section.key"
            default: Значение по умолчанию, если ключ не найден

        Returns:
            Значение из конфигурации
        """
        parts = key.split(".")
        value = self.config

        for part in parts:
            if part in value:
                value = value[part]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Установка значения в конфигурацию.

        Args:
            key: Ключ в формате "section.key"
            value: Значение для установки
        """
        parts = key.split(".")
        config = self.config

        # Навигация по вложенным словарям
        for i, part in enumerate(parts[:-1]):
            if part not in config:
                config[part] = {}
            config = config[part]

        # Установка значения
        config[parts[-1]] = value

        # Сохраняем изменения
        self.save()

    def load_zones(self) -> Dict[str, Any]:
        """
        Загрузка зон из JSON файла.

        Returns:
            Словарь с зонами
        """
        zones_file = Path(self.get("zones.file", "config/zones.json"))

        if not zones_file.exists():
            # Если файл не существует, создаем пустой
            zones_data = {"zones": []}
            with open(zones_file, "w") as f:
                json.dump(zones_data, f, indent=4)
            return zones_data

        with open(zones_file, "r") as f:
            return json.load(f)

    def save_zones(self, zones_data: Dict[str, Any]) -> None:
        """
        Сохранение зон в JSON файл.

        Args:
            zones_data: Словарь с зонами для сохранения
        """
        zones_file = Path(self.get("zones.file", "config/zones.json"))

        with open(zones_file, "w") as f:
            json.dump(zones_data, f, indent=4)


# Глобальный экземпляр конфигурации
config = Config()
