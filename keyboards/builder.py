from enum import Enum
from typing import Optional, List, Union
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class ButtonType(Enum):
    """Типы кнопок для унификации создания клавиатур"""
    CALLBACK = "callback"
    URL = "url"
    LOGIN = "login"


class KeyboardBuilder:
    """
    Универсальный строитель клавиатур с возможностью быстрого создания
    часто используемых типов клавиатур
    """
    
    def __init__(self):
        self.builder = InlineKeyboardBuilder()
    
    def add_button(
        self, 
        text: str, 
        button_type: ButtonType = ButtonType.CALLBACK, 
        data: Optional[str] = None, 
        url: Optional[str] = None
    ) -> 'KeyboardBuilder':
        """Добавление кнопки к клавиатуре"""
        if button_type == ButtonType.CALLBACK:
            if data is None:
                raise ValueError("For CALLBACK buttons, 'data' parameter is required")
            self.builder.button(text=text, callback_data=data)
        elif button_type == ButtonType.URL:
            if url is None:
                raise ValueError("For URL buttons, 'url' parameter is required")
            self.builder.button(text=text, url=url)
        elif button_type == ButtonType.LOGIN:
            if url is None:
                raise ValueError("For LOGIN buttons, 'url' parameter is required")
            # Note: login_url is not supported in InlineKeyboardBuilder directly
            # We'll need to handle this differently if needed
            pass
        return self
    
    def add_buttons_row(self, *buttons) -> 'KeyboardBuilder':
        """Добавление нескольких кнопок в один ряд"""
        for button in buttons:
            if isinstance(button, tuple) and len(button) == 3:
                text, button_type, data_or_url = button
                self.add_button(text, button_type, data_or_url if button_type == ButtonType.CALLBACK else None, 
                               data_or_url if button_type == ButtonType.URL else None)
            elif isinstance(button, dict):
                self.add_button(**button)
        return self
    
    def add_navigation_buttons(
        self, 
        back_callback: Optional[str] = None, 
        home_callback: Optional[str] = None,
        custom_buttons: Optional[List[tuple]] = None
    ) -> 'KeyboardBuilder':
        """Добавление навигационных кнопок"""
        nav_buttons = []
        if custom_buttons:
            nav_buttons.extend(custom_buttons)
        if back_callback:
            nav_buttons.append(("🔙 Назад", ButtonType.CALLBACK, back_callback))
        if home_callback:
            nav_buttons.append(("🏠 Главное меню", ButtonType.CALLBACK, home_callback))
        
        if nav_buttons:
            self.add_buttons_row(*nav_buttons)
        return self
    
    def adjust(self, *sizes: int) -> 'KeyboardBuilder':
        """Настройка размеров рядов кнопок"""
        self.builder.adjust(*sizes)
        return self
    
    def build(self) -> InlineKeyboardMarkup:
        """Получение готовой клавиатуры"""
        return self.builder.as_markup()


class StandardKeyboards:
    """Класс для создания стандартных клавиатур"""
    
    @staticmethod
    def confirmation_keyboard(
        confirm_callback: str, 
        cancel_callback: str, 
        confirm_text: str = "✅ Да", 
        cancel_text: str = "❌ Нет",
        back_callback: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        """Стандартная клавиатура подтверждения"""
        builder = KeyboardBuilder()
        builder.add_buttons_row(
            (confirm_text, ButtonType.CALLBACK, confirm_callback),
            (cancel_text, ButtonType.CALLBACK, cancel_callback)
        )
        if back_callback:
            builder.add_button("🔙 Назад", ButtonType.CALLBACK, back_callback)
        return builder.adjust(2).build()
    
    @staticmethod
    def pagination_keyboard(
        current_page: int, 
        total_pages: int, 
        base_callback: str,
        back_callback: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        """Стандартная клавиатура с пагинацией"""
        if total_pages <= 1:
            if back_callback:
                return KeyboardBuilder().add_button("🔙 Назад", ButtonType.CALLBACK, back_callback).build()
            return InlineKeyboardMarkup()
        
        builder = KeyboardBuilder()
        
        # Кнопки навигации
        nav_buttons = []
        if current_page > 0:
            nav_buttons.append(("⬅️", ButtonType.CALLBACK, f"{base_callback}:{current_page - 1}"))
        
        nav_buttons.append((f"{current_page + 1}/{total_pages}", ButtonType.CALLBACK, "ignore"))
        
        if current_page < total_pages - 1:
            nav_buttons.append(("➡️", ButtonType.CALLBACK, f"{base_callback}:{current_page + 1}"))
        
        builder.add_buttons_row(*nav_buttons)
        
        if back_callback:
            builder.add_button("🔙 Назад", ButtonType.CALLBACK, back_callback)
        
        return builder.build()
    
    @staticmethod
    def choice_keyboard(
        choices: List[tuple],  # (text, callback_data)
        back_callback: Optional[str] = None,
        columns: int = 1
    ) -> InlineKeyboardMarkup:
        """Клавиатура для выбора из списка опций"""
        builder = KeyboardBuilder()
        
        for text, callback_data in choices:
            builder.add_button(text, ButtonType.CALLBACK, callback_data)
        
        if back_callback:
            builder.add_button("🔙 Назад", ButtonType.CALLBACK, back_callback)
        
        # Adjust buttons in rows according to columns
        if len(choices) % columns == 0:
            row_sizes = [columns] * (len(choices) // columns)
        else:
            row_sizes = [columns] * (len(choices) // columns) + [len(choices) % columns]
        
        if back_callback:
            row_sizes.append(1)  # For back button
            
        return builder.adjust(*row_sizes).build()
    
    @staticmethod
    def url_keyboard(
        buttons: List[tuple],  # (text, url)
        back_callback: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        """Клавиатура с URL-кнопками"""
        builder = KeyboardBuilder()
        
        for text, url in buttons:
            builder.add_button(text, ButtonType.URL, url=url)
        
        if back_callback:
            builder.add_button("🔙 Назад", ButtonType.CALLBACK, back_callback)
        
        return builder.build()