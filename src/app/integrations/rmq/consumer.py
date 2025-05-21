import re
import json
import asyncio
import logging
import aio_pika

from typing import Dict
from aiogram import Bot
from logging.config import dictConfig
from aiogram.enums import ParseMode

from src.app.utils.log_config import LogConfig
from src.app.core.config import settings
from src.app.core.containers import Container
from src.app.integrations.redis import RedisService
from src.app.integrations.llm.openai import OpenaiService
from src.app.integrations.llm.yandexgpt import YandexService
from src.app.services.vector_storage_service import VectorStorageService
from src.app.utils.embedding_utils import generate_embedding
from src.app.core.prompts import SYSTEM_PROMPT, INTENT_PROMPTS
from src.app.bot.main import bot
from src.app.bot.keyboards.main_keyboards import get_auth_prompt_keyboard
from src.app.utils.general import (
    convert_to_allowed_tags,
)


log_config = LogConfig()
log_config_dict = log_config.model_dump()
dictConfig(log_config_dict)

logger = logging.getLogger(__name__)


class BaseTaskHandler:
    async def handle(self, task: dict):
        raise NotImplementedError


class LLMTaskHandler(BaseTaskHandler):
    def __init__(
        self,
        redis_service: RedisService,
        openai_service: OpenaiService,
        yandex_service: YandexService,
        vector_storage_service: VectorStorageService,
        bot: Bot,
    ) -> None:
        self.redis_service = redis_service
        self.openai_service = openai_service
        self.yandex_service = yandex_service
        self.vector_storage_service = vector_storage_service
        self.bot = bot

    async def handle(self, task: Dict) -> None:
        task_id = task.get("task_id")
        user_id = task.get("user_id")
        chat_id = task.get("chat_id")
        user_query = task.get("user_query")
        rephrased_query = task.get("rephrased_query", user_query)
        model = task.get("model")
        waiting_message_id: int = int(task.get("waiting_message_id"))
        intent = task.get("intent", "unknown")
        is_authenticated = task.get("is_authenticated", False)
        show_auth_prompt = task.get("show_auth_prompt", False)
        vector_store_task_id = task.get("vector_store_task_id")

        try:
            if model == "chatgpt":
                llm_service = self.openai_service
            elif model == "yandexgpt":
                llm_service = self.yandex_service
            else:
                raise ValueError(f"Unknown model: {model}")

            await self.redis_service.set(
                f"task:{user_id}:status", "processing", ex=60
            )

            system_prompt = INTENT_PROMPTS.get(intent, SYSTEM_PROMPT)
            logger.info(f"Using {intent} prompt for user {user_id}")

            # Дополняем промпт релевантной информацией из базы знаний
            additional_context = []

            # Если запрос связан с часто задаваемыми вопросами, ищем ответы в FAQ
            try:
                faq_entries = (
                    await self.vector_storage_service.find_faq_entries(
                        rephrased_query, limit=2
                    )
                )
                if faq_entries:
                    faq_context = (
                        "\n\nИнформация из часто задаваемых вопросов:\n"
                    )
                    for entry in faq_entries:
                        faq_context += f"Вопрос: {entry['question']}\nОтвет: {entry['answer']}\n\n"
                    additional_context.append(faq_context)
                    logger.info(
                        f"Added {len(faq_entries)} FAQ entries to the context for user {user_id}"
                    )
            except Exception as e:
                logger.error(f"Error retrieving FAQ entries: {e}")

            # Ищем релевантные статьи из базы знаний
            try:
                knowledge_articles = (
                    await self.vector_storage_service.find_knowledge_articles(
                        rephrased_query, limit=2
                    )
                )
                if knowledge_articles:
                    kb_context = "\n\nРелевантная информация из базы знаний:\n"
                    for article in knowledge_articles:
                        kb_context += f"Тема: {article['title']}\nСодержание: {article['content']}\n\n"
                    additional_context.append(kb_context)
                    logger.info(
                        f"Added {len(knowledge_articles)} knowledge base articles to the context for user {user_id}"
                    )
            except Exception as e:
                logger.error(f"Error retrieving knowledge base articles: {e}")

            # Если пользователь авторизован, добавляем в промпт информацию о генетических данных
            if is_authenticated:
                try:
                    genetic_report = (
                        await self.vector_storage_service.get_genetic_report(
                            user_id
                        )
                    )
                    if genetic_report:
                        genetics_context = "\n\nИнформация из генетического отчета пользователя:\n"
                        # В реальности здесь нужно будет извлечь ключевую информацию из отчета,
                        # которая релевантна текущему запросу пользователя
                        genetics_context += f"Лабкод пользователя: {genetic_report.get('codelab')}\n"

                        # Можно добавить обработку report_data с извлечением нужных данных
                        # Пример: report_data = genetic_report.get('report_data', {})
                        # Извлекать и форматировать нужную информацию

                        additional_context.append(genetics_context)
                        logger.info(
                            f"Added genetic report data to the context for user {user_id}"
                        )
                except Exception as e:
                    logger.error(f"Error retrieving genetic report: {e}")
                    additional_context.append(
                        "\n\nУ вас есть доступ к генетическим данным пользователя. Интегрируйте эту информацию в свои рекомендации."
                    )

            # Добавляем дополнительный контекст к промпту
            if additional_context:
                system_prompt += "\n\n" + "\n".join(additional_context)

            response_text: str = await llm_service.get_response(
                rephrased_query, system_prompt=system_prompt
            )

            html_response_text = convert_to_allowed_tags(response_text)

            # Добавляем приглашение авторизоваться, если нужно
            if show_auth_prompt and not is_authenticated:
                auth_prompt = (
                    "\n\n<hr>\n"
                    "<i>💡 Авторизуйтесь для персональных рекомендаций на основе генетического отчета</i>"
                )
                html_response_text += auth_prompt

            # Сохраняем запрос пользователя в векторной базе (уже сделано в обработчике сообщений)
            # Историю диалогов не храним в Weaviate, как указано в требованиях

            await self.bot.delete_message(
                chat_id=chat_id, message_id=waiting_message_id
            )
            await self.redis_service.set(f"task:{user_id}:status", "completed")

            # Отправляем ответ с кнопкой авторизации или без неё
            if show_auth_prompt and not is_authenticated:
                await self.bot.send_message(
                    text=html_response_text,
                    chat_id=chat_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_auth_prompt_keyboard(),
                )
            else:
                await self.bot.send_message(
                    text=html_response_text,
                    chat_id=chat_id,
                    parse_mode=ParseMode.HTML,
                )

            await self.redis_service.set(
                f"task:{task_id}:response", response_text, ex=60
            )

        except Exception as e:
            logger.error(f"Ошибка при обработке задачи {task_id}: {e}")
            await self.redis_service.set(f"task:{task_id}:status", "failed")
            try:
                await self.bot.delete_message(
                    chat_id=chat_id, message_id=waiting_message_id
                )
                await self.bot.send_message(
                    text="<b>К сожалению, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.</b>",
                    chat_id=chat_id,
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e2:
                logger.error(f"Не удалось отправить сообщение об ошибке: {e2}")


TASK_HANDLERS: Dict[str, BaseTaskHandler] = {
    "llm_task": LLMTaskHandler(
        redis_service=Container.redis_service(),
        openai_service=Container.openai_service(),
        yandex_service=Container.yandex_service(),
        vector_storage_service=Container.vector_storage_service(),
        bot=bot,
    ),
}


async def on_message(message: aio_pika.IncomingMessage):
    async with message.process():
        task = json.loads(message.body)

        task_type = task.get("type")
        handler = TASK_HANDLERS.get(task_type)

        if handler:
            asyncio.create_task(handler.handle(task))
            logger.info(f"Task scheduled: {task_type}")
        else:
            logger.info(f"Unknown task type: {task_type}")


async def consumer():
    connection = await aio_pika.connect_robust(
        f"amqp://{settings.rabbit.RABBITMQ_USER}:{settings.rabbit.RABBITMQ_PASS}@rabbitmq/"
    )
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue = await channel.declare_queue("task_queue", durable=True)
    await queue.consume(on_message)
    await asyncio.Future()


if __name__ == "__main__":
    from src.app.core.containers import Container
    from src.app.core.config import settings

    container = Container()
    container.config.from_pydantic(settings)
    container.wire(
        modules=[
            "src.app.integrations.rmq.consumer",
            "src.app.bot.handlers.messages_handler",
            "src.app.bot.handlers.command_handler",
            "src.app.services.bot_functions",
            "src.app.db.crud",
        ]
    )

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(consumer())
    except RuntimeError:
        asyncio.run(consumer())  # Безопасный запуск
