# Рекомендации по улучшению Telegram-бота для розыгрышей

## 1. Архитектурные улучшения

### 1.1. Улучшенная структура middleware

В файле [`random/main.py`](file:///home/hot/Desktop/ytb/random/main.py:1-95) необходимо изменить порядок middleware:

```python
# Правильный порядок middleware:
dp.update.middleware(DbSessionMiddleware())  # Сначала сессия БД
dp.update.middleware(ErrorMiddleware())      # Затем обработка ошибок
dp.message.middleware(ThrottlingMiddleware(redis, rate_limit=1.0))
dp.callback_query.middleware(ThrottlingMiddleware(redis, rate_limit=1.0))
```

### 1.2. Создание централизованного файла настройки middleware

Создайте файл [`random/middlewares/setup.py`](file:///home/hot/Desktop/ytb/random/middlewares/setup.py):

```python
from aiogram import Dispatcher
from redis.asyncio import Redis

from .db_session import DbSessionMiddleware
from .error_handler import ErrorMiddleware
from .throttling import ThrottlingMiddleware


def setup_middlewares(dp: Dispatcher, redis: Redis):
    """Установка middleware в правильном порядке"""
    # Сначала сессия БД
    dp.update.middleware(DbSessionMiddleware())
    
    # Затем обработка ошибок
    dp.update.middleware(ErrorMiddleware())
    
    # Затем throttling
    dp.message.middleware(ThrottlingMiddleware(redis, rate_limit=1.0))
    dp.callback_query.middleware(ThrottlingMiddleware(redis, rate_limit=1.0))
```

### 1.3. Улучшенный жизненный цикл приложения

Обновите файл [`random/main.py`](file:///home/hot/Desktop/ytb/random/main.py:1-95):

```python
import asyncio
import signal
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from config import config
from database import engine, Base
from core.tools.scheduler import start_scheduler, scheduler
from core.logic.game_actions import update_active_giveaways_task
from middlewares.setup import setup_middlewares

# Импорты роутеров
from handlers.user import router as user_router
from handlers.creator import router as creator_router
from handlers.participant import join
from handlers.common import start


@asynccontextmanager
async def lifespan(app):
    """Управление жизненным циклом приложения"""
    redis = Redis.from_url(config.REDIS_URL)
    bot = Bot(token=config.BOT_TOKEN.get_secret_value(), default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=RedisStorage(redis=redis))
    
    # Установка middleware
    setup_middlewares(dp, redis)
    
    # Подключение роутеров
    dp.include_router(user_router)
    dp.include_router(creator_router)
    dp.include_router(join.router)
    dp.include_router(start.router)
    
    # Запуск планировщика
    scheduler.add_job(update_active_giveaways_task, "interval", minutes=30, id="global_updater", replace_existing=True)
    await start_scheduler()
    
    yield {"bot": bot, "dp": dp, "redis": redis}
    
    # Очистка
    await scheduler.shutdown()
    await bot.session.close()
    await redis.aclose()


async def main():
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Инициализация БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with lifespan(None) as app:
        bot = app["bot"]
        dp = app["dp"]
        redis = app["redis"]
        
        # Удаляем вебхук и сбрасываем старые апдейты
        await bot.delete_webhook(drop_pending_updates=True)
        
        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()
            await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
```

## 2. Улучшения безопасности

### 2.1. Улучшенный throttling с учетом chat_id

Обновите файл [`random/middlewares/throttling.py`](file:///home/hot/Desktop/ytb/random/middlewares/throttling.py:1-42):

```python
from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from core.exceptions import error_handler


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis, rate_limit: float = 1.0):
        self.redis = redis
        self.rate_limit = rate_limit

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        try:
            user_id = event.from_user.id
            # Для групповых чатов используем chat_id в ключе
            chat_id = getattr(event, 'chat', None)
            if chat_id and hasattr(chat_id, 'id'):
                key = f"throttle:{chat_id.id}:{user_id}"
            else:
                key = f"throttle:user:{user_id}"
            
            # Проверяем наличие ключа в Redis
            if await self.redis.get(key):
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Не так быстро!", show_alert=True)
                elif isinstance(event, Message):
                    # Для сообщений можем отправить предупреждение
                    await event.answer("⏳ Не так быстро!")
                return
                
            # Устанавливаем ключ с временем жизни (TTL) = rate_limit
            await self.redis.set(key, "1", ex=int(self.rate_limit))
            
            # Пропускаем дальше
            return await handler(event, data)
        except Exception as e:
            # Обрабатываем ошибку через централизованный обработчик
            await error_handler.handle_error(e, event.from_user.id if event.from_user else None, "throttling_middleware")
            raise e
```

### 2.2. Улучшенная обработка ошибок TelegramBadRequest

Создайте файл [`random/core/telegram_error_handler.py`](file:///home/hot/Desktop/ytb/random/core/telegram_error_handler.py):

```python
from aiogram.exceptions import TelegramBadRequest
from aiogram import html


async def handle_telegram_bad_request(error: TelegramBadRequest, user_id: int = None):
    """Обработка специфичных ошибок TelegramBadRequest"""
    error_description = str(error).lower()
    
    if "message is not modified" in error_description:
        # Это нормальное поведение, можно игнорировать
        return True
    elif "message to edit not found" in error_description:
        # Сообщение было удалено, можно игнорировать
        return True
    elif "query is too old" in error_description or "query_id_invalid" in error_description:
        # Callback query слишком старый, можно игнорировать
        return True
    elif "user is deactivated" in error_description or "user not found" in error_description:
        # Пользователь удален, можно игнорировать
        return True
    elif "bot was blocked" in error_description or "bot was kicked" in error_description:
        # Бот заблокирован, можно игнорировать
        return True
    
    return False  # Ошибка требует дополнительной обработки


async def safe_edit_message(call: CallbackQuery, text: str, reply_markup=None):
    """Безопасное редактирование сообщения с обработкой различных ошибок"""
    try:
        await call.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if await handle_telegram_bad_request(e, call.from_user.id):
            # Игнорируем известные ошибки, просто отвечаем на callback
            await call.answer()
        else:
            # Другая ошибка, логируем
            from utils.logging_config import logger
            logger.error(f"Unexpected TelegramBadRequest: {e}")
            await call.answer("Ошибка при обновлении сообщения", show_alert=True)
    except Exception as e:
        from utils.logging_config import logger
        logger.error(f"Error editing message: {e}")
        await call.answer("Произошла ошибка", show_alert=True)
```

### 2.3. Улучшенная обработка обновлений

Обновите файл [`random/handlers/user/dashboard.py`](file:///home/hot/Desktop/ytb/random/handlers/user/dashboard.py:1-59):

```python
from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import html
from core.telegram_error_handler import safe_edit_message

from database.requests.user_repo import register_user
from keyboards.inline.dashboard import start_menu_kb, cabinet_kb
from handlers.common.start import cmd_start as deep_link_logic

router = Router()

@router.message(CommandStart())
async def smart_dashboard(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    bot: Bot,
    state: FSMContext
):
    # DeepLink (рефки и участие)
    if command.args and (command.args.startswith("gw_") or command.args.startswith("res_")):
        await deep_link_logic(message, command, session, bot, state)
        return

    # Регистрация
    await register_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    text = (
        f"👋 <b>Привет, {html.quote(message.from_user.first_name)}!</b>\n"
        f"Это платформа для проведения честных розыгрышей.\n\n"
        f"Выберите действие:"
    )

    await message.answer(text, reply_markup=start_menu_kb())

@router.callback_query(F.data == "dashboard_home")
async def back_home(call: CallbackQuery):
    await safe_edit_message(
        call,
        "👋 <b>Главное меню</b>\nВыберите действие:",
        reply_markup=start_menu_kb()
    )

@router.callback_query(F.data == "cabinet_hub")
async def open_cabinet(call: CallbackQuery, session: AsyncSession):
    text = (
        "👤 <b>Кабинет организатора</b>\n\n"
        f"🆔 ID: <code>{html.quote(str(call.from_user.id))}</code>\n"
        "📊 Здесь вы управляете каналами и подпиской."
    )
    await safe_edit_message(call, text, reply_markup=cabinet_kb())
```

## 3. Улучшения производительности

### 3.1. Оптимизация запросов к базе данных

В файле [`random/database/requests/user_repo.py`](file:///home/hot/Desktop/ytb/random/database/requests/user_repo.py:1-29) добавьте индексы для часто используемых полей:

```python
from sqlalchemy import BigInteger, String, Boolean, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    full_name: Mapped[str] = mapped_column(String)
    
    # --- Monetization ---
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # --- Timestamps ---
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Связь с розыгрышами (владелец)
    giveaways: Mapped[list["Giveaway"]] = relationship("Giveaway", back_populates="owner", lazy="selectin")

    def __repr__(self):
        return f"<User {self.user_id}>"

# Индексы для оптимизации производительности
Index('idx_users_username', User.username)
Index('idx_users_premium', User.is_premium)
Index('idx_users_created_at', User.created_at.desc())
# Добавляем индекс по user_id для быстрого поиска
Index('idx_users_user_id', User.user_id)
```

### 3.2. Улучшенная система логирования

Создайте файл [`random/utils/logger.py`](file:///home/hot/Desktop/ytb/random/utils/logger.py):

```python
import logging
from typing import Optional
import sys
from config import config

def setup_logger(name: str = "bot", level: int = logging.INFO) -> logging.Logger:
    """Настройка логгера с форматированием"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Избегаем дублирования хендлеров
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Получение логгера с глобальным уровнем из конфига"""
    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO) if hasattr(config, 'LOG_LEVEL') else logging.INFO
    return setup_logger(name, level)
```

И обновите [`random/config.py`](file:///home/hot/Desktop/ytb/random/config.py:1-30):

```python
from typing import List
from pydantic_settings import BaseSettings
from pydantic import SecretStr, field_validator, ConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    # Используем валидатор, чтобы превращать строку "123,456" в список [123, 456]
    ADMIN_IDS: List[int]
    DB_DNS: str
    REDIS_URL: str
    SECRET_KEY: str
    LOG_LEVEL: str = "INFO"  # Добавляем уровень логирования
    
    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        # Если пришла строка (например "123,456"), сплитим её
        if isinstance(v, str):
            # Удаляем квадратные скобки если пользователь их все-таки написал
            v = v.replace("[", "").replace("]", "")
            if not v:
                return []
            return [int(x.strip()) for x in v.split(",")]
        # Если пришло число (один админ без кавычек и запятых)
        if isinstance(v, int):
            return [v]
        return v

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

config = Settings()
```

## 4. Улучшения безопасности данных

### 4.1. Проверка подписки с кэшированием

Обновите сервис проверки подписки, добавив кэширование результатов:

```python
# В файле random/core/services/checker_service.py (или создайте новый)
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from redis.asyncio import Redis
from config import config

logger = logging.getLogger(__name__)
redis = Redis.from_url(config.REDIS_URL)

async def is_user_subscribed(bot: Bot, chat_id: int, user_id: int, force_check: bool = False) -> bool:
    """
    Проверка подписки пользователя на канал с кэшированием
    """
    cache_key = f"sub:{chat_id}:{user_id}"
    
    if not force_check:
        # Проверяем кэш
        cached_result = await redis.get(cache_key)
        if cached_result is not None:
            return cached_result == b"1"
    
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        is_subscribed = member.status in ['member', 'administrator', 'creator']
        
        # Сохраняем результат в кэш на 5 минут
        await redis.setex(cache_key, 300, "1" if is_subscribed else "0")
        
        return is_subscribed
    except TelegramBadRequest as e:
        logger.error(f"Error checking subscription (User: {user_id}, Chat: {chat_id}): {e}")
        # В случае ошибки сохраняем результат как "не подписан" на короткое время
        await redis.setex(cache_key, 60, "0")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking subscription (User: {user_id}, Chat: {chat_id}): {e}")
        return False
```

## 5. Улучшения архитектуры обработчиков

### 5.1. Использование централизованного реестра роутеров

Создайте файл [`random/handlers/__init__.py`](file:///home/hot/Desktop/ytb/random/handlers/__init__.py):

```python
from aiogram import Router

# Импорты всех роутеров
from .user import router as user_router
from .creator import router as creator_router
from .participant import join
from .common import start

# Централизованный роутер для всех обработчиков
def get_main_router() -> Router:
    """Возвращает главный роутер с подключенными всеми подроутерами"""
    main_router = Router()
    
    # Подключение всех роутеров
    main_router.include_router(user_router)
    main_router.include_router(creator_router)
    main_router.include_router(join.router)
    main_router.include_router(start.router)
    
    return main_router
```

Затем обновите [`random/main.py`](file:///home/hot/Desktop/ytb/random/main.py:1-95) для использования централизованного роутера:

```python
# В начале файла
from handlers import get_main_router

# В функции main()
async def main():
    # ... остальной код ...
    
    # Подключение роутеров через централизованный метод
    dp.include_router(get_main_router())
    
    # ... остальной код ...
```

## 6. Дополнительные рекомендации

### 6.1. Использование типизации для улучшения читаемости

Добавьте аннотации типов к основным функциям:

```python
from typing import Union
from aiogram.types import Message, CallbackQuery

async def process_user_action(
    event: Union[Message, CallbackQuery],
    session: AsyncSession,
    bot: Bot,
    state: FSMContext
) -> None:
    # Реализация функции
    pass
```

### 6.2. Создание системы конфигурации с валидацией

Обновите файл [`random/config.py`](file:///home/hot/Desktop/ytb/random/config.py:1-30) для добавления дополнительных параметров:

```python
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import SecretStr, field_validator, ConfigDict, validator

class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    ADMIN_IDS: List[int]
    DB_DNS: str
    REDIS_URL: str
    SECRET_KEY: str
    LOG_LEVEL: str = "INFO"
    
    # Дополнительные параметры
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_PATH: str = "/webhook"
    LISTEN_HOST: str = "0.0.0"
    LISTEN_PORT: int = 8000
    RATE_LIMIT_PER_SECOND: float = 1.0
    SESSION_LIFETIME: int = 86400  # 24 часа
    
    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            v = v.replace("[", "").replace("]", "")
            if not v:
                return []
            return [int(x.strip()) for x in v.split(",")]
        if isinstance(v, int):
            return [v]
        return v

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

config = Settings()
```

Эти улучшения позволят сделать ваш бот для розыгрышей более стабильным, безопасным и масштабируемым. Они включают в себя лучшие практики разработки Telegram-ботов с использованием aiogram 3.x, а также учитывают современные подходы к асинхронному программированию и работе с базами данных.