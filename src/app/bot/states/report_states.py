from aiogram.fsm.state import State, StatesGroup


class ReportSummary(StatesGroup):
    SHOW_SUMMARY = State()


class MainMenu(StatesGroup):
    MENU = State()


class AskQuestion(StatesGroup):
    INPUT_QUESTION = State()
    CONFIRM_QUESTION = State()


class DetoxSection(StatesGroup):
    SHOW_SUMMARY = State()
    SHOW_DETAIL = State()


class BehaviorSection(StatesGroup):
    SHOW_SUMMARY = State()
    SHOW_DETAIL = State()


class CarbSection(StatesGroup):
    SHOW_SUMMARY = State()
    SHOW_DETAIL = State()


class SportSection(StatesGroup):
    SHOW_SUMMARY = State()
    SHOW_DETAIL = State()


class LipidSection(StatesGroup):
    SHOW_SUMMARY = State()
    SHOW_DETAIL = State()
