from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor
from telegraph import Telegraph
import logging

API_TOKEN = ''
TELEGRAPH_TOKEN = '793a75f549c0fcd42f82af1a617e9f1c952fefb58994b253012823d75d0c'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

telegraph = Telegraph(TELEGRAPH_TOKEN)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Привет\n1. Заголовок\n2. Внутренний текст")

@dp.message_handler(lambda message: '\n' in message.text)
async def create_telegraph_page(message: types.Message):
    try:
        title, content = message.text.split('\n', 1)
        response = telegraph.create_page(
            title=title,
            html_content=f'<p>{content}</p>'
        )
        page_url = f'https://telegra.ph/{response["path"]}'
        await message.reply(f'Страница создана: {page_url}')
    except Exception as e:
        logging.error(e)
        await message.reply("Произошла ошибка при создании страницы. Убедитесь, что формат сообщения верный.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
