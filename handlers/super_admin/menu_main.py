from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from filters.is_admin import IsAdmin
from database.models.user import User
from database.models.giveaway import Giveaway

router = Router()

# В этом файле остаются только callback-обработчики, связанные с меню администратора
# Команда /admin теперь обрабатывается в новой админ-панели для суперадминистраторов