# YAM LikedTg

Скрипт для скачивания всех доступных треков с поставленными лайками из Yandex.Music в Telegram.

Скрипт потроен на основе [aiogram](https://github.com/aiogram/aiogram "aiogram") + [Yandex Music Api](https://github.com/MarshalX/yandex-music-api "Yandex Music Api") (Не официальная)

Скрипт проверяет список "Мне нравится" в Яндекс Музыке, скачивает локально, добавляет описание в mp3 файл (Исполнитель, название, обложка), отправляет в Telegream канал и удаляет за собой файл с жёсткого диска.

Проверка выполняется каждые 30 минут. Промежуток времени задаётся в:
```python
SHEDULE_INTERVAL_SECONDS = 60 * 30  # Отправка каждые 30 минут
```
### Где взять токен Яндекс Музыки?
Яндекс отдаёт токен от всего что угодно, кроме Яндекс Музыки. Получить его в настоящий момент можно благодаря автору [Yandex Music API](https://github.com/MarshalX/yandex-music-api "Yandex Music API"). 
Делать это на свой страх и риск.


### Перед запуском:
```bash
pip install -r requirements.txt
```

#### Использование: 
```bash
app.py [-h] -b BOT [-c CHAT] [-g GROUP] [-y YAM] [-q]
```


#### Опции запуска:

```bash
  -h, --help            show this help message and exit
  -b BOT, --bot BOT     telegram bot token
  -c CHAT, --chat CHAT  telegram chat id
  -g GROUP, --group GROUP telegram group id
  -y YAM, --yam YAM     Yandex Music token
  -q, --quiet           do not print status messages to stdout
```
Огромная благодраность за помощь [Alexey Ponomarev](https://github.com/real-mielofon "Alexey Ponomarev")

Пример работы: [Чо послушать 🎧](https://t.me/music4o "Чо послушать 🎧")