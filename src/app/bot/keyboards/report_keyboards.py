from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def get_report_summary_kb() -> InlineKeyboardMarkup:
    """Клавиатура для экрана резюме отчета"""
    keyboard = [
        [InlineKeyboardButton(text="Вперед", callback_data="to_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_main_menu_kb() -> InlineKeyboardMarkup:
    """Клавиатура для главного меню выбора раздела"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Задать вопрос по отчёту", callback_data="ask_question"
            )
        ],
        [
            InlineKeyboardButton(
                text="Системы детоксикации", callback_data="section_detox"
            )
        ],
        [
            InlineKeyboardButton(
                text="Пищевое поведение", callback_data="section_behavior"
            )
        ],
        [
            InlineKeyboardButton(
                text="Углеводный обмен", callback_data="section_carb"
            )
        ],
        [
            InlineKeyboardButton(
                text="Спортивное здоровье", callback_data="section_sport"
            )
        ],
        [
            InlineKeyboardButton(
                text="Лимитный обмен", callback_data="section_lipid"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_ask_question_kb() -> InlineKeyboardMarkup:
    """Клавиатура для экрана ввода вопроса"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Назад в меню", callback_data="back_to_menu"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_section_summary_kb(section: str) -> InlineKeyboardMarkup:
    """Клавиатура для экрана с кратким резюме секции"""
    keyboard = [
        [
            InlineKeyboardButton(text="Назад", callback_data="back_to_menu"),
            InlineKeyboardButton(
                text="Подробнее", callback_data=f"detail_{section}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_section_detail_kb(
    section: str, next_section: str = None
) -> InlineKeyboardMarkup:
    """Клавиатура для экрана с подробной информацией секции"""
    buttons = [
        InlineKeyboardButton(text="Назад", callback_data=f"back_to_{section}")
    ]

    if next_section:
        buttons.append(
            InlineKeyboardButton(
                text="Вперед", callback_data=f"to_{next_section}"
            )
        )
    else:
        buttons.append(
            InlineKeyboardButton(text="Вперед", callback_data="back_to_menu")
        )

    keyboard = [buttons]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
