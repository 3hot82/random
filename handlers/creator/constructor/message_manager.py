from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class MessageManager:
    """Класс для управления сообщениями в конструкторе"""
    
    def __init__(self):
        self.preview_message_id = None      # ID сообщения предпросмотра (пост)
        self.control_message_id = None      # ID сообщения управления (кнопки)
        self.instruction_message_id = None  # ID сообщения с инструкцией (Шаг 1)
        self.temp_messages = []             # Временные сообщения (ошибки, диалоги ввода)
    
    def set_preview_message(self, message: types.Message):
        if message:
            self.preview_message_id = message.message_id
    
    def set_control_message(self, message: types.Message):
        if message:
            self.control_message_id = message.message_id
        
    def set_instruction_message(self, message: types.Message):
        if message:
            self.instruction_message_id = message.message_id

    def add_temp_message(self, message: types.Message):
        if message:
            self.temp_messages.append(message.message_id)
    
    async def delete_all(self, bot: Bot, chat_id: int):
        """Удаляет ВСЕ сообщения интерфейса конструктора"""
        ids_to_delete = []
        
        if self.preview_message_id: ids_to_delete.append(self.preview_message_id)
        if self.control_message_id: ids_to_delete.append(self.control_message_id)
        if self.instruction_message_id: ids_to_delete.append(self.instruction_message_id)
        ids_to_delete.extend(self.temp_messages)
        
        # Удаляем уникальные ID, чтобы не спамить запросами
        for msg_id in set(ids_to_delete):
            try:
                await bot.delete_message(chat_id, msg_id)
            except Exception:
                # Сообщение уже удалено или слишком старое
                pass
        
        # Очищаем память
        self.clear()

    def clear(self):
        self.preview_message_id = None
        self.control_message_id = None
        self.instruction_message_id = None
        self.temp_messages = []
    
    def to_dict(self) -> dict:
        return {
            'preview_message_id': self.preview_message_id,
            'control_message_id': self.control_message_id,
            'instruction_message_id': self.instruction_message_id,
            'temp_messages': self.temp_messages
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        manager = cls()
        manager.preview_message_id = data.get('preview_message_id')
        manager.control_message_id = data.get('control_message_id')
        manager.instruction_message_id = data.get('instruction_message_id')
        manager.temp_messages = data.get('temp_messages', [])
        return manager

async def get_message_manager(state: FSMContext) -> MessageManager:
    data = await state.get_data()
    if 'message_manager_data' not in data:
        manager = MessageManager()
        await state.update_data(message_manager_data=manager.to_dict())
        return manager
    return MessageManager.from_dict(data['message_manager_data'])

async def update_message_manager(state: FSMContext, manager: MessageManager):
    await state.update_data(message_manager_data=manager.to_dict())