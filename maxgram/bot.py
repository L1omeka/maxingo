"""
Класс бота для работы с API Max
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Union, Type
import functools
import re
import json

from maxgram.api import Api
from maxgram.context import Context
from maxgram.types import UpdateType
from maxgram.core.network.polling import Polling

logger = logging.getLogger(__name__)

# Типы обработчиков
HandlerFunc = Callable[[Context], None]


class Bot:
    """
    Основной класс для работы с ботом
    
    Предоставляет методы для обработки обновлений и отправки ответов
    """
    
    def __init__(self, token: str, client_options: Optional[Dict[str, Any]] = None):
        """
        Инициализация бота
        
        Args:
            token: Токен доступа бота
            client_options: Дополнительные настройки клиента
        """
        self.api = Api(token, client_options)
        self.handlers = {
            "update": [],  # Общие обработчики для всех типов обновлений
            UpdateType.MESSAGE_CREATED: [],
            UpdateType.MESSAGE_CALLBACK: [],
            UpdateType.BOT_STARTED: [],
            UpdateType.MESSAGE_EDITED: [],
            UpdateType.MESSAGE_DELETED: [],
            UpdateType.MESSAGE_CHAT_CREATED: [],
        }
        self.command_handlers = {}  # Обработчики команд: {"command": [handler1, handler2, ...]}
        self.text_handlers = []  # Обработчики текста: [(pattern, handler), ...]
        
        self.polling = None
        self.is_running = False
    
    def on(self, update_type: str):
        """
        Декоратор для регистрации обработчика определенного типа обновлений
        
        Args:
            update_type: Тип обновления (см. UpdateType)
        """
        def decorator(func: HandlerFunc):
            self.handlers.setdefault(update_type, []).append(func)
            return func
        return decorator
    
    def command(self, *command_names: str):
        """
        Декоратор для регистрации обработчика команды (или нескольких команд)
        
        Args:
            *command_names: Имя или список имён команд (без слеша или со слешем)
        """
        def decorator(func: HandlerFunc):
            for name in command_names:
                clean_name = str(name).strip().lstrip("/").lower()
                self.command_handlers.setdefault(clean_name, []).append(func)
            return func
        return decorator
    
    def hears(self, pattern: str):
        """
        Декоратор для регистрации обработчика текстовых сообщений по шаблону
        
        Args:
            pattern: Шаблон текста (точное совпадение или регулярное выражение)
        """
        def decorator(func: HandlerFunc):
            self.text_handlers.append((pattern, func))
            return func
        return decorator
    
    async def start(self, allowed_updates: Optional[List[str]] = None):
        """
        Запускает получение обновлений
        
        Args:
            allowed_updates: Список типов обновлений, которые нужно получать
        """
        if self.is_running:
            logger.warning("Bot is already running")
            return
        
        self.is_running = True
        
        self.polling = Polling(self.api, allowed_updates)
        
        await self.polling.loop(self._process_update)

    def run(self, allowed_updates: Optional[List[str]] = None):
        """Обертка для запуска корутины"""
        asyncio.run(self.start(allowed_updates))
    
    def stop(self):
        """Останавливает получение обновлений"""
        if not self.is_running:
            logger.warning("Bot is not running")
            return
        
        if self.polling:
            self.polling.stop()
        
        self.is_running = False
    
    def _process_update(self, update: Dict[str, Any]):
        """
        Обрабатывает входящее обновление
        
        Args:
            update: Данные обновления
        """
        try:
            # Логируем структуру обновления для диагностики
            logger.info(f"Received update: {json.dumps(update, ensure_ascii=False)}")
            
            update_type = update.get("update_type")
            
            context = Context(update, self.api)
            
            # Вызываем общие обработчики
            for handler in self.handlers.get("update", []):
                handler(context)
            
            # Вызываем обработчики для конкретного типа обновления
            for handler in self.handlers.get(update_type, []):
                handler(context)
            
            # Обрабатываем сообщения особым образом (команды и текстовые шаблоны)
            if update_type == UpdateType.MESSAGE_CREATED and "message" in update:
                self._process_message(context)
                
        except Exception as e:
            self.handle_error(e, update)
    
    def _process_message(self, context: Context):
        """
        Обрабатывает входящее сообщение
        
        Args:
            context: Контекст обновления
        """
        if not context.message:
            return
            
        message_body = context.message.get("body", {})
        if not message_body or "text" not in message_body:
            return
            
        text = str(message_body["text"]).strip()
        
        # Проверяем, является ли сообщение командой
        if text.startswith("/"):
            command_parts = text[1:].split(" ", 1)
            raw_command = command_parts[0]
            # Убираем имя бота (@bot_name), если клиент отправил /command@botname
            command = raw_command.split("@")[0].lower()
            
            logger.info(f"Получена команда: /{command}")
            
            # Вызываем обработчики команды
            handlers = self.command_handlers.get(command, [])
            if handlers:
                for handler in handlers:
                    handler(context)
                logger.info(f"Обработчик команды /{command} выполнен успешно")
                return  # Команда обработана, текстовые триггеры пропускаем
            else:
                logger.warning(f"Не найден обработчик для команды: /{command}")
                # Если зарегистрирован обработчик fallback_command, вызываем его
                fallback_handlers = self.command_handlers.get("__fallback__", [])
                for handler in fallback_handlers:
                    handler(context)
                return
                
        # Проверяем обработчики текста
        for pattern, handler in self.text_handlers:
            if pattern == text or re.search(pattern, text):
                logger.info(f"Сработал текстовый триггер: {pattern}")
                handler(context)
                handler(context)
                
    def handle_error(self, error: Exception, update: Dict[str, Any]):
        """
        Обрабатывает ошибку при обработке обновления
        
        Args:
            error: Ошибка
            update: Данные обновления
        """
        logger.error(f"Error while processing update: {error}", exc_info=True)
        
    def catch(self, handler: Callable[[Exception, Dict[str, Any]], None]):
        """
        Устанавливает пользовательский обработчик ошибок
        
        Args:
            handler: Функция-обработчик ошибок
        """
        self.handle_error = handler
        return self
        
    def set_my_commands(self, commands: Dict[str, str]) -> Dict[str, Any]:
        """
        Устанавливает команды для бота в удобном формате
        
        Args:
            commands: Словарь команд в формате {"command": "description"}
            
        Returns:
            Результат запроса PATCH /me
        """
        commands_list = [{"name": name, "description": description} for name, description in commands.items()]
        return self.api.set_my_commands(commands_list)
