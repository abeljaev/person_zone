import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://31.148.204.230:8443"
USERNAME = "admin"
PASSWORD = "admin"
AUDIO_FILE = "1.wav"


def main():
    print("Получаем токен")
    try:
        login_url = f"{BASE_URL}/login"
        login_data = {"username": USERNAME, "password": PASSWORD}

        response = requests.post(login_url, json=login_data, verify=False, timeout=10)

        if response.status_code == 200:
            token = response.json().get("token")
            print(f"Токен получен: {token[:50]}...")
        else:
            print(f"Ошибка получения токена: {response.status_code}")
            return 1

    except Exception as e:
        print(f"Ошибка запроса токена: {e}")
        return 1

    print("Воспроизводим аудио")
    try:
        audio_url = f"{BASE_URL}/play/{AUDIO_FILE}/1"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(audio_url, headers=headers, verify=False, timeout=10)

        if response.status_code == 200:
            print("Аудио успешно воспроизведено")
            return 0
        else:
            print(f"Ошибка воспроизведения: {response.status_code}")
            if response.text:
                print(f"Ответ: {response.text}")
            return 1

    except Exception as e:
        print(f"Ошибка запроса аудио: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
