import requests
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MyGeneticsCredentials:
    login: str
    password: str


class MyGeneticsClient:
    """
    Клиент для работы с API MyGenetics
    """

    API_BASE_URL = "https://mygenetics.ru/api/v2"

    def __init__(self):
        self.session = requests.Session()
        self._is_authenticated = False

    async def authenticate(self, login: str, password: str) -> bool:
        """
        Аутентификация пользователя в MyGenetics API
        """
        url = f"{self.API_BASE_URL}/auth/login"
        data = {"login": login, "password": password}

        try:
            response = self.session.post(url, json=data)
            if (
                response.status_code == 200
                and response.json().get("code") == "success"
            ):
                self._is_authenticated = True
                logger.info(
                    f"Успешная аутентификация в MyGenetics API для пользователя {login}"
                )
                return True
            else:
                logger.warning(
                    f"Ошибка аутентификации в MyGenetics API для пользователя {login}"
                )
                return False
        except Exception as e:
            logger.error(f"Ошибка при аутентификации в MyGenetics API: {e}")
            return False

    async def renew_token(self) -> bool:
        """
        Обновление токена аутентификации
        """
        if not self._is_authenticated:
            logger.warning(
                "Попытка обновить токен без предварительной аутентификации"
            )
            return False

        url = f"{self.API_BASE_URL}/auth/renew"
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                logger.info("Токен MyGenetics успешно обновлен")
                return True
            else:
                logger.warning(
                    f"Ошибка обновления токена MyGenetics: {response.status_code}"
                )
                self._is_authenticated = False
                return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении токена MyGenetics: {e}")
            self._is_authenticated = False
            return False

    async def get_codelab_data(self, codelab: str) -> Optional[Dict[str, Any]]:
        """
        Получение данных по лабкоду
        """
        if not self._is_authenticated:
            logger.warning("Попытка получить данные без аутентификации")
            return None

        url = f"{self.API_BASE_URL}/codelabs/{codelab}"
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Успешно получены данные по лабкоду {codelab}")
                return data
            else:
                logger.warning(
                    f"Ошибка получения данных по лабкоду {codelab}: {response.status_code}"
                )
                if response.status_code == 401:
                    self._is_authenticated = False
                return None
        except Exception as e:
            logger.error(
                f"Ошибка при получении данных по лабкоду {codelab}: {e}"
            )
            return None

    async def logout(self) -> bool:
        """
        Выход из аккаунта MyGenetics
        """
        if not self._is_authenticated:
            return True

        url = f"{self.API_BASE_URL}/auth/logout"
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                self._is_authenticated = False
                self.session = requests.Session()  # Создаем новую сессию
                logger.info("Успешный выход из аккаунта MyGenetics")
                return True
            else:
                logger.warning(
                    f"Ошибка при выходе из аккаунта MyGenetics: {response.status_code}"
                )
                return False
        except Exception as e:
            logger.error(f"Ошибка при выходе из аккаунта MyGenetics: {e}")
            return False

    @property
    def is_authenticated(self) -> bool:
        return self._is_authenticated
