"""
API-клиент для работы с API Max
"""

from typing import Dict, Any, List, Optional, Union
from maxgram.core.network.client import Client

class Api:
    """
    API-клиент для работы с API Max
    
    Класс предоставляет методы для работы с различными ресурсами API.
    """
    
    def __init__(self, token: str, client_options: Optional[Dict[str, Any]] = None):
        """
        Инициализация API-клиента
        
        Args:
            token: Токен доступа бота
            client_options: Дополнительные настройки клиента
        """
        self.client = Client(token, client_options)
    
    def get_my_info(self) -> Dict[str, Any]:
        """
        Получает информацию о текущем боте
        
        Returns:
            Информация о боте
        """
        return self.client.request("GET", "/me")
    
    def set_my_commands(self, commands: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Устанавливает команды для бота через PATCH /me
        
        Args:
            commands: Список команд в формате [{"name": "command", "description": "Description"}]
            
        Returns:
            Результат запроса PATCH /me
        """
        return self.client.request("PATCH", "/me", data={"commands": commands})
    
    def send_message(self, chat_id: int, text: str, attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Отправляет сообщение в чат
        
        Args:
            chat_id: Идентификатор чата
            text: Текст сообщения
            attachments: Вложения сообщения
            
        Returns:
            Информация об отправленном сообщении
        """
        # Параметры запроса
        params = {
            "chat_id": chat_id
        }
        
        # Тело запроса
        data = {
            "text": text
        }
        
        if attachments:
            data["attachments"] = attachments
        
        return self.client.request("POST", "/messages", params=params, data=data)
    
    def edit_message(self, message_id: str, text: str, attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Редактирует существующее сообщение
        
        Args:
            message_id: Идентификатор сообщения
            text: Новый текст сообщения
            attachments: Новые вложения сообщения
            
        Returns:
            Информация об отредактированном сообщении
        """
        # Параметры запроса
        params = {
            "message_id": message_id
        }
        
        # Тело запроса
        data = {
            "text": text
        }
        
        if attachments:
            data["attachments"] = attachments
        
        return self.client.request("PUT", "/messages", params=params, data=data)
    
    def answer_callback(self, callback_id: str, text: Optional[str] = None) -> Dict[str, Any]:
        """
        Отправляет ответ на колбэк
        
        Args:
            callback_id: Идентификатор колбэка
            text: Текст уведомления, которое увидит пользователь
            
        Returns:
            Результат операции
        """
        # Параметры запроса с callback_id
        params = {
            "callback_id": callback_id
        }
        
        # Тело запроса с уведомлением
        data = {}
        if text:
            data["notification"] = text
        
        return self.client.request("POST", "/answers", params=params, data=data)
    
    def get_updates(self, allowed_updates: List[str], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Получает новые обновления от API через лонгполлинг
        
        Args:
            allowed_updates: Список типов обновлений, которые нужно получать
            extra: Дополнительные параметры запроса
            
        Returns:
            Список обновлений
        """
        params = extra or {}
        
        if allowed_updates:
            params["types"] = ",".join(allowed_updates)
        
        return self.client.request("GET", "/updates", params=params) 