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
from mutagen.id3 import TIT2
from yandex_music import Client, Track

LAST_FILE_NAME = 'last.txt'
SHEDULE_INTERVAL_SECONDS = 60 * 30 # Отправка каждые 30 минут

logger = logging.getLogger(__name__)

handler = StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

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
    except mutagen.id3.ID3NoHeaderError:
        meta = mutagen.File(track_file_name, easy=True)
        meta.add_tags()

    meta['title'] = track.title
    meta['artist'] = DELIMITER.join(i['name'] for i in track.artists)
    meta['genre'] = track.albums[0].genre if track.albums[0].genre is not None else ""
    meta.save()


def main(arguments):
    args = parser.parse_args(arguments)

    token_tg = args.bot
    token_yam = args.yam
    chat_id_tg = args.chat
    group_id_tg = args.group

    bot = Bot(token=token_tg, parse_mode=types.ParseMode.HTML)
    dp = Dispatcher(bot)

    async def bot_online(_):
        print('Я готов!')

    async def check_and_send_lastTrack():
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
        print('Проверка лайкнутого трека')
        try:
            with open(LAST_FILE_NAME, 'r',
                      encoding='utf-8') as last_state_open:  # Открываем файл с последний лайкнутым треком
                last_state = last_state_open.read()  # Читаем последний лайкнутый трек
        except:
            last_state = ""  # Нет файла - первый запуск

        client = Client(token_yam).init()  # Инициализирцем токен
        likes = client.users_likes_tracks()
        index_last_track = 0  # вобще нужно найти какой последний посланный
        for index_last_track, track in enumerate(likes.tracks):
            if track.id == last_state:
                index_last_track -= 1  # следующий
                break
        while index_last_track >= 0:
            track = likes[index_last_track].fetch_track()
            if track.available:
                break
            index_last_track -= 1

        if index_last_track < 0 or (not track.available):
            logger.error("Доступных треков больше нет")
            return

        artist = track.artists_name()[0]  # Получаем артиста
        title = track.title  # Получаем название трека
        album = track.albums[0]
        genre = album.genre
        url = f'https://music.yandex.ru/album/{album.id}/track/{track.id}'  # Подставялем URL
        print(f'Последний лайк: {artist} - {title}')
        # await bot.send_message(chat_id_tg, 'Последний лайк: {artist} - {title}') # Создано для отправки в лс
        send_file = f'{artist} - {title}.mp3' # Отправляемый файл в формате mp3
        send_file = send_file.replace('*', '_')
        #slugify(send_file).replace("/", "_").replace("\\", "_").replace("\'", "_")
        send_file = send_file.replace("\"", "_").replace("?", "_")
        send_file = send_file.replace(">", ")")
        send_file = send_file.replace("<", "(")
        send_file = send_file.replace("/", "_")
        send_file = send_file.replace("|", "_")
        send_file = send_file.replace(":", "_")
        send_file = send_file.replace("!", "_")
        send_file = send_file.replace("*", "_")
        if send_file == last_state:
            # await bot.send_message(chat_id_tg, 'Доступных треков больше нет') # Создано для отправки в лс
            print('Доступных треков больше нет')  # Последний лайкнутый не изменился. Ничего не отправляем
        else:           
            track.download(send_file)  # Качаем трек
            set_mp3_tags(send_file, track)
            try:
                await bot.send_audio(group_id_tg, open(send_file, 'rb'),
                                     caption=f'🎧 {artist} - {title}\n**🎧 Жанр:** #{genre}\n\n[🎧 Я.Музыка]({url})',parse_mode='markdown')
                print(f'Отправлен: {send_file}')
                try:
                    with open(LAST_FILE_NAME, 'w',
                              encoding='utf-8') as last_track:  # Открываем файл, чтобы записать инфу
                        last_track.write(track.id)  # Записываем последний отправленный трек
                except:
                    logger.error("Ошибка записи в файл {0}", LAST_FILE_NAME)
            finally:
                os.remove(send_file)  # Удаляем за собой файл
                # await bot.send_message(chat_id_tg, f'Удёлан: {send_file}') # Создано для отправки в лс
                print(f'Удалён: {send_file}')


    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_send_lastTrack, 'interval', seconds=SHEDULE_INTERVAL_SECONDS)
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