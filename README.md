# YAM LikedTg

Скрипт для скачивания всех доступных треков с поставленными лайками из Yandex.Music в Telegram.
Скрипт потроен на основе [aiogram](https://github.com/aiogram/aiogram "aiogram") + [Yandex Music Api](https://github.com/MarshalX/yandex-music-api "Yandex Music Api") (Не официальная)


Перед запуском:
```bash
pip install -r requirements.txt
```

Использование: 
```bash
app.py [-h] -b BOT [-c CHAT] [-g GROUP] [-y YAM] [-q]
```


Опции:

```bash
  -h, --help            show this help message and exit
  -b BOT, --bot BOT     telegram bot token
  -c CHAT, --chat CHAT  telegram chat id
  -g GROUP, --group GROUP telegram group id
  -y YAM, --yam YAM     Yandex Music token
  -q, --quiet           do not print status messages to stdout
```
