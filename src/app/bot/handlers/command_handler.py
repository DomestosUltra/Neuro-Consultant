import logging
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, BotCommand

from src.app.bot.keyboards.main_keyboards import (
    get_model_keyboard,
    get_agent_keyboard,
    get_auth_keyboard,
)

from src.app.services.bot_functions import (
    log_interaction,
    is_first_start,
    start_auth_process,
    is_user_authenticated,
    set_auth_stage,
    get_user_credentials,
    get_user_codelab,
)


logger = logging.getLogger(__name__)

router = Router(name="Commands")


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="model", description="Выбрать модель GPT"),
        BotCommand(command="agent", description="Выбрать специалиста"),
        BotCommand(command="auth", description="Авторизация"),
        BotCommand(command="help", description="Справка по командам"),
    ]
    await bot.set_my_commands(commands)


@router.message(Command("start"))
async def cmd_start(message: Message):
    response_text = "<b>Привет! 👋</b>\nЯ – бот-диетолог, готов помочь тебе улучшить питание и здоровье!"
    await message.answer(response_text)

    start = await is_first_start(message.from_user.id)
    if start:
        await message.answer(
            "<i>Выбери модель для начала работы:</i>",
            reply_markup=get_model_keyboard(),
        )

    await log_interaction(
        message.from_user.id,
        message.from_user.username or "",
        "/start",
        "Приветствие отправлено.",
    )


@router.message(Command("model"))
async def cmd_model(message: Message):
    response_text = "<b>Выбор модели</b> 🤖\nПожалуйста, выбери одну из доступных моделей для получения рекомендаций:"
    await message.answer(response_text, reply_markup=get_model_keyboard())

    await log_interaction(
        message.from_user.id,
        message.from_user.username or "",
        "/model",
        "Изменена модель.",
    )


@router.message(Command("agent"))
async def cmd_agent(message: Message):
    response_text = (
        "<b>Выбор специалиста</b> 👨‍⚕️\n\n"
        "Выбери специалиста, который будет отвечать на твои вопросы:\n\n"
        "• 🍏 <b>Диетолог</b> - советы по питанию и диетам\n"
        "• 💪 <b>Фитнес тренер</b> - программы тренировок и упражнения\n"
        "• 🏥 <b>Врач</b> - консультации по медицинским вопросам\n\n"
        "<i>Выбранный специалист будет отвечать на следующих запросах</i>"
    )
    await message.answer(response_text, reply_markup=get_agent_keyboard())

    await log_interaction(
        message.from_user.id,
        message.from_user.username or "",
        "/agent",
        "Выбор специалиста.",
    )


@router.message(Command("auth"))
async def cmd_auth(message: Message):
    user_id = str(message.from_user.id)

    # Проверяем, авторизован ли уже пользователь
    if await is_user_authenticated(user_id):
        credentials = await get_user_credentials(user_id)
        codelab = await get_user_codelab(user_id)

        auth_details = (
            f"логин: {credentials.login}"
            if credentials
            else "данные не найдены"
        )
        codelab_details = (
            f"лабкод: {codelab}" if codelab else "лабкод не установлен"
        )

        await message.answer(
            "<b>Вы уже авторизованы</b> ✅\n\n"
            f"<b>Данные аккаунта MyGenetics:</b>\n"
            f"• {auth_details}\n"
            f"• {codelab_details}\n\n"
            "Ваши генетические данные будут использованы при ответах на вопросы."
        )
        return

    # Начинаем процесс авторизации
    await start_auth_process(user_id)
    await set_auth_stage(user_id, "waiting_credentials")

    response_text = (
        "<b>Авторизация в MyGenetics</b> 🔐\n\n"
        "Авторизация позволит использовать данные вашего отчета по генетическому тесту "
        "для более персонализированных рекомендаций.\n\n"
        "<i>Выберите действие:</i>"
    )
    await message.answer(response_text, reply_markup=get_auth_keyboard())

    await log_interaction(
        message.from_user.id,
        message.from_user.username or "",
        "/auth",
        "Запрос авторизации.",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "<b>Справка</b> ℹ️\n\n"
        "<b>Доступные команды:</b>\n"
        "<code>/start</code> — запуск бота\n"
        "<code>/model</code> — выбор модели для ответа\n"
        "<code>/agent</code> — выбор специалиста для ответа\n"
        "<code>/auth</code> — авторизация для доступа к вашим данным\n"
        "<code>/help</code> — справка по командам\n\n"
        "Для получения персональных рекомендаций просто отправь свой запрос!\n"
    )
    await message.answer(help_text)

    await log_interaction(
        message.from_user.id,
        message.from_user.username or "",
        "/help",
        help_text,
    )
