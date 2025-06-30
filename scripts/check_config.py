#!/usr/bin/env python3
"""
Скрипт для проверки загрузки конфигурации.
"""

import sys
from pathlib import Path

# Добавляем путь к src для импорта модулей
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.config import config


def main():
    print("Проверяем загрузку конфигурации...")
    print(f"Путь к конфигурации: {config.config_path}")
    print(f"Файл существует: {config.config_path.exists()}")

    print("\nЗагруженная конфигурация:")

    api_config = config.get("api", {})
    print(f"  base_url: {api_config.get('base_url')}")
    print(f"  username: {api_config.get('username')}")
    print(f"  password: {api_config.get('password')}")
    print(f"  audio_file: {api_config.get('audio_file')}")
    print(f"  requests_on_entry: {api_config.get('requests_on_entry')}")
    print(f"  request_on_timer_end: {api_config.get('request_on_timer_end')}")
    print(f"  timeout: {api_config.get('timeout')}")
    print(f"  timer_duration: {api_config.get('timer_duration')}")

    print(f"\nПроверяем метод config.get():")
    print(f"  api.base_url: {config.get('api.base_url')}")
    print(f"  api.username: {config.get('api.username')}")
    print(f"  api.password: {config.get('api.password')}")
    print(f"  api.audio_file: {config.get('api.audio_file')}")

    return 0


if __name__ == "__main__":
    exit(main())
