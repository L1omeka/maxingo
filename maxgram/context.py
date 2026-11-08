"""
Контекст для обработки обновлений
"""

from typing import Dict, Any, Optional, List, Union
import logging
import time

from maxgram.types import Update, Message, UpdateType


class Context:
    """
    Контекст для обработки обновлений
    
    Содержит информацию о текущем обновлении и методы для работы с ним
    """
    
    def __init__(self, update: Dict[str, Any], api):
        """
        Инициализация контекста
        
        Args:
            update: Данные обновления
            api: API-клиент
        """
        self.update = update
        self.api = api
        
        # Логируем структуру обновления для диагностики
        logging.getLogger(__name__).debug(f"Context init with update: {update}")
        
        # Устанавливаем свойства в зависимости от типа обновления
        self.update_type = update.get('update_type')
        self.chat_id = update.get('chat_id')
        self.user = update.get('user')
        self.message = update.get('message')
        self.callback = update.get('callback')
        self.callback_id = update.get('callback_id')
        self.payload = update.get('payload')
        
        # Если callback_id не указан в корне обновления, но это callback-обновление
        if not self.callback_id and self.update_type == 'message_callback' and self.callback:
            self.callback_id = self.callback.get('callback_id')
            if not self.payload and 'payload' in self.callback:
                self.payload = self.callback.get('payload')
        
        # Если user не указан в корне обновления, извлекаем из message или callback
        if not self.user:
            if self.message and isinstance(self.message, dict) and 'sender' in self.message:
                self.user = self.message['sender']
            elif self.callback and isinstance(self.callback, dict) and 'user' in self.callback:
                self.user = self.callback['user']
        
        # Если chat_id не указан в корне обновления
        if not self.chat_id:
            # Попробуем получить из message -> recipient -> chat_id
            if self.message and isinstance(self.message, dict):
                if 'recipient' in self.message and 'chat_id' in self.message['recipient']:
                    self.chat_id = self.message['recipient']['chat_id']
                elif 'chat_id' in self.message:
                    self.chat_id = self.message.get('chat_id')
            elif self.callback and isinstance(self.callback, dict):
                if 'message' in self.callback and 'recipient' in self.callback['message']:
                    self.chat_id = self.callback['message']['recipient'].get('chat_id')
                elif 'chat_id' in self.callback:
                    self.chat_id = self.callback.get('chat_id')
    
    def reply(self, text: str, attachments: Optional[List[Dict[str, Any]]] = None, keyboard: Optional[Any] = None) -> Dict[str, Any]:
        """
        Отправляет ответ на текущее сообщение/обновление
        
        Args:
            text: Текст сообщения
            attachments: Вложения сообщения
            keyboard: Объект клавиатуры (будет добавлен к attachments)
            
        Returns:
            Информация об отправленном сообщении
        """
        chat_id = self._get_chat_id()
        if not chat_id:
            raise ValueError("Cannot reply without chat_id in context")
        
        # Подготавливаем вложения
        final_attachments = attachments.copy() if attachments else []
        
        # Если передана клавиатура, добавляем её как вложение
        if keyboard:
            if hasattr(keyboard, 'to_attachment'):
                final_attachments.append(keyboard.to_attachment())
            elif isinstance(keyboard, (list, tuple)):
                from maxgram.keyboards import InlineKeyboard
                final_attachments.append(InlineKeyboard(keyboard).to_attachment())
            elif isinstance(keyboard, dict):
                final_attachments.append(keyboard)
        
        return self.api.send_message(
            chat_id,
            text,
            final_attachments
        )
    
    def _get_chat_id(self) -> Optional[int]:
        """
        Получает идентификатор чата из контекста обновления
        
        Returns:
            Идентификатор чата или None если его нет
        """
        # Сначала пробуем использовать сохраненный chat_id
        if self.chat_id:
            return self.chat_id
            
        # Пробуем получить из message -> recipient -> chat_id
        if self.message and isinstance(self.message, dict):
            if 'recipient' in self.message and 'chat_id' in self.message['recipient']:
                return self.message['recipient']['chat_id']
            elif 'chat_id' in self.message:
                return self.message['chat_id']
        
        if self.user and isinstance(self.user, dict) and 'user_id' in self.user:
            return self.user['user_id']
                
        return None
    
    def answer_callback(self, text: Optional[str] = None) -> Dict[str, Any]:
        """
        Отправляет ответ на колбэк-запрос
        
        Args:
            text: Текст уведомления
            
        Returns:
            Результат операции
        """
        if not self.callback_id:
            raise ValueError("Cannot answer callback without callback_id in context")
            
        return self.api.answer_callback(
            self.callback_id,
            text
        )
    
    def reply_callback(self, text: str, attachments: Optional[List[Dict[str, Any]]] = None, 
                         keyboard: Optional[Any] = None, 
                         notification: Optional[str] = None,
                         is_current: bool = False) -> Dict[str, Any]:
        """
        Отправляет ответ на callback и новое сообщение пользователю или редактирует текущее
        
        Args:
            text: Текст сообщения для пользователя
            attachments: Вложения сообщения
            keyboard: Объект клавиатуры
            notification: Текст уведомления для callback (если не указан, будет сгенерирован)
            is_current: Если True, редактирует текущее сообщение вместо отправки нового
            
        Returns:
            Информация об отправленном или отредактированном сообщении
        """
        logger = logging.getLogger(__name__)
        
        # Если не указан текст уведомления, генерируем его на основе payload и timestamp
        if notification is None:
            notification = f"Обработка запроса {self.payload}_{int(time.time())}"
        
        # Отправляем ответ на callback
        if self.callback_id:
            try:
                self.answer_callback(notification)
            except Exception as e:
                logger.warning(f"Failed to answer callback: {e}")
        
        # Подготавливаем вложения
        final_attachments = attachments.copy() if attachments else []
        
        # Если передана клавиатура, добавляем её как вложение
        if keyboard:
            if hasattr(keyboard, 'to_attachment'):
                final_attachments.append(keyboard.to_attachment())
            elif isinstance(keyboard, (list, tuple)):
                from maxgram.keyboards import InlineKeyboard
                final_attachments.append(InlineKeyboard(keyboard).to_attachment())
            elif isinstance(keyboard, dict):
                final_attachments.append(keyboard)
        
        # Если нужно редактировать текущее сообщение
        if is_current:
            logger.debug(f"Attempting to edit message, callback structure: {self.update}")
            
            # Пытаемся получить ID сообщения из разных мест структуры обновления
            message_id = None
            
            # Проверяем наличие сообщения в колбэке
            if 'callback' in self.update and 'message' in self.update['callback']:
                callback_message = self.update['callback']['message']
                if 'body' in callback_message and 'mid' in callback_message['body']:
                    message_id = callback_message['body']['mid']
                elif 'message_id' in callback_message:
                    message_id = callback_message['message_id']
            
            # Если сообщение не найдено в колбэке, проверяем корень обновления
            if not message_id and 'message' in self.update:
                if 'body' in self.update['message'] and 'mid' in self.update['message']['body']:
                    message_id = self.update['message']['body']['mid']
                elif 'message_id' in self.update['message']:
                    message_id = self.update['message']['message_id']
            
            if message_id:
                try:
                    return self.api.edit_message(message_id, text, final_attachments)
                except Exception as e:
                    logger.error(f"Error editing message: {e}")
                    return self.reply(text, attachments, keyboard)
            else:
                return self.reply(text, attachments, keyboard)
        else:
            return self.reply(text, attachments, keyboard)
