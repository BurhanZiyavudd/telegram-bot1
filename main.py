from db import init_db
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from hotel_app.handlers import router

"""Loging a bot to the further actions"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler("bot.log", maxBytes=2*1024*1024, backupCount=3),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def main():
    init_db()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")