#!/usr/bin/env python3
"""
Быстрый тест API.
"""

import sys
from pathlib import Path
import importlib


sys.path.append(str(Path(__file__).parent.parent))


try:
    import src.utils.config

    importlib.reload(src.utils.config)
    print("Конфигурация перезагружена")
except Exception as e:
    print(f"Ошибка перезагрузки: {e}")

from src.api.client import ApiClient


def main():
    print("Быстрый тест API...")

    client = ApiClient()
    print(f"Base URL: {client.base_url}")
    print(f"Username: {client.username}")
    print(f"Audio file: {client.audio_file}")

    print("\nТестируем аутентификацию...")
    auth_result = client._authenticate()
    print(f"Результат: {auth_result}")

    if auth_result and client.jwt_token:
        print(f"Токен получен: {client.jwt_token[:50]}...")

        print("\nТестируем воспроизведение аудио...")
        audio_result = client.play_audio()
        print(f"Результат воспроизведения: {audio_result}")

        if audio_result:
            print("Все работает!")

            print("\nТестируем обработку входа в зону...")
            zone_result = client.send_zone_entry_request("test_zone", 42)
            print(f"Результат обработки зоны: {zone_result}")

        return 0 if audio_result else 1
    else:
        print("Аутентификация не удалась")
        return 1


if __name__ == "__main__":
    exit(main())
