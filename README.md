# Генетический Отчет Бот

Телеграм-бот для просмотра генетического отчета на основе FSM-диаграммы с использованием aiogram 3.0.

## Структура бота

Бот реализует навигацию по генетическому отчету с использованием конечного автомата (FSM) согласно следующей диаграмме:

```mermaid
stateDiagram-v2
    direction LR

    [*] --> REPORT_SUMMARY : после расшифровки

    %% Отчёт
    state REPORT_SUMMARY {
      note right: Экран 1\n«Резюме отчёта»
      [*] --> SHOW_SUMMARY
      SHOW_SUMMARY --> SHOW_SUMMARY : «Назад» (неактивна)
      SHOW_SUMMARY --> MAIN_MENU : «Вперед»
    }

    %% Главное меню
    state MAIN_MENU {
      note right: Экран 2\n«Выбор раздела»
      [*] --> MENU
      MENU --> ASK_QUESTION : «Задать вопрос по отчёту»
      MENU --> SECTION_DETOX_SUMMARY : «Системы детоксикации»
      MENU --> SECTION_BEHAVIOR_SUMMARY : «Пищевое поведение»
      MENU --> SECTION_CARB_SUMMARY : «Углеводный обмен»
      MENU --> SECTION_SPORT_SUMMARY : «Спортивное здоровье»
      MENU --> SECTION_LIPID_SUMMARY : «Лимитный обмен»
    }

    %% Задать вопрос
    state ASK_QUESTION {
      note right: Поле ввода текста\n(отправка — любым текстом)
      [*] --> INPUT_QUESTION
      INPUT_QUESTION --> CONFIRM_QUESTION : при вводе текста
      CONFIRM_QUESTION --> MAIN_MENU : «Назад» или по кнопке
    }

    %% Универсальный шаблон раздела
    state SECTION_TEMPLATE <<choice>>

    %% Системы детоксикации
    state SECTION_DETOX_SUMMARY {
      note right: Экран 1\nКраткая информация
      [*] --> SHOW_DETOX_SUMMARY
      SHOW_DETOX_SUMMARY --> MAIN_MENU : «Назад»
      SHOW_DETOX_SUMMARY --> SECTION_DETOX_DETAIL : «Подробнее»
    }
    state SECTION_DETOX_DETAIL {
      note right: Экран 2\nРасширенная информация
      [*] --> SHOW_DETOX_DETAIL
      SHOW_DETOX_DETAIL --> SECTION_DETOX_SUMMARY : «Назад»
      SHOW_DETOX_DETAIL --> SECTION_BEHAVIOR_SUMMARY : «Вперед»
    }

    %% Пищевое поведение
    state SECTION_BEHAVIOR_SUMMARY {
      note right: Экран 1\nКраткая информация
      [*] --> SHOW_BEHAVIOR_SUMMARY
      SHOW_BEHAVIOR_SUMMARY --> MAIN_MENU : «Назад»
      SHOW_BEHAVIOR_SUMMARY --> SECTION_BEHAVIOR_DETAIL : «Подробнее»
    }
    state SECTION_BEHAVIOR_DETAIL {
      note right: Экран 2\nРасширенная информация
      [*] --> SHOW_BEHAVIOR_DETAIL
      SHOW_BEHAVIOR_DETAIL --> SECTION_BEHAVIOR_SUMMARY : «Назад»
      SHOW_BEHAVIOR_DETAIL --> SECTION_CARB_SUMMARY : «Вперед»
    }

    %% Углеводный обмен
    state SECTION_CARB_SUMMARY {
      note right: Экран 1\nКраткая информация
      [*] --> SHOW_CARB_SUMMARY
      SHOW_CARB_SUMMARY --> MAIN_MENU : «Назад»
      SHOW_CARB_SUMMARY --> SECTION_CARB_DETAIL : «Подробнее»
    }
    state SECTION_CARB_DETAIL {
      note right: Экран 2\nРасширенная информация
      [*] --> SHOW_CARB_DETAIL
      SHOW_CARB_DETAIL --> SECTION_CARB_SUMMARY : «Назад»
      SHOW_CARB_DETAIL --> SECTION_SPORT_SUMMARY : «Вперед»
    }

    %% Спортивное здоровье
    state SECTION_SPORT_SUMMARY {
      note right: Экран 1\nКраткая информация
      [*] --> SHOW_SPORT_SUMMARY
      SHOW_SPORT_SUMMARY --> MAIN_MENU : «Назад»
      SHOW_SPORT_SUMMARY --> SECTION_SPORT_DETAIL : «Подробнее»
    }
    state SECTION_SPORT_DETAIL {
      note right: Экран 2\nРасширенная информация
      [*] --> SHOW_SPORT_DETAIL
      SHOW_SPORT_DETAIL --> SECTION_SPORT_SUMMARY : «Назад»
      SHOW_SPORT_DETAIL --> SECTION_LIPID_SUMMARY : «Вперед»
    }

    %% Лимитный обмен
    state SECTION_LIPID_SUMMARY {
      note right: Экран 1\nКраткая информация
      [*] --> SHOW_LIPID_SUMMARY
      SHOW_LIPID_SUMMARY --> MAIN_MENU : «Назад»
      SHOW_LIPID_SUMMARY --> SECTION_LIPID_DETAIL : «Подробнее»
    }
    state SECTION_LIPID_DETAIL {
      note right: Экран 2\nРасширенная информация
      [*] --> SHOW_LIPID_DETAIL
      SHOW_LIPID_DETAIL --> SECTION_LIPID_SUMMARY : «Назад»
      SHOW_LIPID_DETAIL --> MAIN_MENU : «Вперед»  
    }
```

## Структура проекта

- `src/app/bot/states/report_states.py` - определение состояний FSM
- `src/app/bot/keyboards/report_keyboards.py` - клавиатуры для разных экранов
- `src/app/bot/handlers/report_handlers.py` - обработчики сообщений и коллбэков
- `src/app/services/report_service.py` - сервис для работы с данными отчета

## Использование

1. Запустите бота командой:
```
python -m src.app.bot.main
```

2. Для начала работы с ботом отправьте команду:
```
/start_report
```

## Навигация

Навигация между экранами осуществляется с помощью Inline-кнопок:
- Перемещение между экранами выполняется кнопками «Назад» и «Вперед»
- Детальную информацию по разделу можно получить кнопкой «Подробнее»
- Возврат в главное меню доступен из каждого раздела через кнопку «Назад»