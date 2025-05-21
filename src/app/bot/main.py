import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from src.app.core.config import settings
from src.app.bot.handlers.report_handlers import router as report_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Создаем экземпляр бота
bot = Bot(
    token=settings.bot.TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)


async def setup_bot():
    # Выбираем хранилище состояний (Redis в продакшне, Memory для разработки)
    if settings.ENVIRONMENT == "production":
        storage = RedisStorage.from_url(
            url=f"redis://{settings.redis.REDIS_HOST}:{settings.redis.REDIS_PORT}/0",
            password=settings.redis.REDIS_PASSWORD,
        )
    else:
        storage = MemoryStorage()

    # Создаем диспетчер
    dp = Dispatcher(storage=storage)

    # Регистрируем роутеры
    dp.include_router(report_router)

    return dp


# Инициализируем диспетчер для использования в других модулях
dp = Dispatcher(storage=MemoryStorage())


if __name__ == "__main__":
    try:
        # Пересоздаем диспетчер с правильным хранилищем и роутерами
        dp = asyncio.run(setup_bot())
        asyncio.run(dp.start_polling(bot))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
