import sys
import os
import time
import logging

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from yandex_music import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from logging import StreamHandler
from argparse import ArgumentParser

LAST_FILE_NAME = 'last.txt'
SHEDULE_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)

handler = StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

logger.setLevel(logging.DEBUG)
logger.info('Start YAM bot')

parser = ArgumentParser()

parser.add_argument("-b", "--bot", dest="bot", required=True,
                    help="telegram bot token", metavar="BOT")
parser.add_argument("-c", "--chat", dest="chat",
                    help="telegram chat id", metavar="CHAT")
parser.add_argument("-g", "--group", dest="group",
                    help="telegram group id", metavar="GROUP")
parser.add_argument("-y", "--yam", dest="yam",
                    help="Yandex Music token", metavar="YAM")

parser.add_argument("-q", "--quiet",
                    action="store_false", dest="verbose", default=True,
                    help="don't print status messages to stdout")

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
            logger.error("empty chat id")
            return
        if group_id_tg == '':
            logger.error("empty group id")
            return
        if token_yam == '':
            logger.error("empty yandexMusic token")
            return

        # await bot.send_message(chat_id_tg, 'Ушёл проверять последний лайкнутый трек')
        print('Проверка лайкнутого трека')

        try:
            with open(LAST_FILE_NAME, 'r', encoding='utf-8') as last_state_open:  # Открываем файл с последний лайкнутым треком
                last_state = last_state_open.read()  # Читаем последний лайкнутый трек
        except:
            last_state = ""  # Нет файла - первый запуск

        client = Client(token_yam).init()  # Инициализирцем токен
        artist = client.users_likes_tracks()[0].fetch_track().artists_name()[0]  # Получаем артиста
        track = client.users_likes_tracks()[0].fetch_track()['title']  # Получаем название трека
        url = f'https://music.yandex.ru/album/{client.users_likes_tracks()[0].album_id}/track/{client.users_likes_tracks()[0].id}'  # Подставялем URL
        print(f'Ласт лайкед: {artist} - {track}')
        send_file = f'{artist} - {track}.mp3'  # Отправляемый файл в формате mp3
        if send_file == last_state:
            print('Изменений нет')  # Последний лайкнутый не изменился. Ничего не отправляем
            await bot.send_message(chat_id_tg, 'изменений нет')
            # last_state.close
        else:
            client.users_likes_tracks()[0].fetch_track().download(f'{artist} - {track}.mp3')  # Качаем трек
            try:
                await bot.send_audio(group_id_tg, open(send_file, 'rb'),
                                 caption=f'🎧 {artist} - {track}\n<a href="{url}">🎧 Яндекс.Музыка</a>')
                try:
                    with open(LAST_FILE_NAME, 'w', encoding='utf-8') as last_track:  # Открываем файл, чтобы записать инфу
                        last_track.write(send_file)  # Записываем последний отправленный трек
                except:
                    logger.error("ошибка записи в файл {0}", LAST_FILE_NAME)
            finally:
                os.remove(send_file)  # Удаляем за собой файл

    @dp.message_handler(commands=['get'])
    async def send_file_command(message: types.Message):
        logger.debug("message %s", message)
        await check_and_send_lastTrack()

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
