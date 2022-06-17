import logging
import os
import sys
from argparse import ArgumentParser
from logging import StreamHandler

import unicodedata2
import mutagen
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from mutagen.easyid3 import EasyID3
from mutagen.id3._util import ID3NoHeaderError
from yandex_music import Client, Track
from telegram_handler import TelegramHandler

LAST_FILE_NAME = 'last.txt'
SCHEDULER_INTERVAL_SECONDS = 60 * 30  # Отправка каждые 30 минут
MAX_FILE_SIZE = 10*1024*1024

logger = logging.getLogger(__name__)

handler = StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.setLevel(logging.DEBUG)
logger.info('Запуск YAM LikedTg')

parser = ArgumentParser()

parser.add_argument("-b", "--bot", dest="bot", required=True,
                    help="Telegram bot token", metavar="BOT")
parser.add_argument("-c", "--chat", dest="chat",
                    help="Telegram chat id", metavar="CHAT")
parser.add_argument("-g", "--group", dest="group",
                    help="Telegram group id", metavar="GROUP")
parser.add_argument("-y", "--yam", dest="yam",
                    help="Yandex Music token", metavar="YAM")

parser.add_argument("-q", "--quiet",
                    action="store_false", dest="verbose", default=True,
                    help="don't print status messages to stdout")

DELIMITER = "/"


# Транслитирация русских названий
def slugify(value):
    symbols = (u"абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ",
               u"abvgdeejzijklmnoprstufhzcss_y_euaABVGDEEJZIJKLMNOPRSTUFHZCSS_Y_EUA")

    tr = {ord(a): ord(b) for a, b in zip(*symbols)}

    value = value.translate(tr)  # looks good

    value = unicodedata2.normalize('NFKD', value).encode('ascii', 'ignore').decode('utf-8').strip()
    return value


def set_mp3_tags(track_file_name: str, track: Track):
    try:
        meta = EasyID3(track_file_name)
    except ID3NoHeaderError:
        meta = mutagen.File(track_file_name, easy=True)
        meta.add_tags()

    meta['title'] = track.title
    meta['artist'] = DELIMITER.join(i['name'] for i in track.artists)
    album = track.albums[0] if len(track.albums) > 0 else None
    meta['genre'] = album.genre if album is not None and album.genre is not None else ""
    meta.save()


def normalize_file_name(file_name):
    file_name = slugify(file_name)
    bad_symbols = u"/\\\'?*|:!"
    symbols = (bad_symbols, "_" * len(bad_symbols))

    tr = {ord(a): ord(b) for a, b in zip(*symbols)}

    file_name = file_name.translate(tr)
    return file_name[:120]


def main(arguments):
    args = parser.parse_args(arguments)

    token_tg = args.bot
    token_yam = args.yam
    chat_id_tg = args.chat
    group_id_tg = args.group

    bot = Bot(token=token_tg, parse_mode=types.ParseMode.HTML)
    dp = Dispatcher(bot)

    telegram_handler = TelegramHandler(token=token_tg, chat_id=chat_id_tg, level=logging.ERROR)
    telegram_handler.setFormatter(formatter)
    logger.addHandler(telegram_handler)

    async def bot_online(_):
        logger.error('Бот запущен')

    async def check_and_send_last_track():
        if chat_id_tg == '':
            logger.error("Chat ID не заполнен!")
            return
        if group_id_tg == '':
            logger.error("Group ID не заполнен!")
            return
        if token_yam == '':
            logger.error("YandexMusic Token не заполнен")
            return

        # await bot.send_message(chat_id_tg, 'Ушёл проверять последний лайкнутый трек') # Создано для отправки в лс
        logger.info('Проверка лайкнутого трека')
        try:
            with open(LAST_FILE_NAME, 'r',
                      encoding='utf-8') as last_state_open:  # Открываем файл с последний лайкнутым треком
                last_state = last_state_open.read()  # Читаем последний лайкнутый трек
        except Exception as e:
            logger.error(f'Не открыли файл с состоянием: {e}')
            last_state = ""  # Нет файла - первый запуск

        client = Client(token_yam).init()  # Инициализирцем токен
        likes = client.users_likes_tracks()
        index_last_track = 0  # вобще нужно найти какой последний посланный

        track = None
        # ищем последний отправленый трек
        for index_last_track, track in enumerate(likes.tracks):
            if track.id == last_state:
                index_last_track -= 1  # следующий
                break

        # ищем последний отправленый трек
        while index_last_track >= 0:
            track = likes[index_last_track].fetch_track()
            if track.available:
                break
            index_last_track -= 1

        if index_last_track < 0 or (not track.available):
            logger.warning("Доступных треков больше нет")
            return

        artists = track.artists_name()
        artist = artists[0] if len(artists) > 0 else ""  # Получаем артиста
        title = track.title  # Получаем название трека
        album = track.albums[0] if len(track.albums) > 0 else None
        if album is not None:
            genre = album.genre
            url = f'https://music.yandex.ru/album/{album.id}/track/{track.id}'  # Подставялем URL
        else:
            genre = None
            url = ""
        # await bot.send_message(chat_id_tg, 'Последний лайк: {artist} - {title}') # Создано для отправки в лс
        send_file = normalize_file_name(f'{artist} - {title}') + '.mp3'  # Отправляемый файл в формате mp3
        track.download(send_file)  # Качаем трек
        size_file = os.path.getsize(send_file)
        logger.info(f'Скачали: {send_file}, размер: {size_file}')
        set_mp3_tags(send_file, track)
        try:
            if size_file < MAX_FILE_SIZE:
                await bot.send_audio(group_id_tg, open(send_file, 'rb'),
                                     caption=f'🎧 {artist} - {title}\n**🎧 Жанр:** #{genre}\n\n[🎧 Я.Музыка]({url})',
                                     parse_mode='markdown')
                logger.info(f'Отправлен: {send_file}')
            else:
                logger.error(f'Трек {artist} - {title} размер {size_file}. Не шлём.')
            try:
                with open(LAST_FILE_NAME, 'w',
                          encoding='utf-8') as last_track:  # Открываем файл, чтобы записать инфу
                    last_track.write(track.id)  # Записываем последний отправленный трек
            except Exception as e:
                logger.error(f'Ошибка записи в файл {LAST_FILE_NAME}: {e}')
        finally:
            os.remove(send_file)  # Удаляем за собой файл
            # await bot.send_message(chat_id_tg, f'Удёлан: {send_file}') # Создано для отправки в лс
            logger.info(f'Удалён: {send_file}')

    @dp.message_handler(commands=['get'])
    async def send_file_command(message: types.Message):
        logger.debug("message %s", message)
        await do_shedule()

    async def do_shedule():
        try:
            await check_and_send_last_track()
        except Exception as e:
            logger.exception(f'Ошибка проверки и отправки очередного файла: {e}')

    scheduler = AsyncIOScheduler()
    scheduler.add_job(do_shedule, 'interval', seconds=SCHEDULER_INTERVAL_SECONDS)
    scheduler.start()

    logger.info('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        executor.start_polling(dp, skip_updates=True, on_startup=bot_online)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()


if __name__ == '__main__':
    argv = sys.argv[1:]

    if not len(argv):
        parser.print_help()
        sys.exit(1)

    main(argv)
