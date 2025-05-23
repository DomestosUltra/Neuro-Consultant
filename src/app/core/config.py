import os

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic_settings import BaseSettings

load_dotenv()


class AppSettings(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LOCAL")
    BASE_DIR: str = str(Path(__file__).resolve().parent.parent)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "MyR@nD0m^$3cR3t%K3Y")


class RedisSettings(BaseSettings):
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD", "password")
    REDIS_USER: str | None = os.getenv("REDIS_USER", "user")
    REDIS_USER_PASSWORD: str | None = os.getenv(
        "REDIS_USER_PASSWORD", "password"
    )


class RabbitSettings(BaseSettings):
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASS: str = os.getenv("RABBITMQ_PASS", "guest")


class PostgresSettings(BaseSettings):
    HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    PORT: str = os.getenv("POSTGRES_PORT", "5432")
    USER: str = os.getenv("POSTGRES_USER", "postgres")
    PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    DB: str = os.getenv("POSTGRES_DB", "nutritionist_bot")


class OpenaiSettings(BaseSettings):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_DEFAULT_MODEL: str = os.getenv("OPENAI_DEFAULT_MODEL")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL")


class YandexGPTSettings(BaseSettings):
    YANDEX_API_KEY: str = os.getenv("YANDEX_API_KEY")
    YANDEX_DEFAULT_MODEL: str = os.getenv("YANDEX_DEFAULT_MODEL")
    YANDEX_BASE_URL: str = os.getenv(
        "YANDEX_BASE_URL",
        "https://llm.api.cloud.yandex.net/foundationModels/v1",
    )
    YANDEX_FOLDER_ID: str = os.getenv("YANDEX_FOLDER_ID")


class BotSettings(BaseSettings):
    TOKEN: str = os.getenv("BOT_TOKEN")
    WEBHOOK_URL: str = os.getenv("TG_WEBHOOK_URL", "https://your.domain.com")
    MAX_MESSAGES_PER_MINUTE: int = 5


class MongoDBSettings(BaseSettings):
    MONGO_HOST: str = os.getenv("MONGO_HOST", "localhost")
    MONGO_PORT: int = int(os.getenv("MONGO_PORT", "27017"))
    MONGO_USER: str = os.getenv("MONGO_USER", "root")
    MONGO_PASS: str = os.getenv("MONGO_PASS", "example")


class WeaviateSettings(BaseSettings):
    WEAVIATE_URL: str = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
    WEAVIATE_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    WEAVIATE_BATCH_SIZE: int = int(os.getenv("WEAVIATE_BATCH_SIZE", "100"))


class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    redis: RedisSettings = RedisSettings()
    rabbit: RabbitSettings = RabbitSettings()
    postgres: PostgresSettings = PostgresSettings()
    openai: OpenaiSettings = OpenaiSettings()
    bot: BotSettings = BotSettings()
    yandex: YandexGPTSettings = YandexGPTSettings()
    mongodb: MongoDBSettings = MongoDBSettings()
    weaviate: WeaviateSettings = WeaviateSettings()


settings = Settings()


def create_app(settings: Settings, lifespan) -> FastAPI:
    app_settings = {
        "title": "bot-service",
    }
    if settings.app.ENVIRONMENT != "PROD":
        app_settings.update(
            {
                "docs_url": "/api/v1/docs",
                "openapi_url": "/api/v1/openapi.json",
                "redoc_url": "/api/v1/redoc",
                "swagger_ui_oauth2_redirect_url": "/backend/docs/oauth2-redirect",  # noqa
            }
        )

    app = FastAPI(**app_settings, debug=True, lifespan=lifespan)

    return app


def create_bot():
    pass
