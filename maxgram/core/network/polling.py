"""
Модуль для получения обновлений от API Max через лонгполлинг
"""

import asyncio
import logging
import time
from typing import Callable, List, Optional, Dict, Any

from maxgram.types import Update, UpdateType

logger = logging.getLogger(__name__)


class Polling:
    """Класс для получения обновлений через лонгполлинг"""
    
    def __init__(self, api, allowed_updates: Optional[List[str]] = None):
        """
        Инициализация лонгполлинга
        
        Args:
            api: API-клиент
            allowed_updates: Список типов обновлений, которые нужно получать
        """
        self.api = api
        self.allowed_updates = allowed_updates
        self.is_running = False
        self.marker = None
    
    def stop(self):
        """Остановить лонгполлинг"""
        self.is_running = False
    
    async def loop(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Запускает цикл лонгполлинга
        
        Args:
            handler: Функция-обработчик обновлений
        """
        self.is_running = True
        
        logger.info("Starting long polling loop")
        
        while self.is_running:
            try:
                updates_data = await self._get_updates()
                
                # Получаем и обновляем marker для следующего запроса
                if "marker" in updates_data:
                    self.marker = updates_data["marker"]
                
                updates = updates_data.get("updates", [])
                
                for update in updates:
                    try:
                        logger.info(f"Получено обновление: {update.get('update_type')}")
                        handler(update)
                    except Exception as e:
                        logger.error(f"Ошибка обработки обновления: {e}", exc_info=True)
                
            except Exception as e:
                err_str = str(e)
                if "Read timed out" in err_str:
                    # Штатный таймаут лонг-поллинга при отсутствии новых событий
                    continue
                logger.error(f"Ошибка получения обновлений: {e}")
                # Пауза перед повторной попыткой при реальной ошибке
                await asyncio.sleep(2)
    
    async def _get_updates(self) -> Dict[str, Any]:
        """
        Получает список обновлений от API
        
        Returns:
            Данные ответа от API, включая обновления и marker
        """
        params = {"timeout": 20}
        
        # Добавляем marker, если он есть
        if self.marker is not None:
            params["marker"] = self.marker
        
        updates_data = await asyncio.to_thread(
            self.api.get_updates,
            self.allowed_updates or [],
            params
        )
        
        return updates_data
