"""
Типы данных для API Max
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

# Типы событий (обновлений)
class UpdateType:
    MESSAGE_CREATED = "message_created"
    MESSAGE_CALLBACK = "message_callback"
    BOT_STARTED = "bot_started"
    MESSAGE_EDITED = "message_edited"
    MESSAGE_DELETED = "message_deleted"
    MESSAGE_CHAT_CREATED = "message_chat_created"

# Базовые модели
class User(BaseModel):
    user_id: int = Field(..., description="Идентификатор пользователя")
    name: str = Field(..., description="Отображаемое имя пользователя")
    username: Optional[str] = Field(None, description="Уникальное публичное имя пользователя")
    is_bot: bool = Field(..., description="Признак бота")
    last_activity_time: Optional[int] = Field(None, description="Время последней активности пользователя")
    description: Optional[str] = Field(None, description="Описание пользователя")
    avatar_url: Optional[str] = Field(None, description="URL аватара")
    full_avatar_url: Optional[str] = Field(None, description="URL полноразмерного аватара")

class BotCommand(BaseModel):
    name: str = Field(..., description="Название команды без слеша")
    description: str = Field(..., description="Описание команды")

class BotInfo(User):
    commands: Optional[List[BotCommand]] = Field(None, description="Список команд бота")

class MessageBody(BaseModel):
    text: str = Field(..., description="Текст сообщения")

class MessageAttachment(BaseModel):
    type: str = Field(..., description="Тип вложения")
    payload: Dict[str, Any] = Field(..., description="Данные вложения")

class Message(BaseModel):
    message_id: str = Field(..., description="Уникальный идентификатор сообщения")
    chat_id: int = Field(..., description="Идентификатор чата")
    sender: User = Field(..., description="Отправитель сообщения")
    body: MessageBody = Field(..., description="Тело сообщения")
    timestamp: int = Field(..., description="Время отправки в Unix формате (миллисекунды)")
    attachments: Optional[List[MessageAttachment]] = Field(None, description="Вложения сообщения")

class Update(BaseModel):
    update_type: str = Field(..., description="Тип обновления")
    timestamp: int = Field(..., description="Время обновления")
    chat_id: Optional[int] = Field(None, description="Идентификатор чата")
    user: Optional[User] = Field(None, description="Пользователь, связанный с обновлением")
    message: Optional[Message] = Field(None, description="Сообщение, связанное с обновлением")
    callback_id: Optional[str] = Field(None, description="Идентификатор обратного вызова")
    payload: Optional[str] = Field(None, description="Полезные данные для обработки") 