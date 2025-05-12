import uuid
import logging
import re
from datetime import datetime
from fastapi import Depends
from aiogram import Router, F
from aiogram.types import Message
from dependency_injector.wiring import inject, Provide
from aiogram.types import (
    Message,
    CallbackQuery,
)
from openai import AsyncOpenAI

from src.app.integrations.redis import RedisService
from src.app.core.containers import Container
from src.app.integrations.rmq.publisher import publish_to_queue
from src.app.services.intent_service import IntentService
from src.app.integrations.mygenetics_api import MyGeneticsClient
from src.app.services.vector_storage_service import VectorStorageService
from src.app.utils.embedding_utils import generate_embedding

from src.app.bot.keyboards.main_keyboards import (
    get_model_keyboard,
    get_auth_keyboard,
    get_auth_prompt_keyboard,
    get_auth_stage_keyboard,
)
from src.app.services.bot_functions import (
    log_interaction,
    check_rate_limit,
    set_model,
    get_model,
    is_response_processing,
    set_user_intent_with_lock,
    check_intent_lock,
    reset_intent_lock,
    get_user_intent,
    set_user_authentication,
    start_auth_process,
    is_auth_process_active,
    cancel_auth_process,
    is_user_authenticated,
    should_show_auth_prompt,
    get_auth_stage,
    set_auth_stage,
    authenticate_with_mygenetics,
)

logger = logging.getLogger(__name__)


router = Router(name="Messages")


@router.callback_query(F.data.startswith("model_"))
async def model_selection(callback: CallbackQuery):
    model: str = callback.data.split("_")[1]

    if model == "chatgpt":
        str_model = "ChatGPT"
    elif model == "yandexgpt":
        str_model = "YandexGPT"
    else:
        return

    await set_model(callback.from_user.id, model)
    await callback.message.answer(
        f"<b>Вы выбрали модель: {str_model}</b> 🤖\nТеперь введи свой запрос для получения персональных рекомендаций по питанию."
    )

    await log_interaction(
        callback.from_user.id,
        callback.from_user.username or "",
        f"Выбор модели {model}",
        f"Модель {model} выбрана.",
    )


@router.callback_query(F.data.startswith("agent_"))
async def agent_selection(callback: CallbackQuery):
    agent_type: str = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)

    if agent_type == "reset":
        await reset_intent_lock(user_id)
        await callback.message.answer(
            "<b>Специалист сброшен</b> 🔄\nТеперь бот будет автоматически определять специалиста для твоих запросов."
        )
        await log_interaction(
            callback.from_user.id,
            callback.from_user.username or "",
            "Сброс специалиста",
            "Intent lock сброшен",
        )
        return

    # Мапинг типов агентов на intent
    specialist_names = {
        "diet": "Диетолог",
        "fitness": "Фитнес тренер",
        "medical": "Врач",
    }

    # Устанавливаем intent и блокируем его на 2 запроса
    await set_user_intent_with_lock(user_id, agent_type)

    specialist_name = specialist_names.get(agent_type, "Специалист")

    await callback.message.answer(
        f"<b>Вы выбрали специалиста: {specialist_name}</b> 👨‍⚕️\n\n"
        f"Следующие 2 твоих запроса будут обработаны специалистом: <b>{specialist_name}</b>.\n"
        f"Задай свой вопрос прямо сейчас!"
    )

    await log_interaction(
        callback.from_user.id,
        callback.from_user.username or "",
        f"Выбор специалиста {specialist_name}",
        f"Специалист {specialist_name} выбран и заблокирован на 2 запроса",
    )


@router.callback_query(F.data.startswith("auth_"))
@inject
async def auth_callback(
    callback: CallbackQuery,
    mygenetics_client: MyGeneticsClient = Depends(
        Provide[Container.mygenetics_client]
    ),
):
    action: str = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)

    if action == "prompt":
        # Пользователь нажал на кнопку "Авторизоваться" в конце сообщения
        await start_auth_process(user_id)
        await set_auth_stage(user_id, "waiting_credentials")

        await callback.message.answer(
            "<b>Авторизация в MyGenetics</b> 🔐\n\n"
            "Авторизация позволит использовать данные вашего отчета по генетическому тесту "
            "для более персонализированных рекомендаций.\n\n"
            "<i>Выберите действие:</i>",
            reply_markup=get_auth_keyboard(),
        )

        await log_interaction(
            callback.from_user.id,
            callback.from_user.username or "",
            "Запрос авторизации из промпта",
            "Начат процесс авторизации",
        )
        return

    elif action == "enter_credentials":
        # Пользователь нажал на кнопку "Ввести логин/пароль"
        await set_auth_stage(user_id, "waiting_credentials")

        await callback.message.answer(
            "<b>Ввод учетных данных MyGenetics</b> 🔒\n\n"
            "Отправьте мне свой логин и пароль от сервиса MyGenetics в формате:\n"
            "<code>логин:пароль</code>\n\n"
            "<i>Например: example@mail.ru:mypassword</i>\n\n"
            "<i>Ваши данные надежно защищены и используются только для получения доступа к генетическим отчетам.</i>",
            reply_markup=get_auth_stage_keyboard("credentials"),
        )

    elif action == "credentials_entered":
        # Пользователь указал, что ввел данные (уже должны быть в предыдущем сообщении)
        await callback.message.answer(
            "<b>Теперь введите лабкод</b> 📋\n\n"
            "Отправьте лабкод, указанный в отчете MyGenetics, чтобы бот мог использовать данные из вашего отчета.\n\n"
            "<i>Если у вас нет лабкода, вы можете пропустить этот шаг.</i>",
            reply_markup=get_auth_stage_keyboard("codelab"),
        )

        await set_auth_stage(user_id, "waiting_codelab")

    elif action == "codelab_entered" or action == "skip_codelab":
        # Авторизация завершена, мы должны были сохранить данные на предыдущих шагах
        # Пока просто установим флаг авторизации
        await set_user_authentication(user_id, True)
        await cancel_auth_process(user_id)

        await callback.message.answer(
            "<b>Авторизация успешна!</b> ✅\n\n"
            "Теперь ваши генетические данные будут использованы для более персонализированных рекомендаций.\n"
            "Продолжайте задавать вопросы, как обычно."
        )

        await log_interaction(
            callback.from_user.id,
            callback.from_user.username or "",
            "Завершение авторизации",
            "Пользователь авторизован успешно",
        )

    elif action == "cancel":
        # Отмена процесса авторизации
        await cancel_auth_process(user_id)

        await callback.message.answer(
            "<b>Авторизация отменена</b> ❌\n"
            "Вы можете продолжать использовать бота без авторизации или авторизоваться позже с помощью команды /auth."
        )

        await log_interaction(
            callback.from_user.id,
            callback.from_user.username or "",
            "Отмена авторизации",
            "Процесс авторизации отменен пользователем",
        )


@router.message(F.text)
@inject
async def handle_message(
    message: Message,
    intent_service: IntentService = Depends(Provide[Container.intent_service]),
    mygenetics_client: MyGeneticsClient = Depends(
        Provide[Container.mygenetics_client]
    ),
    vector_storage_service=Depends(Provide[Container.vector_storage_service]),
    openai_client: AsyncOpenAI = Depends(Provide[Container.openai_client]),
):
    if not await check_rate_limit(message.from_user.id):
        await message.answer(
            "<b>Слишком много запросов!</b>\nПожалуйста, подождите немного ⏳"
        )
        return

    user_id: str = str(message.from_user.id)
    chat_id: str = str(message.chat.id)
    user_query: str = str(message.text)

    # Проверяем, находится ли пользователь в процессе авторизации
    if await is_auth_process_active(user_id):
        auth_stage = await get_auth_stage(user_id)

        if auth_stage == "waiting_credentials":
            # Ожидаем ввод логина и пароля
            # Регулярное выражение для поиска логина:пароля
            credentials_regex = r"(.+?):(.+)"
            credentials_match = re.match(credentials_regex, user_query)

            if credentials_match:
                # Пользователь ввел логин и пароль в правильном формате
                login, password = credentials_match.groups()

                # Проверяем учетные данные в MyGenetics API
                auth_result, _ = await authenticate_with_mygenetics(
                    user_id, login, password
                )

                if auth_result:
                    # Успешная авторизация
                    await message.answer(
                        "<b>Учетные данные успешно проверены!</b> ✅\n\n"
                        "Теперь введите лабкод, указанный в отчете MyGenetics, чтобы бот мог использовать данные из вашего отчета.\n\n"
                        "<i>Если у вас нет лабкода, вы можете пропустить этот шаг.</i>",
                        reply_markup=get_auth_stage_keyboard("codelab"),
                    )

                    await set_auth_stage(user_id, "waiting_codelab")
                else:
                    # Неверные учетные данные
                    await message.answer(
                        "<b>Не удалось проверить учетные данные</b> ❌\n\n"
                        "Пожалуйста, проверьте логин и пароль и попробуйте еще раз.\n"
                        "Отправьте данные в формате: <code>логин:пароль</code>",
                        reply_markup=get_auth_stage_keyboard("credentials"),
                    )
            else:
                # Пользователь ввел данные в неправильном формате
                await message.answer(
                    "<b>Неверный формат учетных данных</b> ❌\n\n"
                    "Пожалуйста, отправьте логин и пароль в формате:\n"
                    "<code>логин:пароль</code>",
                    reply_markup=get_auth_stage_keyboard("credentials"),
                )

            return

        elif auth_stage == "waiting_codelab":
            # Ожидаем ввод лабкода
            # Сохраняем лабкод и завершаем авторизацию
            await set_auth_stage(user_id, "completed")

            # Здесь можно проверить лабкод, но пока просто сохраним его
            from src.app.services.bot_functions import save_user_codelab

            await save_user_codelab(user_id, user_query)

            await message.answer(
                "<b>Авторизация успешно завершена!</b> ✅\n\n"
                f"Лабкод <b>{user_query}</b> сохранен.\n\n"
                "Теперь ваши генетические данные будут использованы для более персонализированных рекомендаций.\n"
                "Продолжайте задавать вопросы, как обычно."
            )

            await cancel_auth_process(user_id)
            await set_user_authentication(user_id, True)

            await log_interaction(
                message.from_user.id,
                message.from_user.username or "",
                "Ввод лабкода",
                "Авторизация завершена успешно",
            )

            return

    # Если это не процесс авторизации, продолжаем обычную обработку
    model: str = await get_model(user_id)

    if model is None or not model:
        await message.answer(
            "<b>Выбери модель для начала работы:</b>",
            reply_markup=get_model_keyboard(),
        )
        return

    if isinstance(model, bytes):
        model = model.decode("utf-8")

    if await is_response_processing(user_id):
        await message.answer(
            "<b>Запрос в обработке...</b> ⏳\n"
            "Пожалуйста, дождитесь завершения текущего запроса перед отправкой нового."
        )
        return

    waiting_message = await message.answer("<b>Ожидайте ответ...</b> ⏳")
    waiting_message_id = waiting_message.message_id

    # Generate embedding for the user query for vector search
    # embedding = await generate_embedding(user_query, openai_client)

    # Store the user query in vector database
    await vector_storage_service.store_user_query(
        user_id, user_query, embedding=None
    )

    # Проверяем, есть ли у пользователя заблокированный intent
    intent_locked = await check_intent_lock(user_id)

    if intent_locked:
        # Если intent заблокирован, используем его
        intent = await get_user_intent(user_id)
        logger.info(
            f"Используем заблокированный intent для user {user_id}: {intent}"
        )
    else:
        try:
            # Try to find similar queries for context
            similar_queries = (
                await vector_storage_service.find_similar_queries(
                    user_query, limit=3
                )
            )
            if similar_queries:
                logger.info(
                    f"Found {len(similar_queries)} similar queries for user {user_id}"
                )

            # Классифицируем запрос для определения intent
            intent = await intent_service.classify_intent(user_id, user_query)
            logger.info(
                f"Intent для пользователя {user_id} определен как: {intent}"
            )
        except Exception as e:
            intent = "unknown"
            logger.error(f"Ошибка классификации intent: {e}")

    # Переформулируем запрос с учетом intent
    try:
        rephrased_query = await intent_service.rephrase_query(
            user_id, user_query
        )
        logger.info(f"Запрос переформулирован: {rephrased_query}")
    except Exception as e:
        rephrased_query = user_query
        logger.error(f"Ошибка переформулирования запроса: {e}")

    # Определяем, авторизован ли пользователь
    is_auth = await is_user_authenticated(user_id)
    # Проверяем, нужно ли показывать приглашение авторизоваться
    show_auth_prompt = await should_show_auth_prompt(user_id)

    task = {
        "type": "llm_task",
        "task_id": str(uuid.uuid4()),
        "user_id": user_id,
        "chat_id": chat_id,
        "user_query": user_query,  # оригинальный запрос
        "rephrased_query": rephrased_query,  # переформулированный запрос
        "model": str(model) if model else None,
        "waiting_message_id": waiting_message_id,
        "intent": intent,  # Добавляем intent в задачу
        "is_authenticated": is_auth,  # Статус авторизации
        "show_auth_prompt": show_auth_prompt,  # Нужно ли показать приглашение
        "timestamp": datetime.now().isoformat(),
        "vector_store_task_id": message.message_id,  # ID для последующего сохранения ответа
    }

    logger.debug(f"Prepared task: {task}")
    await publish_to_queue(task)

    await log_interaction(
        message.from_user.id,
        message.from_user.username or "",
        user_query,
        response_text="",
    )


@router.message()
async def handle_non_text(message: Message):
    await message.answer("<b>Пожалуйста, отправьте текстовое сообщение</b> 📝")
