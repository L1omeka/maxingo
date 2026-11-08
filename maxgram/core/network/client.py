"""
Базовый HTTP-клиент для API Max
"""

import requests
from typing import Dict, Any, Optional, Union, List
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Client:
    """Класс для выполнения HTTP-запросов к API Max"""
    
    BASE_URL = "https://botapi.max.ru"
    
    def __init__(self, token: str, client_options: Optional[Dict[str, Any]] = None):
        """
        Инициализация клиента
        
        Args:
            token: Токен доступа бота
            client_options: Дополнительные настройки клиента
        """
        self.token = token
        self.options = client_options or {}
        self.session = requests.Session()
    
    def _build_url(self, path: str) -> str:
        """
        Формирует полный URL для запроса
        
        Args:
            path: Путь к методу API
            
        Returns:
            Полный URL для запроса
        """
        return f"{self.BASE_URL}{path}"
    
    def request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, 
                data: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выполняет запрос к API
        
        Args:
            method: HTTP-метод (GET, POST, PUT, DELETE)
            path: Путь к методу API
            params: Параметры запроса
            data: Данные для отправки в теле запроса
            files: Файлы для отправки
            
        Returns:
            Ответ от API в виде словаря
            
        Raises:
            Exception: При ошибке запроса
        """
        url = self._build_url(path)
        
        headers = {
            "User-Agent": f"MaxgramPython/0.1.0",
            "Authorization": self.token,
        }
        
        if data and not files:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data)
        
        logger.debug(f"Request: {method} {url}")
        if params:
            logger.debug(f"Params: {params}")
        if data:
            logger.debug(f"Data: {data}")
        
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            files=files,
            headers=headers,
            timeout=self.options.get("timeout", 60)
        )
        
        try:
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Response: {result}")
            return result
        except requests.exceptions.HTTPError as e:
            error_text = f"HTTP error: {e}"
            try:
                error_json = response.json()
                error_text = f"{error_text}, API response: {error_json}"
            except:
                error_text = f"{error_text}, Response text: {response.text}"
            
            logger.error(error_text)
            raise Exception(error_text)
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise 