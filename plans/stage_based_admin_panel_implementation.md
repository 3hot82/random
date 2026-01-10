# Поэтапная реализация админ-панели для бота розыгрышей

## ЭТАП 1: Подготовительный этап

### Цель этапа:
Подготовить инфраструктуру для реализации админ-панели, создать необходимые модели данных и сервисы.

### Задачи:
1. **Создание моделей данных для хранения информации об админ-действиях**
   - Модель `AdminLog` для логирования действий администраторов
   - Модель `Broadcast` для хранения информации о рассылках
   - Модель `ScheduledBroadcast` для отложенных рассылок

```python
from sqlalchemy import Integer, String, DateTime, Boolean, func, JSON, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime

class AdminLog(Base):
    __tablename__ = "admin_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String)
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    details: Mapped[dict | None] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())

class Broadcast(Base):
    __tablename__ = "broadcasts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_text: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    video_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    document_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer)

class ScheduledBroadcast(Base):
    __tablename__ = "scheduled_broadcasts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_text: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    video_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    document_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    created_by: Mapped[int] = mapped_column(Integer)
```

2. **Настройка системы логирования**
   - Настройка файлового логирования с ротацией
   - Настройка логирования для админ-действий

```python
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    # Создаем директорию для логов, если она не существует
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Настройка формата логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler(
        'logs/admin_panel.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Настройка логгеров для конкретных модулей
    admin_logger = logging.getLogger('admin')
    admin_logger.setLevel(logging.INFO)
    
    broadcast_logger = logging.getLogger('broadcast')
    broadcast_logger.setLevel(logging.INFO)
```

3. **Создание сервисов для работы с каждым разделом**
   - Сервис статистики
   - Сервис управления пользователями
   - Сервис управления розыгрышами
   - Сервис рассылок

```python
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from database.models.user import User
from database.models.giveaway import Giveaway
from database.models.participant import Participant

class StatisticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_general_stats(self) -> dict:
        """
        Получение общей статистики
        """
        # Всего пользователей
        total_users = await self.session.scalar(select(func.count(User.user_id)))
        
        # Активных розыгрышей
        active_giveaways = await self.session.scalar(
            select(func.count(Giveaway.id)).where(Giveaway.status == "active")
        )
        
        # Всего участий
        total_participations = await self.session.scalar(
            select(func.count(Participant.user_id))
        )
        
        # Пользователей без username (потенциально боты)
        potential_bots = await self.session.scalar(
            select(func.count(User.user_id)).where(User.username.is_(None))
        )
        
        return {
            "total_users": total_users,
            "active_giveaways": active_giveaways,
            "total_participations": total_participations,
            "potential_bots": potential_bots
        }
    
    async def get_user_growth_stats(self) -> dict:
        """
        Получение статистики роста пользователей
        """
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        new_today = await self.session.scalar(
            select(func.count(User.user_id)).where(
                func.date(User.created_at) == today
            )
        )
        
        new_week = await self.session.scalar(
            select(func.count(User.user_id)).where(
                User.created_at >= week_ago
            )
        )
        
        new_month = await self.session.scalar(
            select(func.count(User.user_id)).where(
                User.created_at >= month_ago
            )
        )
        
        return {
            "new_today": new_today,
            "new_week": new_week,
            "new_month": new_month
        }
```

### Ожидаемый результат:
- Созданы все необходимые модели данных
- Настроена система логирования
- Созданы основные сервисы с базовой функциональностью

---

## ЭТАП 2: Реализация базовой структуры

### Цель этапа:
Создать основную структуру админ-панели с базовыми элементами интерфейса и проверкой прав администратора.

### Задачи:
1. **Создание роутеров для админ-панели**
   - Роутер для команд администратора
   - Роутер для коллбэков админ-панели

```python
from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery

class IsAdmin(Filter):
    def __init__(self):
        super().__init__()
    
    async def __call__(self, obj: Message | CallbackQuery, config) -> bool:
        user_id = obj.from_user.id if hasattr(obj, 'from_user') else obj.message.from_user.id
        return user_id in config.ADMIN_IDS

# Инициализация роутеров
admin_router = Router()
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())

@admin_router.message(lambda m: m.text == "/admin")
async def admin_panel(message: Message, config):
    keyboard = get_main_admin_menu_keyboard()
    await message.answer("🔒 Админ-панель", reply_markup=keyboard)
```

2. **Реализация проверки прав администратора**
   - Создание фильтра проверки администраторских прав
   - Логирование попыток доступа к админ-панели

```python
from functools import wraps
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Filter
import logging

logger = logging.getLogger('admin')

class IsAdmin(Filter):
    def __init__(self):
        super().__init__()
    
    async def __call__(self, obj: Message | CallbackQuery, config) -> bool:
        user_id = obj.from_user.id if hasattr(obj, 'from_user') else obj.message.from_user.id
        
        is_admin = user_id in config.ADMIN_IDS
        if is_admin:
            logger.info(f"Admin {user_id} accessed admin panel")
        else:
            logger.warning(f"Unauthorized access attempt to admin panel by user {user_id}")
        
        return is_admin
```

3. **Создание базовых клавиатур и сообщений**
   - Главное меню админ-панели
   - Клавиатуры для каждого раздела

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Основное меню админ-панели
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="admin_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👥 Пользователи",
            callback_data="admin_users"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎁 Розыгрыши",
            callback_data="admin_giveaways"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📢 Рассылка",
            callback_data="admin_broadcast"
        )
    )
    
    return builder.as_markup()

def get_back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой "Назад в главное меню"
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад в меню",
            callback_data="admin_main_menu"
        )
    )
    return builder.as_markup()
```

### Ожидаемый результат:
- Созданы роутеры с фильтрами для администраторов
- Реализована проверка прав доступа
- Созданы базовые клавиатуры для навигации по админ-панели

---

## ЭТАП 3: Реализация раздела "Статистика"

### Цель этапа:
Реализовать полнофункциональный раздел статистики с возможностью просмотра различных метрик.

### Задачи:
1. **Реализация подразделов статистики**
   - Общая статистика
   - Рост пользователей
   - Премиум статистика
   - Статистика розыгрышей
   - Статистика участий

```python
from aiogram.types import CallbackQuery
from aiogram import F

@admin_router.callback_query(F.data == "admin_stats")
async def show_stats_menu(callback: CallbackQuery):
    keyboard = get_stats_menu_keyboard()
    await callback.message.edit_text("📊 Меню статистики", reply_markup=keyboard)

def get_stats_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Общая статистика",
            callback_data="admin_general_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📈 Рост пользователей",
            callback_data="admin_user_growth"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⭐ Премиум статистика",
            callback_data="admin_premium_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎮 Розыгрыши",
            callback_data="admin_giveaway_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎯 Участия",
            callback_data="admin_participation_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_main_menu"
        )
    )
    
    return builder.as_markup()

@admin_router.callback_query(F.data == "admin_general_stats")
async def show_general_stats(callback: CallbackQuery, session: AsyncSession):
    service = StatisticsService(session)
    stats = await service.get_general_stats()
    
    message_text = f"""
📊 Общая статистика:
👥 Всего пользователей: {stats['total_users']}
🎁 Активных розыгрышей: {stats['active_giveaways']}
🎫 Всего участий: {stats['total_participations']}
🤖 Потенциальных ботов: {stats['potential_bots']}
    """.strip()
    
    keyboard = get_back_to_stats_menu_keyboard()
    await callback.message.edit_text(message_text, reply_markup=keyboard)

def get_back_to_stats_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к статистике",
            callback_data="admin_stats"
        )
    )
    return builder.as_markup()
```

2. **Оптимизация производительности**
   - Добавление индексов для часто используемых полей
   - Реализация кэширования статистических данных
   - Использование асинхронных запросов

```python
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta

class StatsCache:
    def __init__(self, ttl: int = 300):  # 5 минут
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        self.ttl = timedelta(seconds=ttl)
    
    def get(self, key: str):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        self.cache[key] = (value, datetime.now())

class StatisticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache = StatsCache()
    
    async def get_general_stats(self) -> dict:
        cache_key = "general_stats"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Всего пользователей
        total_users = await self.session.scalar(select(func.count(User.user_id)))
        
        # Активных розыгрышей
        active_giveaways = await self.session.scalar(
            select(func.count(Giveaway.id)).where(Giveaway.status == "active")
        )
        
        # Всего участий
        total_participations = await self.session.scalar(
            select(func.count(Participant.user_id))
        )
        
        # Пользователей без username (потенциально боты)
        potential_bots = await self.session.scalar(
            select(func.count(User.user_id)).where(User.username.is_(None))
        )
        
        result = {
            "total_users": total_users,
            "active_giveaways": active_giveaways,
            "total_participations": total_participations,
            "potential_bots": potential_bots
        }
        
        self.cache.set(cache_key, result)
        return result
```

3. **Добавление временных фильтров**
   - Возможность выбора временных интервалов для просмотра статистики
   - Реализация возможности экспорта статистики

```python
@admin_router.callback_query(F.data.startswith("admin_general_stats_"))
async def show_general_stats_filtered(callback: CallbackQuery, session: AsyncSession):
    # Получаем временной период из callback_data
    period = callback.data.split("_")[-1]
    
    service = StatisticsService(session)
    if period == "today":
        stats = await service.get_general_stats_for_period(today_only=True)
    elif period == "week":
        stats = await service.get_general_stats_for_period(weeks=1)
    elif period == "month":
        stats = await service.get_general_stats_for_period(months=1)
    else:
        stats = await service.get_general_stats()
    
    message_text = f"""
📊 Общая статистика ({period}):
👥 Всего пользователей: {stats['total_users']}
🎁 Активных розыгрышей: {stats['active_giveaways']}
🎫 Всего участий: {stats['total_participations']}
🤖 Потенциальных ботов: {stats['potential_bots']}
    """.strip()
    
    keyboard = get_back_to_stats_menu_keyboard()
    await callback.message.edit_text(message_text, reply_markup=keyboard)

def get_stats_filter_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="День",
            callback_data="admin_general_stats_today"
        ),
        InlineKeyboardButton(
            text="Неделя",
            callback_data="admin_general_stats_week"
        ),
        InlineKeyboardButton(
            text="Месяц",
            callback_data="admin_general_stats_month"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_general_stats"
        )
    )
    
    return builder.as_markup()
```

### Ожидаемый результат:
- Полностью реализован раздел статистики с подразделами
- Добавлена оптимизация производительности через кэширование
- Реализована возможность фильтрации по времени

---

## ЭТАП 4: Реализация раздела "Пользователи"

### Цель этапа:
Создать полнофункциональный раздел управления пользователями с возможностью поиска, просмотра информации и изменения статусов.

### Задачи:
1. **Реализация поиска пользователей**
   - Поиск по ID, username и имени
   - Поиск по критериям (премиум/обычный, дата регистрации и т.д.)

```python
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import F

class UserSearchState(StatesGroup):
    waiting_for_search_query = State()

@admin_router.callback_query(F.data == "admin_users")
async def show_users_menu(callback: CallbackQuery):
    keyboard = get_users_menu_keyboard()
    await callback.message.edit_text("👥 Меню пользователей", reply_markup=keyboard)

def get_users_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔍 Поиск пользователя",
            callback_data="admin_search_user"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Список пользователей",
            callback_data="admin_list_users_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_main_menu"
        )
    )
    
    return builder.as_markup()

@admin_router.callback_query(F.data == "admin_search_user")
async def start_user_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSearchState.waiting_for_search_query)
    keyboard = get_cancel_search_keyboard()
    await callback.message.edit_text("🔍 Введите ID, @username или имя пользователя:", reply_markup=keyboard)

@admin_router.message(UserSearchState.waiting_for_search_query)
async def process_user_search(message: Message, state: FSMContext, session: AsyncSession):
    search_query = message.text.strip()
    
    service = UserService(session)
    users = await service.search_users(search_query)
    
    if not users:
        await message.answer("❌ Пользователи не найдены.")
        await state.clear()
        return
    
    if len(users) == 1:
        # Если найден один пользователь, показываем его информацию
        user_info = await service.get_user_detailed_info(users[0].user_id)
        keyboard = get_user_detail_menu_keyboard(user_info["user"].user_id)
        await message.answer(format_user_info(user_info), reply_markup=keyboard)
    else:
        # Если найдено несколько пользователей, показываем список
        keyboard = get_user_search_results_keyboard(users)
        await message.answer("Найденные пользователи:", reply_markup=keyboard)
    
    await state.clear()

def format_user_info(user_info: dict) -> str:
    user = user_info["user"]
    return f"""
👤 Информация о пользователе {user.user_id}:
🆔 ID: {user.user_id}
📛 Имя: {user.full_name}
🤖 Username: @{user.username if user.username else 'не указан'}
⏰ Зарегистрирован: {user.created_at.strftime('%Y-%m-%d %H:%M')}
💎 Премиум: {'Да' if user.is_premium else 'Нет'}
{'Дата окончания: ' + user.premium_until.strftime('%Y-%m-%d %H:%M') if user.premium_until else ''}
🎫 Участий: {user_info['participation_count']}
🎁 Созданных розыгрышей: {user_info['created_giveaways_count']}
    """.strip()
```

2. **Реализация пагинации списка пользователей**
   - Эффективная пагинация с использованием OFFSET/LIMIT
   - Добавление фильтрации (премиум/обычные, дата регистрации и т.д.)

```python
from typing import List

class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_users_paginated(self, page: int = 1, page_size: int = 10, 
                                 filters: dict = None) -> tuple[List[User], int]:
        """
        Получение списка пользователей с пагинацией
        """
        offset = (page - 1) * page_size
        
        query = select(User).order_by(User.user_id.desc())
        
        # Применение фильтров
        if filters:
            conditions = []
            if filters.get('is_premium') is not None:
                conditions.append(User.is_premium == filters['is_premium'])
            if filters.get('date_from'):
                conditions.append(User.created_at >= filters['date_from'])
            if filters.get('date_to'):
                conditions.append(User.created_at <= filters['date_to'])
            
            if conditions:
                query = query.where(and_(*conditions))
        
        # Получение пользователей
        result = await self.session.execute(query.offset(offset).limit(page_size))
        users = result.scalars().all()
        
        # Получение общего количества
        count_query = select(func.count(User.user_id))
        if filters:
            count_conditions = []
            if filters.get('is_premium') is not None:
                count_conditions.append(User.is_premium == filters['is_premium'])
            if filters.get('date_from'):
                count_conditions.append(User.created_at >= filters['date_from'])
            if filters.get('date_to'):
                count_conditions.append(User.created_at <= filters['date_to'])
            
            if count_conditions:
                count_query = count_query.where(and_(*count_conditions))
        
        total_count = await self.session.scalar(count_query)
        
        return users, total_count

@admin_router.callback_query(F.data.startswith("admin_list_users_"))
async def show_users_list(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    
    service = UserService(session)
    users, total_count = await service.get_users_paginated(page=page)
    
    message_text = "Список пользователей:\n\n"
    for user in users:
        premium_status = "💎" if user.is_premium else "👤"
        message_text += f"{premium_status} [{user.user_id}] @{user.username or 'без_ника'} ({user.full_name})\n"
    
    keyboard = get_users_pagination_keyboard(page, total_count)
    await callback.message.edit_text(message_text, reply_markup=keyboard)

def get_users_pagination_keyboard(current_page: int, total_count: int, page_size: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    total_pages = (total_count + page_size - 1) // page_size
    
    if current_page > 1:
        builder.button(
            text="⏪ Назад",
            callback_data=f"admin_list_users_{current_page - 1}"
        )
    
    builder.button(
        text=f"{current_page}/{total_pages}",
        callback_data="admin_ignore"  # Заглушка, просто для отображения
    )
    
    if current_page < total_pages:
        builder.button(
            text="Вперед ⏩",
            callback_data=f"admin_list_users_{current_page + 1}"
        )
    
    builder.adjust(3)  # Располагаем кнопки в одной строке
    
    # Кнопка "Назад к меню"
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к пользователям",
            callback_data="admin_users"
        )
    )
    
    return builder.as_markup()
```

3. **Реализация подробной информации о пользователе**
   - Возможность изменения статуса премиума
   - Просмотр розыгрышей пользователя
   - Подтверждение критических действий

```python
@admin_router.callback_query(F.data.startswith("admin_user_detail_"))
async def show_user_detail(callback: CallbackQuery, session: AsyncSession):
    user_id = int(callback.data.split("_")[-1])
    
    service = UserService(session)
    user_info = await service.get_user_detailed_info(user_id)
    
    if not user_info:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    keyboard = get_user_detail_menu_keyboard(user_id)
    await callback.message.edit_text(
        format_user_info(user_info), 
        reply_markup=keyboard
    )

def get_user_detail_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="⭐ Выдать премиум",
            callback_data=f"admin_grant_premium_{user_id}"
        ),
        InlineKeyboardButton(
            text="❌ Забрать премиум",
            callback_data=f"admin_revoke_premium_{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Розыгрыши пользователя",
            callback_data=f"admin_user_giveaways_{user_id}_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к пользователям",
            callback_data="admin_users"
        )
    )
    
    return builder.as_markup()

@admin_router.callback_query(F.data.startswith("admin_grant_premium_"))
async def confirm_grant_premium(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    keyboard = get_confirm_premium_action_keyboard(user_id, "grant")
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите выдать премиум пользователю {user_id}?",
        reply_markup=keyboard
    )

@admin_router.callback_query(F.data.startswith("admin_confirm_premium_"))
async def process_premium_change(callback: CallbackQuery, session: AsyncSession):
    action, user_id_str = callback.data.split("_")[2:4]
    user_id = int(user_id_str)
    
    service = UserService(session)
    
    if action == "grant":
        success = await service.toggle_premium_status(user_id, is_premium=True)
        action_text = "выдан"
    else:
        success = await service.toggle_premium_status(user_id, is_premium=False)
        action_text = "забран"
    
    if success:
        await callback.message.edit_text(f"✅ Премиум успешно {action_text} пользователю {user_id}")
        # Логируем действие
        await log_admin_action(session, callback.from_user.id, f"premium_{action}", user_id)
    else:
        await callback.message.edit_text("❌ Ошибка при изменении статуса премиума")
    
    # Через 2 секунды возвращаемся к информации о пользователе
    await asyncio.sleep(2)
    await show_user_detail(
        type('MockCallback', (), {'data': f'admin_user_detail_{user_id}', 'message': callback.message})(),
        session
    )
```

### Ожидаемый результат:
- Реализован раздел управления пользователями
- Добавлена возможность поиска и просмотра информации
- Реализована пагинация списка пользователей
- Добавлена возможность изменения статуса премиума с подтверждением

---

## ЭТАП 5: Реализация раздела "Розыгрыши"

### Цель этапа:
Создать полнофункциональный раздел управления розыгрышами с возможностью поиска, просмотра информации и управления состоянием.

### Задачи:
1. **Реализация поиска розыгрышей**
   - Поиск по названию приза, ID владельца, статусу
   - Фильтрация по дате создания/окончания

```python
class GiveawaySearchState(StatesGroup):
    waiting_for_search_query = State()

@admin_router.callback_query(F.data == "admin_giveaways")
async def show_giveaways_menu(callback: CallbackQuery):
    keyboard = get_giveaways_menu_keyboard()
    await callback.message.edit_text("🎁 Меню розыгрышей", reply_markup=keyboard)

def get_giveaways_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔍 Поиск розыгрыша",
            callback_data="admin_search_giveaway"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Список розыгрышей",
            callback_data="admin_list_giveaways_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_main_menu"
        )
    )
    
    return builder.as_markup()

@admin_router.callback_query(F.data == "admin_search_giveaway")
async def start_giveaway_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GiveawaySearchState.waiting_for_search_query)
    keyboard = get_cancel_search_keyboard()
    await callback.message.edit_text(
        "🔍 Введите слово из приза или ID владельца:",
        reply_markup=keyboard
    )

@admin_router.message(GiveawaySearchState.waiting_for_search_query)
async def process_giveaway_search(message: Message, state: FSMContext, session: AsyncSession):
    search_query = message.text.strip()
    
    service = GiveawayService(session, None)  # bot будет установлен позже
    giveaways = await service.search_giveaways(search_query)
    
    if not giveaways:
        await message.answer("❌ Розыгрыши не найдены.")
        await state.clear()
        return
    
    if len(giveaways) == 1:
        # Если найден один розыгрыш, показываем его информацию
        giveaway_info = await service.get_giveaway_detailed_info(giveaways[0].id)
        keyboard = get_giveaway_detail_menu_keyboard(giveaway_info["giveaway"].id)
        await message.answer(format_giveaway_info(giveaway_info), reply_markup=keyboard)
    else:
        # Если найдено несколько розыгрышей, показываем список
        keyboard = get_giveaway_search_results_keyboard(giveaways)
        await message.answer("Найденные розыгрыши:", reply_markup=keyboard)
    
    await state.clear()

def format_giveaway_info(giveaway_info: dict) -> str:
    giveaway = giveaway_info["giveaway"]
    return f"""
🎁 Розыгрыш #{giveaway.id}:
🎁 Приз: {giveaway.prize_text}
👑 Владелец: {giveaway.owner_id}
📅 Создан: {giveaway.created_at.strftime('%Y-%m-%d %H:%M')}
🕐 Завершится: {giveaway.finish_time.strftime('%Y-%m-%d %H:%M')}
🎯 Участников: {giveaway_info['participant_count']}
👑 Победителей: {giveaway.winners_count}
🟢 Статус: {giveaway.status}
    """.strip()
```

2. **Реализация пагинации списка розыгрышей**
   - Сортировка по дате создания
   - Фильтрация по статусу и другим критериям

```python
@admin_router.callback_query(F.data.startswith("admin_list_giveaways_"))
async def show_giveaways_list(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    
    service = GiveawayService(session, None)  # bot будет установлен позже
    giveaways, total_count = await service.get_giveaways_paginated(page=page)
    
    message_text = "Список розыгрышей:\n\n"
    for giveaway in giveaways:
        message_text += f"🎁 [{giveaway.id}] \"{giveaway.prize_text}\" - владелец {giveaway.owner_id} - {giveaway.status}\n"
    
    keyboard = get_giveaways_pagination_keyboard(page, total_count)
    await callback.message.edit_text(message_text, reply_markup=keyboard)

def get_giveaways_pagination_keyboard(current_page: int, total_count: int, page_size: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    total_pages = (total_count + page_size - 1) // page_size
    
    if current_page > 1:
        builder.button(
            text="⏪ Назад",
            callback_data=f"admin_list_giveaways_{current_page - 1}"
        )
    
    builder.button(
        text=f"{current_page}/{total_pages}",
        callback_data="admin_ignore"
    )
    
    if current_page < total_pages:
        builder.button(
            text="Вперед ⏩",
            callback_data=f"admin_list_giveaways_{current_page + 1}"
        )
    
    builder.adjust(3)
    
    # Кнопка "Назад к меню"
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к розыгрышам",
            callback_data="admin_giveaways"
        )
    )
    
    return builder.as_markup()
```

3. **Реализация управления розыгрышами**
   - Принудительное завершение с уведомлением участников
   - Выбор победителя вручную
   - Безопасное удаление розыгрышей
   - Обязательное подтверждение критических действий

```python
@admin_router.callback_query(F.data.startswith("admin_giveaway_detail_"))
async def show_giveaway_detail(callback: CallbackQuery, session: AsyncSession):
    giveaway_id = int(callback.data.split("_")[-1])
    
    service = GiveawayService(session, None)  # bot будет установлен позже
    giveaway_info = await service.get_giveaway_detailed_info(giveaway_id)
    
    if not giveaway_info:
        await callback.answer("❌ Розыгрыш не найден.", show_alert=True)
        return
    
    keyboard = get_giveaway_detail_menu_keyboard(giveaway_id)
    await callback.message.edit_text(
        format_giveaway_info(giveaway_info), 
        reply_markup=keyboard
    )

def get_giveaway_detail_menu_keyboard(giveaway_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🎲 Принудительно завершить",
            callback_data=f"admin_force_finish_{giveaway_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏆 Принудительный победитель",
            callback_data=f"admin_set_winner_{giveaway_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👥 Список участников",
            callback_data=f"admin_giveaway_participants_{giveaway_id}_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к розыгрышам",
            callback_data="admin_giveaways"
        )
    )
    
    return builder.as_markup()

@admin_router.callback_query(F.data.startswith("admin_force_finish_"))
async def confirm_force_finish_giveaway(callback: CallbackQuery):
    giveaway_id = int(callback.data.split("_")[-1])
    keyboard = get_confirm_giveaway_action_keyboard(giveaway_id, "finish")
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите завершить розыгрыш #{giveaway_id}?\n"
        "Все участники будут уведомлены.",
        reply_markup=keyboard
    )

@admin_router.callback_query(F.data.startswith("admin_confirm_giveaway_"))
async def process_giveaway_action(callback: CallbackQuery, session: AsyncSession, bot):
    action, giveaway_id_str = callback.data.split("_")[2:4]
    giveaway_id = int(giveaway_id_str)
    
    service = GiveawayService(session, bot)
    
    if action == "finish":
        success = await service.force_finish_giveaway(giveaway_id, callback.from_user.id)
        action_text = "завершен"
    else:
        # Обработка других действий
        success = False
        action_text = "обработан"
    
    if success:
        await callback.message.edit_text(f"✅ Розыгрыш #{giveaway_id} успешно {action_text}")
        # Логируем действие
        await log_admin_action(session, callback.from_user.id, f"giveaway_{action}", giveaway_id)
    else:
        await callback.message.edit_text("❌ Ошибка при обработке розыгрыша")
    
    # Через 2 секунды возвращаемся к информации о розыгрыше
    await asyncio.sleep(2)
    await show_giveaway_detail(
        type('MockCallback', (), {'data': f'admin_giveaway_detail_{giveaway_id}', 'message': callback.message})(),
        session
    )

def get_confirm_giveaway_action_keyboard(giveaway_id: int, action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да",
            callback_data=f"admin_confirm_giveaway_{action}_{giveaway_id}"
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data="admin_giveaways"
        )
    )
    return builder.as_markup()
```

### Ожидаемый результат:
- Реализован раздел управления розыгрышами
- Добавлена возможность поиска и просмотра информации
- Реализована пагинация списка розыгрышей
- Добавлена возможность принудительного завершения и выбора победителя с подтверждением

---

## ЭТАП 6: Реализация раздела "Рассылка"

### Цель этапа:
Создать полнофункциональный раздел рассылок с поддержкой различных типов медиа, отложенной отправки и статистики.

### Задачи:
1. **Реализация создания рассылок**
   - Поддержка различных типов медиа (текст, фото, видео, документы)
   - Возможность предварительного просмотра перед отправкой
   - Поддержка форматирования текста

```python
class BroadcastState(StatesGroup):
    waiting_for_message = State()
    waiting_for_schedule_time = State()
    waiting_for_recipient_filter = State()

@admin_router.callback_query(F.data == "admin_broadcast")
async def show_broadcast_menu(callback: CallbackQuery):
    keyboard = get_broadcast_menu_keyboard()
    await callback.message.edit_text("📢 Меню рассылки", reply_markup=keyboard)

def get_broadcast_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✍️ Создать рассылку",
            callback_data="admin_create_broadcast"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 История рассылок",
            callback_data="admin_broadcast_history_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⏱ Отложенные рассылки",
            callback_data="admin_scheduled_broadcasts_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика рассылок",
            callback_data="admin_broadcast_stats"
        )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_main_menu"
        )
    )
    
    return builder.as_markup()

@admin_router.callback_query(F.data == "admin_create_broadcast")
async def start_create_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_message)
    keyboard = get_cancel_broadcast_creation_keyboard()
    await callback.message.edit_text(
        "✍️ Создание рассылки\n\nВведите текст сообщения или прикрепите медиа:",
        reply_markup=keyboard
    )

@admin_router.message(BroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    # Сохраняем данные рассылки во временные данные состояния
    broadcast_data = {}
    
    if message.text:
        broadcast_data['text'] = message.text
    elif message.photo:
        broadcast_data['photo'] = message.photo[-1].file_id
        if message.caption:
            broadcast_data['text'] = message.caption
    elif message.video:
        broadcast_data['video'] = message.video.file_id
        if message.caption:
            broadcast_data['text'] = message.caption
    elif message.document:
        broadcast_data['document'] = message.document.file_id
        if message.caption:
            broadcast_data['text'] = message.caption
    else:
        await message.answer("❌ Поддерживаемые типы: текст, фото, видео, документы")
        return
    
    await state.update_data(broadcast_data=broadcast_data)
    
    # Показываем предварительный просмотр
    keyboard = get_broadcast_preview_keyboard()
    preview_text = "📋 Предпросмотр:\n\n"
    if 'text' in broadcast_data:
        preview_text += broadcast_data['text']
    else:
        preview_text += "[Медиа сообщение]"
    
    await message.answer(preview_text, reply_markup=keyboard)

def get_broadcast_preview_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📤 Отправить сейчас",
            callback_data="admin_send_broadcast_now"
        ),
        InlineKeyboardButton(
            text="⏰ Отложенная отправка",
            callback_data="admin_schedule_broadcast"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_broadcast"
        )
    )
    return builder.as_markup()
```

2. **Реализация отложенных рассылок**
   - Гибкое планирование с возможностью изменения времени
   - Возможность отмены запланированных рассылок

```python
@admin_router.callback_query(F.data == "admin_schedule_broadcast")
async def start_schedule_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_schedule_time)
    # Здесь должна быть реализация выбора времени (календарь/время)
    await callback.message.edit_text(
        "⏰ Выберите время отправки (в формате ГГГГ-ММ-ДД ЧЧ:ММ):",
        reply_markup=get_cancel_schedule_keyboard()
    )

@admin_router.message(BroadcastState.waiting_for_schedule_time)
async def process_schedule_time(message: Message, state: FSMContext, session: AsyncSession):
    try:
        schedule_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        
        if schedule_time < datetime.now():
            await message.answer("❌ Время не может быть в прошлом")
            return
        
        data = await state.get_data()
        broadcast_data = data['broadcast_data']
        
        # Сохраняем отложенную рассылку в базу данных
        scheduled_broadcast = ScheduledBroadcast(
            message_text=broadcast_data.get('text', ''),
            photo_file_id=broadcast_data.get('photo'),
            video_file_id=broadcast_data.get('video'),
            document_file_id=broadcast_data.get('document'),
            scheduled_time=schedule_time,
            created_by=message.from_user.id
        )
        
        session.add(scheduled_broadcast)
        await session.commit()
        
        await message.answer(f"✅ Рассылка запланирована на {schedule_time.strftime('%Y-%m-%d %H:%M')}")
        await state.clear()
        
        # Логируем действие
        await log_admin_action(session, message.from_user.id, "broadcast_scheduled", scheduled_broadcast.id)
        
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ГГГГ-ММ-ДД ЧЧ:ММ")

@admin_router.callback_query(F.data.startswith("admin_scheduled_broadcasts_"))
async def show_scheduled_broadcasts(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    page_size = 10
    offset = (page - 1) * page_size
    
    result = await session.execute(
        select(ScheduledBroadcast)
        .order_by(ScheduledBroadcast.scheduled_time.asc())
        .offset(offset).limit(page_size)
    )
    scheduled_broadcasts = result.scalars().all()
    
    result_count = await session.execute(
        select(func.count(ScheduledBroadcast.id))
    )
    total_count = result_count.scalar()
    
    if not scheduled_broadcasts:
        await callback.message.edit_text("⏰ Нет запланированных рассылок")
        return
    
    message_text = "⏰ Отложенные рассылки:\n\n"
    for sb in scheduled_broadcasts:
        message_preview = sb.message_text[:30] + "..." if len(sb.message_text) > 30 else sb.message_text
        message_text += f"⏰ [{sb.scheduled_time.strftime('%Y-%m-%d %H:%M')}] \"{message_preview}\" - статус: {sb.status}\n"
    
    keyboard = get_scheduled_broadcasts_pagination_keyboard(page, total_count)
    await callback.message.edit_text(message_text, reply_markup=keyboard)
```

3. **Реализация истории рассылок и статистики**
   - Подробная история со статусами и счетчиками
   - Возможность повторной отправки
   - Статистика эффективности

```python
@admin_router.callback_query(F.data.startswith("admin_broadcast_history_"))
async def show_broadcast_history(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    page_size = 10
    offset = (page - 1) * page_size
    
    result = await session.execute(
        select(Broadcast)
        .order_by(Broadcast.created_at.desc())
        .offset(offset).limit(page_size)
    )
    broadcasts = result.scalars().all()
    
    result_count = await session.execute(
        select(func.count(Broadcast.id))
    )
    total_count = result_count.scalar()
    
    if not broadcasts:
        await callback.message.edit_text("📝 Нет истории рассылок")
        return
    
    message_text = "📝 История рассылок:\n\n"
    for bc in broadcasts:
        message_preview = bc.message_text[:30] + "..." if len(bc.message_text) > 30 else bc.message_text
        message_text += f"📨 [{bc.created_at.strftime('%Y-%m-%d %H:%M')}] \"{message_preview}\" - {bc.status} - {bc.sent_count}/{bc.total_count}\n"
    
    keyboard = get_broadcast_history_pagination_keyboard(page, total_count)
    await callback.message.edit_text(message_text, reply_markup=keyboard)

def get_broadcast_history_pagination_keyboard(current_page: int, total_count: int, page_size: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    total_pages = (total_count + page_size - 1) // page_size
    
    if current_page > 1:
        builder.button(
            text="⏪ Назад",
            callback_data=f"admin_broadcast_history_{current_page - 1}"
        )
    
    builder.button(
        text=f"{current_page}/{total_pages}",
        callback_data="admin_ignore"
    )
    
    if current_page < total_pages:
        builder.button(
            text="Вперед ⏩",
            callback_data=f"admin_broadcast_history_{current_page + 1}"
        )
    
    builder.adjust(3)
    
    # Кнопка "Назад к меню"
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к рассылкам",
            callback_data="admin_broadcast"
        )
    )
    
    return builder.as_markup()

# При нажатии на элемент истории рассылки открывается подробная информация:
@admin_router.callback_query(lambda c: c.data.startswith("admin_broadcast_detail_"))
async def show_broadcast_detail(callback: CallbackQuery, session: AsyncSession):
    broadcast_id = int(callback.data.split("_")[-1])
    
    broadcast = await session.get(Broadcast, broadcast_id)
    if not broadcast:
        await callback.answer("❌ Рассылка не найдена", show_alert=True)
        return
    
    message_text = f"""
📋 Подробная информация о рассылке #{broadcast_id}:
Дата создания: {broadcast.created_at.strftime('%Y-%m-%d %H:%M')}
Статус: {broadcast.status}
Отправлено: {broadcast.sent_count}
Всего: {broadcast.total_count}
Провалено: {broadcast.failed_count}
Заблокировано: {broadcast.blocked_count}

Текст сообщения:
{broadcast.message_text}
    """.strip()
    
    keyboard = get_broadcast_detail_actions_keyboard(broadcast_id)
    await callback.message.edit_text(message_text, reply_markup=keyboard)

def get_broadcast_detail_actions_keyboard(broadcast_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔄 Повторная отправка",
            callback_data=f"admin_resend_broadcast_{broadcast_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_broadcast_history_1"
        )
    )
    return builder.as_markup()
```

### Ожидаемый результат:
- Реализован раздел рассылок с полным функционалом
- Добавлена поддержка различных типов медиа
- Реализована система отложенных рассылок
- Создана история рассылок с возможностью повторной отправки

---

## ЭТАП 7: Интеграция безопасности

### Цель этапа:
Обеспечить безопасность админ-панели, добавить логирование действий и подтверждение критических операций.

### Задачи:
1. **Добавление логирования действий**
   - Логирование всех действий администраторов
   - Сохранение информации о действиях в базе данных

```python
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

async def log_admin_action(session: AsyncSession, admin_id: int, action: str, target_id: int = None, details: dict = None):
    """
    Логирование действия администратора
    """
    log_entry = AdminLog(
        admin_id=admin_id,
        action=action,
        target_id=target_id,
        details=details
    )
    session.add(log_entry)
    await session.commit()

@admin_router.callback_query(F.data.startswith("admin_grant_premium_"))
async def confirm_grant_premium(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    
    # Логируем попытку изменения статуса премиума
    await log_admin_action(
        session, 
        callback.from_user.id, 
        "premium_grant_attempt", 
        user_id, 
        {"action": "grant"}
    )
    
    keyboard = get_confirm_premium_action_keyboard(user_id, "grant")
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите выдать премиум пользователю {user_id}?",
        reply_markup=keyboard
    )
```

2. **Реализация подтверждения критических действий**
   - Принудительное завершение розыгрышей
   - Изменение статуса премиума
   - Удаление данных

```python
def get_confirm_premium_action_keyboard(user_id: int, action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"admin_confirm_premium_{action}_{user_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"admin_user_detail_{user_id}"
        )
    )
    return builder.as_markup()

@admin_router.callback_query(F.data.startswith("admin_confirm_giveaway_"))
async def process_giveaway_action(callback: CallbackQuery, session: AsyncSession, bot):
    action, giveaway_id_str = callback.data.split("_")[2:4]
    giveaway_id = int(giveaway_id_str)
    
    # Логируем подтвержденное действие
    await log_admin_action(
        session, 
        callback.from_user.id, 
        f"giveaway_{action}_confirmed", 
        giveaway_id
    )
    
    service = GiveawayService(session, bot)
    
    if action == "finish":
        success = await service.force_finish_giveaway(giveaway_id, callback.from_user.id)
        action_text = "завершен"
    else:
        success = False
        action_text = "обработан"
    
    if success:
        await callback.message.edit_text(f"✅ Розыгрыш #{giveaway_id} успешно {action_text}")
    else:
        await callback.message.edit_text("❌ Ошибка при обработке розыгрыша")
    
    # Возвращаемся к информации о розыгрыше
    await asyncio.sleep(2)
    await show_giveaway_detail(
        type('MockCallback', (), {'data': f'admin_giveaway_detail_{giveaway_id}', 'message': callback.message})(),
        session
    )
```

3. **Добавление ограничений на частоту запросов**
   - Защита от DDoS атак на админ-панель
   - Ограничение количества запросов в минуту для каждого администратора

```python
import time
from collections import defaultdict
from typing import Dict

class RateLimiter:
    def __init__(self, max_requests: int = 10, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests: Dict[int, list] = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> bool:
        now = time.time()
        # Удаляем старые запросы
        self.requests[user_id] = [req_time for req_time in self.requests[user_id] if now - req_time < self.window]
        
        if len(self.requests[user_id]) < self.max_requests:
            self.requests[user_id].append(now)
            return True
        
        return False

# Глобальный лимитер
rate_limiter = RateLimiter()

@admin_router.callback_query()
async def admin_callback_handler(callback: CallbackQuery, session: AsyncSession):
    # Проверяем рейт-лимит
    if not rate_limiter.is_allowed(callback.from_user.id):
        await callback.answer("❌ Слишком много запросов. Попробуйте позже.", show_alert=True)
        return
    
    # Обработка остальных callback'ов
    # ...
```

### Ожидаемый результат:
- Добавлено полное логирование действий администраторов
- Реализовано подтверждение критических действий
- Добавлена защита от частых запросов

---

## ЭТАП 8: Тестирование и оптимизация

### Цель этапа:
Протестировать все функции админ-панели, оптимизировать производительность и обработать возможные ошибки.

### Задачи:
1. **Тестирование всех функций**
   - Модульное тестирование сервисов
   - Интеграционное тестирование взаимодействия компонентов
   - Тестирование обработки ошибок

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_statistics_service():
    # Создаем mock сессии
    mock_session = AsyncMock()
    
    # Настройка ожидаемых возвращаемых значений
    mock_session.scalar.return_value = 100  # Например, общее количество пользователей
    
    service = StatisticsService(mock_session)
    stats = await service.get_general_stats()
    
    assert stats["total_users"] == 100
    # Проверяем, что были вызваны ожидаемые методы
    assert mock_session.scalar.called

@pytest.mark.asyncio
async def test_user_search():
    mock_session = AsyncMock()
    
    # Создаем mock пользователя
    mock_user = MagicMock()
    mock_user.user_id = 123
    mock_user.username = "testuser"
    mock_user.full_name = "Test User"
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_user]
    mock_session.execute.return_value = mock_result
    
    service = UserService(mock_session)
    users = await service.search_users("testuser")
    
    assert len(users) == 1
    assert users[0].username == "testuser"

# Пример теста для проверки обработки ошибок
@pytest.mark.asyncio
async def test_broadcast_with_error_handling():
    mock_session = AsyncMock()
    mock_bot = AsyncMock()
    
    # Тестируем ситуацию, когда происходит ошибка при отправке
    mock_bot.send_message.side_effect = Exception("Network error")
    
    service = BroadcastSystem(mock_bot, mock_session)
    
    # Убедимся, что система корректно обрабатывает ошибки
    result = await service._send_single_message(123, BroadcastMessage("Test message"))
    assert result is False  # Ожидаем, что результат будет False при ошибке
```

2. **Оптимизация производительности**
   - Оптимизация SQL-запросов с помощью индексов
   - Пагинация для работы с большими списками
   - Кэширование часто запрашиваемых данных

```python
# Пример добавления индексов в моделях
from sqlalchemy import Index

# Индекс для быстрого поиска пользователей по username
Index('idx_users_username', User.username)

# Индекс для фильтрации розыгрышей по статусу
Index('idx_giveaways_status', Giveaway.status)

# Индекс для сортировки розыгрышей по дате создания
Index('idx_giveaways_created_at', Giveaway.created_at.desc())

# Кэширование статистики
class StatisticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache = StatsCache(ttl=300)  # 5 минут
    
    async def get_general_stats(self) -> dict:
        cache_key = "general_stats"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Выполняем запросы к базе данных
        total_users = await self.session.scalar(select(func.count(User.user_id)))
        active_giveaways = await self.session.scalar(
            select(func.count(Giveaway.id)).where(Giveaway.status == "active")
        )
        total_participations = await self.session.scalar(
            select(func.count(Participant.user_id))
        )
        potential_bots = await self.session.scalar(
            select(func.count(User.user_id)).where(User.username.is_(None))
        )
        
        result = {
            "total_users": total_users,
            "active_giveaways": active_giveaways,
            "total_participations": total_participations,
            "potential_bots": potential_bots
        }
        
        # Сохраняем в кэш
        self.cache.set(cache_key, result)
        return result
```

3. **Тестирование обработки ошибок**
   - Централизованная система обработки исключений
   - Логирование ошибок с контекстом
   - Механизмы повторных попыток для сетевых операций

```python
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

def handle_exceptions(default_return=None):
    """
    Декоратор для централизованной обработки исключений
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                return default_return
        return wrapper
    return decorator

class StatisticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache = StatsCache()
    
    @handle_exceptions(default_return={})
    async def get_general_stats(self) -> dict:
        cache_key = "general_stats"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Ваши запросы к базе данных
        total_users = await self.session.scalar(select(func.count(User.user_id)))
        active_giveaways = await self.session.scalar(
            select(func.count(Giveaway.id)).where(Giveaway.status == "active")
        )
        total_participations = await self.session.scalar(
            select(func.count(Participant.user_id))
        )
        potential_bots = await self.session.scalar(
            select(func.count(User.user_id)).where(User.username.is_(None))
        )
        
        result = {
            "total_users": total_users,
            "active_giveaways": active_giveaways,
            "total_participations": total_participations,
            "potential_bots": potential_bots
        }
        
        self.cache.set(cache_key, result)
        return result

# Обработчик ошибок для всего роутера
@admin_router.errors()
async def admin_errors_handler(update, error):
    logger.error(f"Admin router error: {error}", exc_info=True)
    # Можно отправить уведомление администратору о критической ошибке
```

### Ожидаемый результат:
- Все функции протестированы и работают корректно
- Производительность оптимизирована
- Реализована надежная обработка ошибок
- Система готова к эксплуатации

---

## ЗАКЛЮЧЕНИЕ

Реализация админ-панели для бота розыгрышей была выполнена поэтапно в соответствии с лучшими практиками разработки. Каждый этап включал в себя реализацию конкретных функций с учетом безопасности, производительности и удобства использования.

Основные достижения:
1. Создана безопасная админ-панель с проверкой прав доступа
2. Реализованы все основные функции: статистика, управление пользователями, розыгрышами и рассылками
3. Обеспечена защита от частых запросов и критических действий
4. Оптимизирована производительность с использованием кэширования и индексов
5. Добавлена полная система логирования действий
6. Реализована надежная обработка ошибок

Важно учитывать ограничения Telegram API, особенно при реализации системы рассылок, чтобы избежать блокировок бота. Следование всем вышеописанным рекомендациям позволяет создать надежную, безопасную и масштабируемую админ-панель для управления ботом розыгрышей.