import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from redis.asyncio import Redis
from pymongo import MongoClient
from dependency_injector import containers, providers

from openai import AsyncOpenAI

from src.app.core.config import settings
from src.app.integrations.redis import RedisService
from src.app.integrations.llm.openai import OpenaiService
from src.app.integrations.llm.yandexgpt import YandexService
from src.app.integrations.mygenetics_api import MyGeneticsClient
from src.app.integrations.weaviate_client import WeaviateClient
from src.app.services.intent_service import IntentService
from src.app.services.vector_storage_service import VectorStorageService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.tests",
            "src.app.integrations.rmq.consumer",
            "src.app.bot.handlers.messages_handler",
            "src.app.bot.handlers.command_handler",
            "src.app.services.bot_functions",
            "src.app.db.crud",
        ]
    )

    config = providers.Configuration()

    redis_client = providers.Factory(
        Redis,
        host=settings.redis.REDIS_HOST,
        port=settings.redis.REDIS_PORT,
    )

    redis_service = providers.Factory(
        RedisService,
        redis_client=redis_client,
    )

    http_client_factory = providers.Factory(httpx.AsyncClient, verify=False)

    openai_client = providers.Factory(
        AsyncOpenAI,
        api_key=settings.openai.OPENAI_API_KEY,
        base_url=settings.openai.OPENAI_BASE_URL,
        http_client=http_client_factory,
    )

    openai_service = providers.Factory(
        OpenaiService,
        llm_client=openai_client,
        model=settings.openai.OPENAI_DEFAULT_MODEL,
    )

    intent_service = providers.Factory(
        IntentService,
        llm_client=openai_client,
        redis_service=redis_service,
    )

    mygenetics_client = providers.Singleton(
        MyGeneticsClient,
    )

    weaviate_client = providers.Singleton(
        WeaviateClient,
        url=settings.weaviate.WEAVIATE_URL,
        api_key=settings.openai.OPENAI_API_KEY,
    )

    vector_storage_service = providers.Factory(
        VectorStorageService,
        weaviate_client=weaviate_client,
    )

    bot = providers.Factory(
        Bot,
        token=settings.bot.TOKEN,
        default=providers.Factory(
            DefaultBotProperties, parse_mode=ParseMode.HTML
        ),
    )

    mongo_client = providers.Factory(
        MongoClient,
        host=settings.mongodb.MONGO_HOST,
        port=settings.mongodb.MONGO_PORT,
        username=settings.mongodb.MONGO_USER,
        password=settings.mongodb.MONGO_PASS,
    )

    yandex_service = providers.Factory(
        YandexService,
        api_key=settings.yandex.YANDEX_API_KEY,
        folder_id=settings.yandex.YANDEX_FOLDER_ID,
        model_name=settings.yandex.YANDEX_DEFAULT_MODEL,
    )

    dispatcher = providers.Factory(
        Dispatcher, storage=providers.Factory(MemoryStorage)
    )


class TestContainer(Container):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.tests",
            "src.app.integrations.rmq.consumer",
            "src.app.bot.handlers.messages_handler",
            "src.app.bot.handlers.command_handler",
            "src.app.services.bot_functions",
            "src.app.db.crud",
        ]
    )

    config = providers.Configuration()

    redis_client = providers.Factory(
        Redis,
        host=config.redis.host,
        port=config.redis.port,
    )

    redis_service = providers.Factory(
        RedisService,
        redis_client=redis_client,
    )
