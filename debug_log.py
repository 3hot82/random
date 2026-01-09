import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

# Создаем специальный роутер для отладки
debug_router = Router()

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("debug_handler")

# Глобальный обработчик всех сообщений для отладки
@debug_router.message()
async def debug_all_messages(message: Message, state: FSMContext):
    current_state = await state.get_state()
    logger.info(f"DEBUG: Message received from user {message.from_user.id}")
    logger.info(f"DEBUG: Message text: {repr(message.text)}")
    logger.info(f"DEBUG: Current FSM state: {current_state}")
    logger.info(f"DEBUG: Message entities: {message.entities}")
    logger.info(f"DEBUG: Message args: {getattr(message, 'text', '')}")
    
    # Если сообщение пришло в состоянии, которое мы ожидаем, продолжаем стандартную обработку
    # Иначе - логируем возможную проблему
    if current_state:
        logger.warning(f"WARNING: Message received in FSM state {current_state}, user: {message.from_user.id}")
        logger.warning(f"WARNING: Message content: {message.text}")

# Глобальный обработчик всех callback_query для отладки
@debug_router.callback_query()
async def debug_all_callbacks(call: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    logger.info(f"DEBUG: Callback received from user {call.from_user.id}")
    logger.info(f"DEBUG: Callback data: {call.data}")
    logger.info(f"DEBUG: Current FSM state: {current_state}")
    
    if current_state:
        logger.warning(f"WARNING: Callback received in FSM state {current_state}, user: {call.from_user.id}")
        logger.warning(f"WARNING: Callback data: {call.data}")