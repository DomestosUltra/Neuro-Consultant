import logging
from typing import Dict, Any

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from src.app.bot.states.report_states import (
    ReportSummary,
    MainMenu,
    AskQuestion,
    DetoxSection,
    BehaviorSection,
    CarbSection,
    SportSection,
    LipidSection,
)

from src.app.bot.keyboards.report_keyboards import (
    get_report_summary_kb,
    get_main_menu_kb,
    get_ask_question_kb,
    get_section_summary_kb,
    get_section_detail_kb,
)

from src.app.services.report_service import ReportService

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер для обработчиков отчета
router = Router()
report_service = ReportService()


# Вспомогательная функция для получения данных отчета
async def get_report_data(user_id: int) -> Dict[str, Any]:
    """Получаем данные отчета пользователя"""
    # В реальном сценарии здесь будет получение данных из БД
    # Для тестирования возвращаем тестовые данные
    return await report_service.get_user_report(user_id)


# Обработчики для начального экрана отчета
@router.message(Command("start_report"))
async def cmd_start_report(message: Message, state: FSMContext):
    """Команда для начала просмотра отчета"""
    user_id = message.from_user.id
    report_data = await get_report_data(user_id)

    # Сохраняем данные отчета в контексте состояния
    await state.update_data(report_data=report_data)

    # Показываем резюме отчета
    summary_text = "🧬 <b>Резюме вашего генетического отчета</b>\n\n"
    summary_text += (
        "Здесь представлено краткое резюме вашего генетического отчета. "
    )
    summary_text += "Нажмите «Вперед» для перехода в главное меню."

    await message.answer(
        text=summary_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_report_summary_kb(),
    )

    await state.set_state(ReportSummary.SHOW_SUMMARY)


# Обработчики переходов между экранами
@router.callback_query(ReportSummary.SHOW_SUMMARY, F.data == "to_main_menu")
async def to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Переход от резюме к главному меню"""
    menu_text = "🧪 <b>Выберите раздел генетического отчета</b>\n\n"
    menu_text += "Навигация по разделам отчета:"

    await callback.message.edit_text(
        text=menu_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_kb(),
    )

    await state.set_state(MainMenu.MENU)
    await callback.answer()


# Обработчики для раздела "Задать вопрос"
@router.callback_query(MainMenu.MENU, F.data == "ask_question")
async def to_ask_question(callback: CallbackQuery, state: FSMContext):
    """Переход к экрану задать вопрос"""
    question_text = "❓ <b>Задайте вопрос по своему отчету</b>\n\n"
    question_text += "Введите ваш вопрос в чат, и наш ассистент попытается на него ответить."

    await callback.message.edit_text(
        text=question_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_ask_question_kb(),
    )

    await state.set_state(AskQuestion.INPUT_QUESTION)
    await callback.answer()


@router.message(AskQuestion.INPUT_QUESTION)
async def process_question(message: Message, state: FSMContext):
    """Обработка введенного вопроса"""
    user_question = message.text

    # Сохраняем вопрос в состоянии
    await state.update_data(user_question=user_question)

    # В реальном сценарии здесь будет обработка вопроса через LLM
    answer_text = f"<b>Ваш вопрос:</b> {user_question}\n\n"
    answer_text += "Ответ: Это демонстрационный ответ на ваш вопрос. "
    answer_text += "В реальном сценарии здесь будет ответ от модели, обработанный через LLM."

    await message.answer(
        text=answer_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_ask_question_kb(),
    )

    await state.set_state(AskQuestion.CONFIRM_QUESTION)


@router.callback_query(AskQuestion.CONFIRM_QUESTION, F.data == "back_to_menu")
@router.callback_query(AskQuestion.INPUT_QUESTION, F.data == "back_to_menu")
async def question_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат из раздела вопросов в главное меню"""
    await to_main_menu(callback, state)


# Обработчики для разделов отчета
@router.callback_query(MainMenu.MENU, F.data == "section_detox")
async def to_detox_summary(callback: CallbackQuery, state: FSMContext):
    """Переход к разделу систем детоксикации (краткая информация)"""
    detox_text = "🧪 <b>Системы детоксикации</b>\n\n"
    detox_text += "Краткая информация о ваших генах, связанных с системами детоксикации.\n"
    detox_text += "Нажмите «Подробнее» для получения расширенной информации."

    await callback.message.edit_text(
        text=detox_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_section_summary_kb("detox"),
    )

    await state.set_state(DetoxSection.SHOW_SUMMARY)
    await callback.answer()


@router.callback_query(DetoxSection.SHOW_SUMMARY, F.data == "detail_detox")
async def to_detox_detail(callback: CallbackQuery, state: FSMContext):
    """Переход к подробной информации о системах детоксикации"""
    detox_detail_text = "🧪 <b>Системы детоксикации (подробно)</b>\n\n"
    detox_detail_text += "Подробная информация о генах, связанных с системами детоксикации вашего организма.\n"
    detox_detail_text += (
        "Здесь приводятся подробные рекомендации и анализ результатов."
    )

    await callback.message.edit_text(
        text=detox_detail_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_section_detail_kb("detox", "behavior"),
    )

    await state.set_state(DetoxSection.SHOW_DETAIL)
    await callback.answer()


@router.callback_query(DetoxSection.SHOW_DETAIL, F.data == "back_to_detox")
async def back_to_detox_summary(callback: CallbackQuery, state: FSMContext):
    """Возврат к краткой информации о системах детоксикации"""
    await to_detox_summary(callback, state)


@router.callback_query(DetoxSection.SHOW_DETAIL, F.data == "to_behavior")
async def to_behavior_summary(callback: CallbackQuery, state: FSMContext):
    """Переход к разделу пищевого поведения"""
    behavior_text = "🍽️ <b>Пищевое поведение</b>\n\n"
    behavior_text += (
        "Краткая информация о ваших генах, связанных с пищевым поведением.\n"
    )
    behavior_text += (
        "Нажмите «Подробнее» для получения расширенной информации."
    )

    await callback.message.edit_text(
        text=behavior_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_section_summary_kb("behavior"),
    )

    await state.set_state(BehaviorSection.SHOW_SUMMARY)
    await callback.answer()


@router.callback_query(
    BehaviorSection.SHOW_SUMMARY, F.data == "detail_behavior"
)
async def to_behavior_detail(callback: CallbackQuery, state: FSMContext):
    """Переход к подробной информации о пищевом поведении"""
    behavior_detail_text = "🍽️ <b>Пищевое поведение (подробно)</b>\n\n"
    behavior_detail_text += (
        "Подробная информация о генах, связанных с пищевым поведением.\n"
    )
    behavior_detail_text += "Здесь приводятся детальные рекомендации по питанию с учетом вашей генетики."

    await callback.message.edit_text(
        text=behavior_detail_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_section_detail_kb("behavior", "carb"),
    )

    await state.set_state(BehaviorSection.SHOW_DETAIL)
    await callback.answer()


@router.callback_query(
    BehaviorSection.SHOW_DETAIL, F.data == "back_to_behavior"
)
async def back_to_behavior_summary(callback: CallbackQuery, state: FSMContext):
    """Возврат к краткой информации о пищевом поведении"""
    await to_behavior_summary(callback, state)


@router.callback_query(BehaviorSection.SHOW_DETAIL, F.data == "to_carb")
@router.callback_query(MainMenu.MENU, F.data == "section_carb")
async def to_carb_summary(callback: CallbackQuery, state: FSMContext):
    """Переход к разделу углеводного обмена"""
    carb_text = "🥐 <b>Углеводный обмен</b>\n\n"
    carb_text += (
        "Краткая информация о ваших генах, связанных с углеводным обменом.\n"
    )
    carb_text += "Нажмите «Подробнее» для получения расширенной информации."

    await callback.message.edit_text(
        text=carb_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_section_summary_kb("carb"),
    )

    await state.set_state(CarbSection.SHOW_SUMMARY)
    await callback.answer()


@router.callback_query(CarbSection.SHOW_SUMMARY, F.data == "detail_carb")
async def to_carb_detail(callback: CallbackQuery, state: FSMContext):
    """Переход к подробной информации об углеводном обмене"""
    carb_detail_text = "🥐 <b>Углеводный обмен (подробно)</b>\n\n"
    carb_detail_text += (
        "Подробная информация о генах, связанных с углеводным обменом.\n"
    )
    carb_detail_text += (
        "Здесь приводятся детальные рекомендации по употреблению углеводов."
    )

    await callback.message.edit_text(
        text=carb_detail_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_section_detail_kb("carb", "sport"),
    )

    await state.set_state(CarbSection.SHOW_DETAIL)
    await callback.answer()


@router.callback_query(CarbSection.SHOW_DETAIL, F.data == "back_to_carb")
async def back_to_carb_summary(callback: CallbackQuery, state: FSMContext):
    """Возврат к краткой информации об углеводном обмене"""
    await to_carb_summary(callback, state)


@router.callback_query(CarbSection.SHOW_DETAIL, F.data == "to_sport")
@router.callback_query(MainMenu.MENU, F.data == "section_sport")
async def to_sport_summary(callback: CallbackQuery, state: FSMContext):
    """Переход к разделу спортивного здоровья"""
    sport_text = "🏃 <b>Спортивное здоровье</b>\n\n"
    sport_text += "Краткая информация о ваших генах, связанных со спортивным здоровьем.\n"
    sport_text += "Нажмите «Подробнее» для получения расширенной информации."

    await callback.message.edit_text(
        text=sport_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_section_summary_kb("sport"),
    )

    await state.set_state(SportSection.SHOW_SUMMARY)
    await callback.answer()


@router.callback_query(SportSection.SHOW_SUMMARY, F.data == "detail_sport")
async def to_sport_detail(callback: CallbackQuery, state: FSMContext):
    """Переход к подробной информации о спортивном здоровье"""
    sport_detail_text = "🏃 <b>Спортивное здоровье (подробно)</b>\n\n"
    sport_detail_text += "Подробная информация о генах, связанных со спортивными показателями.\n"
    sport_detail_text += "Здесь приводятся рекомендации по физическим нагрузкам с учетом вашей генетики."

    await callback.message.edit_text(
        text=sport_detail_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_section_detail_kb("sport", "lipid"),
    )

    await state.set_state(SportSection.SHOW_DETAIL)
    await callback.answer()


@router.callback_query(SportSection.SHOW_DETAIL, F.data == "back_to_sport")
async def back_to_sport_summary(callback: CallbackQuery, state: FSMContext):
    """Возврат к краткой информации о спортивном здоровье"""
    await to_sport_summary(callback, state)


@router.callback_query(SportSection.SHOW_DETAIL, F.data == "to_lipid")
@router.callback_query(MainMenu.MENU, F.data == "section_lipid")
async def to_lipid_summary(callback: CallbackQuery, state: FSMContext):
    """Переход к разделу липидного обмена"""
    lipid_text = "🧈 <b>Липидный обмен</b>\n\n"
    lipid_text += (
        "Краткая информация о ваших генах, связанных с липидным обменом.\n"
    )
    lipid_text += "Нажмите «Подробнее» для получения расширенной информации."

    await callback.message.edit_text(
        text=lipid_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_section_summary_kb("lipid"),
    )

    await state.set_state(LipidSection.SHOW_SUMMARY)
    await callback.answer()


@router.callback_query(LipidSection.SHOW_SUMMARY, F.data == "detail_lipid")
async def to_lipid_detail(callback: CallbackQuery, state: FSMContext):
    """Переход к подробной информации о липидном обмене"""
    lipid_detail_text = "🧈 <b>Липидный обмен (подробно)</b>\n\n"
    lipid_detail_text += (
        "Подробная информация о генах, связанных с липидным обменом.\n"
    )
    lipid_detail_text += (
        "Здесь приводятся рекомендации по потреблению и усвоению жиров."
    )

    await callback.message.edit_text(
        text=lipid_detail_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_section_detail_kb("lipid"),
    )

    await state.set_state(LipidSection.SHOW_DETAIL)
    await callback.answer()


@router.callback_query(LipidSection.SHOW_DETAIL, F.data == "back_to_lipid")
async def back_to_lipid_summary(callback: CallbackQuery, state: FSMContext):
    """Возврат к краткой информации о липидном обмене"""
    await to_lipid_summary(callback, state)


# Общие обработчики для всех секций для возврата в главное меню
@router.callback_query(F.data == "back_to_menu")
async def general_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Универсальный обработчик для возврата в главное меню из любой секции"""
    await to_main_menu(callback, state)
