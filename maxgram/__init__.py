"""
Python Max Bot API Client

Это библиотека для создания ботов для мессенджера Max
"""

from maxgram.bot import Bot
from maxgram.api import Api
from maxgram.context import Context
from maxgram.keyboards import InlineKeyboard

__version__ = "0.1.4"
__all__ = ["Bot", "Api", "Context", "InlineKeyboard"] 