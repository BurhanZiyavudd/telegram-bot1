import asyncio
import logging
from aiogram.filters import Command

from aiogram import Bot, Dispatcher, types
from config import BOT_TOKEN
import requests
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

@dp.message(Command("start"))
async def welcome(message: types.Message):
    await message.answer(
        f"Hello {message.from_user.first_name},\nIt's nice to see you!"
        f"\nHow may I help you today?"
    )

@dp.message(Command('status'))
async def status(msg: types.Message):
    response = requests.get("https://shiotstandard-production.up.railway.app/devices/1/status")
    await msg.answer(response.json())



async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())