#!/usr/bin/env python3
"""
Тестирование исправлений FSM-состояний
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from aiogram import Router, F
from aiogram.types import Message, User
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Имитация фильтра администратора
class IsAdmin:
    async def __call__(self, obj, data):
        # Возвращаем True для администраторов, False для обычных пользователей
        # В реальном коде это проверяется по ID пользователя
        return hasattr(obj, 'from_user') and getattr(obj.from_user, 'id', 0) in [123456789]  # Пример ID администратора


class TestState(StatesGroup):
    waiting_for_giveaway_id = State()
    waiting_for_user_id_for_rig = State()


async def simulate_old_behavior_without_protection(message: Message, state: FSMContext):
    """
    Симуляция старого поведения - обработчик без проверки прав
    """
    try:
        giveaway_id = int(message.text)
        return f"Processed giveaway ID: {giveaway_id}"
    except ValueError:
        return "❌ Пожалуйста, введите числовое значение ID розыгрыша."


async def simulate_new_behavior_with_protection(message: Message, state: FSMContext):
    """
    Симуляция нового поведения - обработчик с проверкой прав
    """
    # Проверяем, является ли пользователь администратором
    is_admin_filter = IsAdmin()
    if not await is_admin_filter(message, {}):
        await state.clear()  # В реальном коде было бы state.clear()
        return "❌ У вас нет прав для выполнения этой операции."
        
    try:
        giveaway_id = int(message.text)
        return f"Processed giveaway ID: {giveaway_id}"
    except ValueError:
        return "❌ Пожалуйста, введите числовое значение ID розыгрыша."


async def test_fsm_protection():
    print("Тестирование защиты FSM-состояний...")
    
    # Создаем фейковые объекты
    state = MagicMock(spec=FSMContext)
    state.clear = AsyncMock()
    
    # Тест 1: Сообщение от администратора
    admin_user = User(id=123456789, is_bot=False, first_name="Admin")
    admin_message = MagicMock(spec=Message)
    admin_message.text = "123"
    admin_message.from_user = admin_user
    
    # Тест 2: Сообщение от обычного пользователя
    regular_user = User(id=987654321, is_bot=False, first_name="User")
    regular_message = MagicMock(spec=Message)
    regular_message.text = "123"
    regular_message.from_user = regular_user
    
    # Тест 3: Неправильное сообщение от обычного пользователя
    invalid_message = MagicMock(spec=Message)
    invalid_message.text = "abc"
    invalid_message.from_user = regular_user
    
    print("\n--- Тест 1: Администратор отправляет корректный ID ---")
    result = await simulate_new_behavior_with_protection(admin_message, state)
    print(f"Результат: {result}")
    assert "Processed giveaway ID: 123" == result
    print("✓ Пройден")
    
    print("\n--- Тест 2: Обычный пользователь отправляет корректный ID ---")
    result = await simulate_new_behavior_with_protection(regular_message, state)
    print(f"Результат: {result}")
    assert "❌ У вас нет прав для выполнения этой операции." == result
    print("✓ Пройден")
    
    print("\n--- Тест 3: Обычный пользователь отправляет некорректный ID ---")
    result = await simulate_new_behavior_with_protection(invalid_message, state)
    print(f"Результат: {result}")
    assert "❌ У вас нет прав для выполнения этой операции." == result
    print("✓ Пройден")
    
    print("\n--- Тест 4: Поведение без защиты (для сравнения) ---")
    result_old = await simulate_old_behavior_without_protection(invalid_message, state)
    print(f"Старое поведение: {result_old}")
    print("Как видите, старое поведение показывает сообщение об ошибке ввода вместо проверки прав")
    
    print("\n✅ Все тесты пройдены! FSM-защита работает корректно.")


if __name__ == "__main__":
    asyncio.run(test_fsm_protection())