"""
Модуль для работы с клавиатурами в Max API
"""

from typing import List, Dict, Any, Union, Optional


class InlineKeyboard:
    """
    Класс для удобного создания inline-клавиатур в Max

    Пример использования:
    ```python
    keyboard = InlineKeyboard(
        [
            {"text": "Кнопка 1", "callback": "button1"},
        ],
        [ 
            {"text": "Кнопка 2", "callback": "button2"},
            {"text": "Кнопка 3", "callback": "button3"}
        ],
        [
            {"text": "Открыть ссылку", "url": "https://max.ru"}
        ]
    )
    ```
    """

    def __init__(self, *rows: Union[List[Dict[str, Any]], List[List[Dict[str, Any]]]]):
        """
        Создает inline-клавиатуру из строк кнопок

        Args:
            *rows: Списки словарей, описывающих кнопки в каждой строке
                  Поддерживает как передачу строк через запятую: InlineKeyboard(row1, row2),
                  так и готовый список строк: InlineKeyboard([row1, row2]).
        """
        if len(rows) == 1 and isinstance(rows[0], (list, tuple)):
            if rows[0] and isinstance(rows[0][0], (list, tuple)):
                self.rows = list(rows[0])
            else:
                self.rows = [list(rows[0])]
        else:
            self.rows = list(rows)
        
    def to_attachment(self) -> Dict[str, Any]:
        """
        Преобразует клавиатуру в формат вложения для отправки API

        Returns:
            Словарь с параметрами клавиатуры для отправки в API
        """
        buttons = []
        
        for row in self.rows:
            button_row = []
            
            for button in row:
                if not isinstance(button, dict):
                    continue
                btn_data = {"text": str(button.get("text", ""))}
                
                # Поддерживаем callback, callback_data и payload
                cb_payload = button.get("callback") or button.get("callback_data") or button.get("payload")
                if cb_payload is not None:
                    btn_data["type"] = "callback"
                    btn_data["payload"] = str(cb_payload)
                elif "url" in button:
                    btn_data["type"] = "link"
                    btn_data["url"] = str(button["url"])
                elif "chat_title" in button:
                    btn_data["type"] = "chat"
                    btn_data["chat_title"] = str(button["chat_title"])
                    if "chat_description" in button:
                        btn_data["chat_description"] = str(button["chat_description"])
                else:
                    btn_data["type"] = button.get("type", "callback")
                    btn_data["payload"] = str(button.get("payload", ""))
                
                button_row.append(btn_data)
            
            if button_row:
                buttons.append(button_row)
        
        return {
            "type": "inline_keyboard",
            "payload": {
                "buttons": buttons
            }
        }
