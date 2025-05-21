import logging
from fastapi import Depends
from dependency_injector.wiring import inject, Provide
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Tuple, Optional, Any

from src.app.integrations.redis import RedisService
from src.app.integrations.mygenetics_api import (
    MyGeneticsClient,
    MyGeneticsCredentials,
)
from src.app.services.vector_storage_service import VectorStorageService
from src.app.core.containers import Container
from src.app.core.config import settings


logger = logging.getLogger(__name__)


@inject
async def check_rate_limit(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> bool:
    key = f"tg_user:{user_id}:msg_count"
    try:
        count = await redis_service.get(key)
        logger.info(f"Проверка лимита для user_id {user_id}: count = {count}")

        if count is None:
            await redis_service.set(key, "1", ex=60)
            logger.info(f"Установлен новый счётчик для user_id {user_id}: 1")
            return True
        else:
            count = int(count)
            if count >= settings.bot.MAX_MESSAGES_PER_MINUTE:
                logger.info(
                    f"Лимит превышен для user_id {user_id}: {count} >= {settings.bot.MAX_MESSAGES_PER_MINUTE}"
                )
                return False
            else:
                new_count = count + 1
                await redis_service.set(key, str(new_count), ex=60)
                logger.info(
                    f"Счётчик увеличен для user_id {user_id}: {new_count}"
                )
                return True
    except ValueError:
        logger.error(
            f"Некорректное значение счётчика для user_id {user_id}: {count}"
        )
        return False
    except Exception as e:
        logger.error(f"Ошибка Redis для user_id {user_id}: {e}")
        return True  # Разрешаем запрос, если Redis недоступен


@inject
async def is_first_start(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> bool:
    key = f"tg_user:{user_id}"
    user = await redis_service.get(key)
    if user is None:
        await redis_service.set(key, value="False")
        return True

    return False


@inject
async def set_model(
    user_id: str,
    model_name: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    key = f"tg_user:{user_id}:model"
    await redis_service.set(key, value=model_name)


@inject
async def get_model(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> str | None:
    key = f"tg_user:{user_id}:model"
    model = await redis_service.get(key)
    return model if model else None


@inject
async def get_user_intent(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> str:
    key = f"tg_user:{user_id}:intent"
    intent = await redis_service.get(key)
    return intent if intent else "unknown"


@inject
async def set_user_intent_with_lock(
    user_id: str,
    intent: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    """
    Устанавливает intent пользователя и блокирует его на 2 запроса
    """
    # Сохраняем intent
    intent_key = f"tg_user:{user_id}:intent"
    await redis_service.set(intent_key, intent)

    # Устанавливаем счетчик запросов для блокировки
    lock_key = f"tg_user:{user_id}:intent_lock"
    await redis_service.set(lock_key, "2")  # 2 запроса

    logger.info(
        f"Intent для пользователя {user_id} установлен на '{intent}' и заблокирован на 2 запроса"
    )


@inject
async def check_intent_lock(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> bool:
    """
    Проверяет, заблокирован ли intent пользователя.
    Возвращает True, если заблокирован, False - если нет.
    """
    lock_key = f"tg_user:{user_id}:intent_lock"
    lock_count = await redis_service.get(lock_key)

    if lock_count is None:
        return False

    try:
        count = int(lock_count)
        if count > 0:
            # Уменьшаем счетчик
            new_count = count - 1
            if new_count > 0:
                await redis_service.set(lock_key, str(new_count))
                logger.info(
                    f"Intent lock для пользователя {user_id}: осталось {new_count} запросов"
                )
            else:
                # Если счетчик достиг нуля, удаляем блокировку
                await redis_service.set(lock_key, "0")
                logger.info(f"Intent lock для пользователя {user_id} снят")
            return True
        else:
            return False
    except ValueError:
        logger.error(
            f"Некорректное значение блокировки intent для user_id {user_id}: {lock_count}"
        )
        return False


@inject
async def reset_intent_lock(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    """
    Сбрасывает блокировку intent пользователя
    """
    lock_key = f"tg_user:{user_id}:intent_lock"
    await redis_service.set(lock_key, "0")
    logger.info(f"Intent lock для пользователя {user_id} сброшен")


@inject
async def is_user_authenticated(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> bool:
    """
    Проверяет, авторизован ли пользователь
    """
    key = f"tg_user:{user_id}:auth"
    auth_status = await redis_service.get(key)
    return auth_status == "authenticated"


@inject
async def get_user_credentials(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> Optional[MyGeneticsCredentials]:
    """
    Получает учетные данные пользователя из Redis
    """
    login_key = f"tg_user:{user_id}:mygenetics:login"
    password_key = f"tg_user:{user_id}:mygenetics:password"

    login = await redis_service.get(login_key)
    password = await redis_service.get(password_key)

    if login and password:
        return MyGeneticsCredentials(login=login, password=password)

    return None


@inject
async def save_user_credentials(
    user_id: str,
    login: str,
    password: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    """
    Сохраняет учетные данные пользователя в Redis
    """
    login_key = f"tg_user:{user_id}:mygenetics:login"
    password_key = f"tg_user:{user_id}:mygenetics:password"

    await redis_service.set(login_key, login)
    await redis_service.set(password_key, password)

    logger.info(
        f"Учетные данные MyGenetics для пользователя {user_id} сохранены"
    )


@inject
async def delete_user_credentials(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    """
    Удаляет учетные данные пользователя из Redis
    """
    login_key = f"tg_user:{user_id}:mygenetics:login"
    password_key = f"tg_user:{user_id}:mygenetics:password"

    await redis_service.set(login_key, "")
    await redis_service.set(password_key, "")

    logger.info(
        f"Учетные данные MyGenetics для пользователя {user_id} удалены"
    )


@inject
async def save_user_codelab(
    user_id: str,
    codelab: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    """
    Сохраняет лабкод пользователя в Redis
    """
    key = f"tg_user:{user_id}:mygenetics:codelab"
    await redis_service.set(key, codelab)
    logger.info(
        f"Лабкод MyGenetics для пользователя {user_id} сохранен: {codelab}"
    )


@inject
async def get_user_codelab(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> Optional[str]:
    """
    Получает лабкод пользователя из Redis
    """
    key = f"tg_user:{user_id}:mygenetics:codelab"
    codelab = await redis_service.get(key)
    return codelab


@inject
async def set_user_authentication(
    user_id: str,
    authenticated: bool,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    """
    Устанавливает статус авторизации пользователя
    """
    key = f"tg_user:{user_id}:auth"
    value = "authenticated" if authenticated else "not_authenticated"
    await redis_service.set(key, value)
    logger.info(
        f"Статус авторизации пользователя {user_id} установлен на {value}"
    )


@inject
async def authenticate_with_mygenetics(
    user_id: str,
    login: str,
    password: str,
    codelab: Optional[str] = None,
    mygenetics_client: MyGeneticsClient = Depends(
        Provide[Container.mygenetics_client]
    ),
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
    vector_storage_service: VectorStorageService = Depends(
        Provide[Container.vector_storage_service]
    ),
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Аутентификация пользователя в MyGenetics и получение данных по лабкоду
    """
    # Попытка аутентификации
    auth_success = await mygenetics_client.authenticate(login, password)

    if not auth_success:
        logger.warning(
            f"Не удалось аутентифицировать пользователя {user_id} в MyGenetics"
        )
        return False, None

    # Сохранить учетные данные
    await save_user_credentials(user_id, login, password)

    # Установить флаг аутентификации
    await set_user_authentication(user_id, True)

    # Если указан лабкод, получим по нему данные
    codelab_data = None
    if codelab:
        codelab_data = await mygenetics_client.get_codelab_data(codelab)
        if codelab_data:
            await save_user_codelab(user_id, codelab)

            # Сохраняем генетический отчет в векторное хранилище для последующего поиска
            try:
                await vector_storage_service.store_genetic_report(
                    user_id=user_id,
                    codelab=codelab,
                    report_data=codelab_data,
                    embedding=None,  # Позволяем Weaviate создать вектор автоматически
                )
                logger.info(
                    f"Генетический отчет для пользователя {user_id} сохранен в векторной базе данных"
                )
            except Exception as e:
                logger.error(
                    f"Ошибка при сохранении генетического отчета в векторную базу: {e}"
                )
                # Продолжаем работу даже при ошибке векторного хранилища

    return True, codelab_data


@inject
async def start_auth_process(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    """
    Начинает процесс авторизации для пользователя
    """
    key = f"tg_user:{user_id}:auth_process"
    await redis_service.set(
        key, "started", ex=300
    )  # Устанавливаем статус и время жизни 5 минут
    logger.info(f"Начат процесс авторизации для пользователя {user_id}")


@inject
async def is_auth_process_active(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> bool:
    """
    Проверяет, активен ли процесс авторизации для пользователя
    """
    key = f"tg_user:{user_id}:auth_process"
    status = await redis_service.get(key)
    return status == "started"


@inject
async def cancel_auth_process(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    """
    Отменяет процесс авторизации для пользователя
    """
    key = f"tg_user:{user_id}:auth_process"
    await redis_service.set(key, "canceled")
    logger.info(f"Процесс авторизации для пользователя {user_id} отменен")


@inject
async def get_auth_stage(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> str:
    """
    Получает текущий этап процесса авторизации

    Возможные значения:
    - "waiting_credentials" - ожидание ввода логина/пароля
    - "waiting_codelab" - ожидание ввода лабкода
    - "none" - процесс не активен
    """
    if not await is_auth_process_active(user_id):
        return "none"

    key = f"tg_user:{user_id}:auth_stage"
    stage = await redis_service.get(key)
    return stage or "waiting_credentials"


@inject
async def set_auth_stage(
    user_id: str,
    stage: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    """
    Устанавливает текущий этап процесса авторизации
    """
    key = f"tg_user:{user_id}:auth_stage"
    await redis_service.set(key, stage, ex=300)  # 5 минут
    logger.info(
        f"Этап авторизации для пользователя {user_id} установлен на {stage}"
    )


@inject
async def should_show_auth_prompt(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> bool:
    """
    Проверяет, нужно ли показывать приглашение авторизоваться
    """
    # Если пользователь уже авторизован, не показываем
    if await is_user_authenticated(user_id):
        return False

    # Если процесс авторизации уже активен, не показываем
    if await is_auth_process_active(user_id):
        return False

    # Проверяем, когда в последний раз показывали приглашение
    key = f"tg_user:{user_id}:auth_prompt_shown"
    last_shown = await redis_service.get(key)

    if last_shown is None:
        # Если никогда не показывали, то нужно показать
        await redis_service.set(key, "shown", ex=3600)  # Показываем раз в час
        return True

    # Иначе не показываем (будет показано через час после последнего показа)
    return False


@inject
async def is_response_processing(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> str:
    key = f"task:{user_id}:status"
    status = await redis_service.get(key)
    if not status or status == "completed":
        return False
    return True


@inject
async def log_interaction(
    user_id: int,
    username: str,
    message_text: str,
    response_text: str,
):
    # Log to console
    logger.info(f"{user_id}||{username}||{message_text}||{response_text}")

    # Save to database
    try:
        logger.info(f"User interaction saved to database: user_id={user_id}")
    except Exception as e:
        logger.error(f"Failed to save user interaction to database: {e}")


@inject
async def renew_mygenetics_token(
    user_id: str,
    mygenetics_client: MyGeneticsClient = Depends(
        Provide[Container.mygenetics_client]
    ),
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> bool:
    """
    Обновляет токен авторизации пользователя в MyGenetics

    Args:
        user_id: ID пользователя

    Returns:
        bool: Успешно ли обновлен токен
    """
    # Проверяем, авторизован ли пользователь
    if not await is_user_authenticated(user_id):
        logger.warning(
            f"Попытка обновить токен для неавторизованного пользователя {user_id}"
        )
        return False

    # Получаем учетные данные пользователя
    credentials = await get_user_credentials(user_id)
    if not credentials:
        logger.warning(f"Не найдены учетные данные для пользователя {user_id}")
        return False

    # Пробуем обновить токен
    result = await mygenetics_client.renew_token()

    # Если не удалось обновить токен, пробуем заново аутентифицироваться
    if not result:
        logger.info(
            f"Не удалось обновить токен для пользователя {user_id}, пробуем заново аутентифицироваться"
        )
        result = await mygenetics_client.authenticate(
            credentials.login, credentials.password
        )

        if not result:
            # Если и повторная аутентификация не удалась, сбрасываем статус авторизации
            await set_user_authentication(user_id, False)
            logger.warning(
                f"Не удалось аутентифицироваться для пользователя {user_id}, сбрасываем статус авторизации"
            )
            return False

    logger.info(f"Токен успешно обновлен для пользователя {user_id}")
    return True


@inject
async def logout_from_mygenetics(
    user_id: str,
    mygenetics_client: MyGeneticsClient = Depends(
        Provide[Container.mygenetics_client]
    ),
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> bool:
    """
    Выполняет выход из аккаунта MyGenetics

    Args:
        user_id: ID пользователя

    Returns:
        bool: Успешно ли выполнен выход
    """
    # Проверяем, авторизован ли пользователь
    if not await is_user_authenticated(user_id):
        logger.warning(
            f"Попытка выйти из аккаунта для неавторизованного пользователя {user_id}"
        )
        return False

    # Выполняем выход из аккаунта
    result = await mygenetics_client.logout()

    # Сбрасываем статус авторизации в любом случае
    await set_user_authentication(user_id, False)

    # Удаляем учетные данные
    await delete_user_credentials(user_id)

    logger.info(
        f"Выход из аккаунта MyGenetics для пользователя {user_id}: {result}"
    )
    return True


@inject
async def save_temp_login(
    user_id: str,
    login: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> None:
    """
    Временно сохраняет логин пользователя во время процесса авторизации
    """
    key = f"tg_user:{user_id}:temp_login"
    await redis_service.set(key, login, ex=300)  # 5 минут
    logger.info(f"Временно сохранен логин для пользователя {user_id}")


@inject
async def get_temp_login(
    user_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> Optional[str]:
    """
    Получает временно сохраненный логин пользователя
    """
    key = f"tg_user:{user_id}:temp_login"
    login = await redis_service.get(key)
    return login
