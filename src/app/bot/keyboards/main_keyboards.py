from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_model_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 ChatGPT", callback_data="model_chatgpt"
                ),
                InlineKeyboardButton(
                    text="🌐 YandexGPT", callback_data="model_yandexgpt"
                ),
            ]
        ]
    )
    return keyboard


def get_agent_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🍏 Диетолог", callback_data="agent_diet"
                ),
                InlineKeyboardButton(
                    text="💪 Фитнес тренер", callback_data="agent_fitness"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏥 Врач", callback_data="agent_medical"
                ),
                InlineKeyboardButton(
                    text="🔄 Сбросить", callback_data="agent_reset"
                ),
            ],
        ]
    )
    return keyboard


def get_auth_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопками для авторизации
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔑 Ввести логин/пароль",
                    callback_data="auth_enter_credentials",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="auth_cancel"
                )
            ],
        ]
    )
    return keyboard


def get_auth_stage_keyboard(
    stage: str = "credentials",
) -> InlineKeyboardMarkup:
    """
    Клавиатура для этапов авторизации
    """
    if stage == "credentials":
        # Клавиатура для ввода учетных данных
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Отмена", callback_data="auth_cancel"
                    )
                ],
            ]
        )
    elif stage == "codelab":
        # Клавиатура для ввода лабкода
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⏭ Пропустить", callback_data="auth_skip_codelab"
                    ),
                    InlineKeyboardButton(
                        text="❌ Отмена", callback_data="auth_cancel"
                    ),
                ],
            ]
        )
    elif stage == "authenticated":
        # Клавиатура для авторизованного пользователя
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить токен",
                        callback_data="auth_renew_token",
                    ),
                    InlineKeyboardButton(
                        text="🚪 Выйти", callback_data="auth_logout"
                    ),
                ],
            ]
        )
    else:
        # Стандартная клавиатура для отмены
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Отмена", callback_data="auth_cancel"
                    )
                ]
            ]
        )

    return keyboard


def get_auth_prompt_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для подсказки авторизации в конце сообщения
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔑 Войти", callback_data="auth_prompt"
                )
            ]
        ]
    )
    return keyboard
