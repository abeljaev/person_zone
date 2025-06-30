1. Клонируем репозиторий:
```bash
git clone git@github.com:abeljaev/person_zone.git
cd person_zone
```

2. Создайте виртуальное окружение и установите зависимости:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## Использование

### Запуск системы

```bash
python scripts/run_person_zone.py --video "rtsp://cam:asd123123@31.148.204.230:9554/cam/realmonitor?channel=1&subtype=0" --zones config/zones_rtsp.json
```
