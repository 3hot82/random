# Подробный план реализации улучшенной админ-панели

## Введение

Данный план описывает пошаговую реализацию улучшенной админ-панели на основе ревью файла `admin_panel_structure_plan.md` и анализа текущего состояния проекта. План включает технические детали, архитектурные решения и поэтапное внедрение новых функций.

## Архитектурные изменения

### 1. Система навигации

#### 1.1. Обновление callback data для навигации

Создадим расширенную систему callback data для поддержки контекстно-зависимой навигации:

```python
# keyboards/callback_data.py
from aiogram.filters.callback_data import CallbackData

# Существующие классы...
class EnhancedNavigationAction(CallbackData, prefix="enh_nav"):
    """
    Callback data для улучшенной навигации
    action: back, main, to_section, refresh, contextual_back, breadcrumb
    section: целевой раздел для "to_section"
    context_stack: сериализованный стек контекста (через запятую)
    page: текущая страница для разделов с пагинацией
    """
    action: str
    section: str = ""
    context_stack: str = ""
    page: int = 1

class BreadcrumbAction(CallbackData, prefix="breadcrumb"):
    """
    Callback data для хлебных крошек
    position: позиция в навигационной цепочке
    target_section: целевой раздел для перехода
    """
    position: int
    target_section: str

class UserManagementAction(CallbackData, prefix="user_mgmt"):
    """
    Callback data для управления пользователем
    action: view, edit, grant_premium, revoke_premium, block, unblock, stats
    user_id: ID пользователя
    from_section: раздел, из которого был вызов
    page: страница, с которой был вызов
    """
    action: str
    user_id: int
    from_section: str = ""
    page: int = 1

class GiveawayManagementAction(CallbackData, prefix="gw_mgmt"):
    """
    Callback data для управления розыгрышем
    action: view, edit, finish, delete, participants, rig, export, stats
    giveaway_id: ID розыгрыша
    from_section: раздел, из которого был вызов
    page: страница, с которой был вызов
    """
    action: str
    giveaway_id: int
    from_section: str = ""
    page: int = 1
```

#### 1.2. Сервис управления контекстом навигации

Создадим сервис для управления контекстом навигации:

```python
# core/services/navigation_service.py
import json
from typing import List, Optional
from aiogram.fsm.context import FSMContext

class NavigationContext:
    """Сервис для управления контекстом навигации админ-панели"""
    
    def __init__(self, state: FSMContext):
        self.state = state
    
    async def push_context(self, context: str) -> List[str]:
        """Добавить контекст в стек и вернуть обновленный стек"""
        data = await self.state.get_data()
        context_stack = data.get("context_stack", [])
        
        # Добавляем новый контекст в стек
        context_stack.append(context)
        
        # Ограничиваем глубину стека, чтобы избежать переполнения
        if len(context_stack) > 10:
            context_stack = context_stack[-10:]
        
        await self.state.update_data(context_stack=context_stack)
        return context_stack
    
    async def pop_context(self) -> Optional[str]:
        """Извлечь последний контекст из стека"""
        data = await self.state.get_data()
        context_stack = data.get("context_stack", [])
        
        if context_stack:
            removed_context = context_stack.pop()
            await self.state.update_data(context_stack=context_stack)
            return removed_context
        
        return None
    
    async def get_current_context(self) -> str:
        """Получить текущий контекст"""
        data = await self.state.get_data()
        context_stack = data.get("context_stack", [])
        return context_stack[-1] if context_stack else "main"
    
    async def get_context_path(self) -> List[str]:
        """Получить полный путь контекста"""
        data = await self.state.get_data()
        return data.get("context_stack", [])
    
    async def clear_context(self):
        """Очистить весь стек контекста"""
        await self.state.update_data(context_stack=[])
    
    async def jump_to_context(self, target_context: str) -> bool:
        """Перейти к определенному контексту в стеке"""
        data = await self.state.get_data()
        context_stack = data.get("context_stack", [])
        
        if target_context in context_stack:
            # Найдем индекс целевого контекста и обрежем стек до него
            target_index = context_stack.index(target_context)
            new_stack = context_stack[:target_index + 1]
            await self.state.update_data(context_stack=new_stack)
            return True
        
        return False

class NavigationService:
    """Сервис навигации админ-панели"""
    
    def __init__(self, state: FSMContext):
        self.nav_context = NavigationContext(state)
    
    async def navigate_to(self, target_context: str):
        """Перейти к определенному контексту"""
        await self.nav_context.push_context(target_context)
    
    async def go_back(self):
        """Вернуться к предыдущему контексту"""
        return await self.nav_context.pop_context()
    
    async def get_breadcrumb_path(self) -> List[tuple[str, str]]:
        """Получить путь хлебных крошек в формате [(icon, text), ...]"""
        context_path = await self.nav_context.get_context_path()
        
        # Карта контекстов в читаемые названия и иконки
        context_map = {
            "main": ("👑", "Админ-панель"),
            "stats": ("📊", "Статистика"),
            "users": ("👥", "Пользователи"),
            "giveaways": ("🎮", "Розыгрыши"),
            "broadcast": ("📢", "Рассылка"),
            "security": ("🛡", "Безопасность"),
            "settings": ("⚙️", "Настройки"),
            "logs": ("📋", "Логи"),
            "user_search": ("🔍", "Поиск пользователя"),
            "user_list": ("📋", "Список пользователей"),
            "giveaway_list": ("📋", "Список розыгрышей"),
            "giveaway_detail": ("🎮", "Детали розыгрыша"),
            "user_detail": ("👤", "Детали пользователя")
        }
        
        breadcrumbs = []
        for context in context_path:
            icon, text = context_map.get(context, ("📍", context.title()))
            breadcrumbs.append((icon, text))
        
        return breadcrumbs
```

### 2. Улучшенная фабрика клавиатур

Обновим фабрику клавиатур для поддержки новых функций:

```python
# keyboards/admin_keyboards.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from typing import List, Optional

from .callback_data import (
    AdminMenuAction,
    StatsAction,
    UsersAction,
    GiveawaysAction,
    BroadcastAction,
    SecurityAction,
    SettingsAction,
    LogsAction,
    EnhancedNavigationAction,
    BreadcrumbAction,
    UserManagementAction,
    GiveawayManagementAction
)

class AdminKeyboardFactory:
    """Фабрика для создания унифицированных административных клавиатур"""
    
    @staticmethod
    def create_main_menu(is_super_admin: bool = False) -> InlineKeyboardMarkup:
        """Создание главной клавиатуры админ-панели с учетом прав доступа"""
        kb = InlineKeyboardBuilder()
        
        # Общие для всех админов кнопки
        kb.button(text="📊 Статистика", callback_data=AdminMenuAction(action="stats"))
        kb.button(text="👥 Пользователи", callback_data=AdminMenuAction(action="users"))
        kb.button(text="🎮 Розыгрыши", callback_data=AdminMenuAction(action="giveaways"))
        
        # Доступно только супер-админу
        if is_super_admin:
            kb.button(text="📢 Рассылка", callback_data=AdminMenuAction(action="broadcast"))
            kb.button(text="🛡 Безопасность", callback_data=AdminMenuAction(action="security"))
            kb.button(text="⚙️ Настройки", callback_data=AdminMenuAction(action="settings"))
            kb.button(text="📋 Логи", callback_data=AdminMenuAction(action="logs"))
        
        kb.button(text="🏠 Главное меню", callback_data=AdminMenuAction(action="main"))
        kb.adjust(2, 2, 2, 1)
        return kb.as_markup()
    
    @staticmethod
    def create_breadcrumb_navigation(breadcrumbs: List[tuple[str, str]], 
                                   current_action: Optional[str] = None) -> InlineKeyboardMarkup:
        """Создание клавиатуры с хлебными крошками"""
        if not breadcrumbs:
            return AdminKeyboardFactory.create_back_button("main")
        
        kb = InlineKeyboardBuilder()
        
        # Добавляем хлебные крошки как кнопки для быстрого перехода
        for i, (icon, text) in enumerate(breadcrumbs):
            if i == len(breadcrumbs) - 1:
                # Последний элемент - текущая страница, делаем его неактивным
                kb.button(text=f"{icon} {text}", callback_data="noop")
            else:
                # Делаем кнопку для перехода к этой точке
                kb.button(text=f"{icon} {text}", 
                         callback_data=BreadcrumbAction(position=i, target_section=text.lower().replace(" ", "_")))
        
        kb.adjust(len(breadcrumbs))
        
        # Добавляем основные кнопки навигации под хлебными крошками
        nav_kb = InlineKeyboardBuilder()
        if current_action:
            nav_kb.button(text="🔄 Обновить", callback_data=EnhancedNavigationAction(action="refresh"))
        nav_kb.button(text="🏠 Главное", callback_data=EnhancedNavigationAction(action="main"))
        nav_kb.button(text="🔙 Назад", callback_data=EnhancedNavigationAction(action="back"))
        
        nav_kb.adjust(3 if current_action else 2)
        
        # Комбинируем клавиатуры
        combined_kb = InlineKeyboardBuilder()
        combined_kb.attach(kb)
        combined_kb.attach(nav_kb)
        
        return combined_kb.as_markup()
    
    @staticmethod
    def create_back_button(action: str = "main") -> InlineKeyboardMarkup:
        """Создание клавиатуры с одной кнопкой 'Назад'"""
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 Назад", callback_data=AdminMenuAction(action=action))
        return kb.as_markup()
    
    @staticmethod
    def create_enhanced_user_list(users: List['User'], 
                                current_page: int, 
                                total_pages: int, 
                                total_count: int,
                                context: str = "main") -> InlineKeyboardMarkup:
        """Создание улучшенной клавиатуры списка пользователей с инлайн-кнопками"""
        kb = InlineKeyboardBuilder()
        
        # Добавляем пользователей в виде инлайн-кнопок
        for user in users:
            premium_emoji = "⭐" if user.is_premium else "👤"
            username = f"@{user.username}" if user.username else f"ID: {user.user_id}"
            status_emoji = "🔒" if hasattr(user, 'is_blocked') and user.is_blocked else ""
            
            kb.button(
                text=f"{premium_emoji}{status_emoji} {username}",
                callback_data=UserManagementAction(
                    action="view", 
                    user_id=user.user_id,
                    from_section=context,
                    page=current_page
                )
            )
        
        # Добавляем пагинацию
        kb.adjust(1)  # одна кнопка в ряду для удобства
        
        # Кнопки пагинации
        nav_kb = InlineKeyboardBuilder()
        if current_page > 1:
            nav_kb.button(
                text="⬅️", 
                callback_data=EnhancedNavigationAction(
                    action="back", 
                    page=current_page-1
                )
            )
        nav_kb.button(text=f"{current_page}/{total_pages}", callback_data="noop")
        if current_page < total_pages:
            nav_kb.button(
                text="➡️", 
                callback_data=EnhancedNavigationAction(
                    action="forward", 
                    page=current_page+1
                )
            )
        
        nav_kb.adjust(3)
        
        # Кнопки навигации
        context_kb = InlineKeyboardBuilder()
        context_kb.button(text="🏠 Главное", callback_data=AdminMenuAction(action="main"))
        context_kb.button(text="👥 Пользователи", callback_data=UsersAction(action="main"))
        context_kb.button(text="🔍 Поиск", callback_data=UsersAction(action="search"))
        context_kb.button(text="📋 Все", callback_data=UsersAction(action="list", page=1))
        context_kb.button(text="⭐ Премиум", callback_data=UsersAction(action="premium_list", page=1))
        context_kb.button(text="🔒 Заблокир.", callback_data=UsersAction(action="blocked_list", page=1))
        
        context_kb.adjust(3)
        
        # Комбинируем все клавиатуры
        combined_kb = InlineKeyboardBuilder()
        combined_kb.attach(kb)
        combined_kb.attach(nav_kb)
        combined_kb.attach(context_kb)
        
        return combined_kb.as_markup()
    
    @staticmethod
    def create_user_management_menu(user_id: int, 
                                  from_section: str = "users", 
                                  page: int = 1,
                                  is_super_admin: bool = False) -> InlineKeyboardMarkup:
        """Создание клавиатуры управления пользователем"""
        kb = InlineKeyboardBuilder()
        
        # Основные действия
        kb.button(
            text="⭐ Выдать премиум", 
            callback_data=UserManagementAction(
                action="grant_premium", 
                user_id=user_id,
                from_section=from_section,
                page=page
            )
        )
        kb.button(
            text="🚫 Снять премиум", 
            callback_data=UserManagementAction(
                action="revoke_premium", 
                user_id=user_id,
                from_section=from_section,
                page=page
            )
        )
        
        if is_super_admin:
            kb.button(
                text="🔒 Заблокировать", 
                callback_data=UserManagementAction(
                    action="block", 
                    user_id=user_id,
                    from_section=from_section,
                    page=page
                )
            )
            kb.button(
                text="✅ Разблокировать", 
                callback_data=UserManagementAction(
                    action="unblock", 
                    user_id=user_id,
                    from_section=from_section,
                    page=page
                )
            )
            kb.button(
                text="📊 Статистика", 
                callback_data=UserManagementAction(
                    action="stats", 
                    user_id=user_id,
                    from_section=from_section,
                    page=page
                )
            )
        
        # Кнопки навигации
        nav_kb = InlineKeyboardBuilder()
        nav_kb.button(text="🏠 Главное", callback_data=AdminMenuAction(action="main"))
        nav_kb.button(text="👥 Список", callback_data=UsersAction(action="list", page=page))
        nav_kb.button(text="🔙 Назад", callback_data=EnhancedNavigationAction(action="back"))
        
        nav_kb.adjust(3)
        
        # Комбинируем клавиатуры
        combined_kb = InlineKeyboardBuilder()
        combined_kb.attach(kb)
        combined_kb.attach(nav_kb)
        
        return combined_kb.as_markup()
    
    @staticmethod
    def create_enhanced_giveaways_list(giveaways: List['Giveaway'], 
                                    current_page: int, 
                                    total_pages: int, 
                                    total_count: int,
                                    context: str = "main") -> InlineKeyboardMarkup:
        """Создание улучшенной клавиатуры списка розыгрышей"""
        kb = InlineKeyboardBuilder()
        
        # Добавляем розыгрыши в виде инлайн-кнопок с ключевой информацией
        for giveaway in giveaways:
            status_emoji = {
                "active": "🟢",
                "finished": "🔴", 
                "pending": "🟡",
                "deleted": "🗑️"
            }.get(giveaway.status, "❓")
            
            # Получаем количество участников (предполагаем, что есть способ получить эту информацию)
            participants_count = getattr(giveaway, 'participants_count', 0)
            
            # Сокращаем текст приза для отображения
            prize_text = giveaway.prize_text[:30] + "..." if len(giveaway.prize_text) > 30 else giveaway.prize_text
            
            kb.button(
                text=f"{status_emoji} #{giveaway.id} {prize_text} | {participants_count} уч.",
                callback_data=GiveawayManagementAction(
                    action="view", 
                    giveaway_id=giveaway.id,
                    from_section=context,
                    page=current_page
                )
            )
        
        # Добавляем пагинацию
        kb.adjust(1)
        
        # Кнопки пагинации
        nav_kb = InlineKeyboardBuilder()
        if current_page > 1:
            nav_kb.button(
                text="⬅️", 
                callback_data=EnhancedNavigationAction(
                    action="back", 
                    page=current_page-1
                )
            )
        nav_kb.button(text=f"{current_page}/{total_pages}", callback_data="noop")
        if current_page < total_pages:
            nav_kb.button(
                text="➡️", 
                callback_data=EnhancedNavigationAction(
                    action="forward", 
                    page=current_page+1
                )
            )
        
        nav_kb.adjust(3)
        
        # Кнопки навигации
        context_kb = InlineKeyboardBuilder()
        context_kb.button(text="🏠 Главное", callback_data=AdminMenuAction(action="main"))
        context_kb.button(text="🎮 Розыгрыши", callback_data=GiveawaysAction(action="main"))
        context_kb.button(text="🔍 Поиск", callback_data=GiveawaysAction(action="search"))
        context_kb.button(text="📋 Все", callback_data=GiveawaysAction(action="list", page=1))
        context_kb.button(text="筛选 Фильтр", callback_data=GiveawaysAction(action="filter"))
        context_kb.button(text="📊 Статистика", callback_data=GiveawaysAction(action="stats"))
        
        context_kb.adjust(3)
        
        # Комбинируем все клавиатуры
        combined_kb = InlineKeyboardBuilder()
        combined_kb.attach(kb)
        combined_kb.attach(nav_kb)
        combined_kb.attach(context_kb)
        
        return combined_kb.as_markup()
    
    @staticmethod
    def create_giveaway_management_menu(giveaway_id: int, 
                                      from_section: str = "giveaways", 
                                      page: int = 1,
                                      is_super_admin: bool = False) -> InlineKeyboardMarkup:
        """Создание клавиатуры управления розыгрышем"""
        kb = InlineKeyboardBuilder()
        
        # Основные действия
        kb.button(
            text="🕹️ Завершить", 
            callback_data=GiveawayManagementAction(
                action="finish", 
                giveaway_id=giveaway_id,
                from_section=from_section,
                page=page
            )
        )
        kb.button(
            text="🗑 Удалить", 
            callback_data=GiveawayManagementAction(
                action="delete", 
                giveaway_id=giveaway_id,
                from_section=from_section,
                page=page
            )
        )
        kb.button(
            text="✏️ Редактировать", 
            callback_data=GiveawayManagementAction(
                action="edit", 
                giveaway_id=giveaway_id,
                from_section=from_section,
                page=page
            )
        )
        kb.button(
            text="👥 Участники", 
            callback_data=GiveawayManagementAction(
                action="participants", 
                giveaway_id=giveaway_id,
                from_section=from_section,
                page=page
            )
        )
        
        if is_super_admin:
            kb.button(
                text="🎲 Определить победителя", 
                callback_data=GiveawayManagementAction(
                    action="rig", 
                    giveaway_id=giveaway_id,
                    from_section=from_section,
                    page=page
                )
            )
            kb.button(
                text="📥 Экспорт", 
                callback_data=GiveawayManagementAction(
                    action="export", 
                    giveaway_id=giveaway_id,
                    from_section=from_section,
                    page=page
                )
            )
            kb.button(
                text="📊 Статистика", 
                callback_data=GiveawayManagementAction(
                    action="stats", 
                    giveaway_id=giveaway_id,
                    from_section=from_section,
                    page=page
                )
            )
        
        # Кнопки навигации
        nav_kb = InlineKeyboardBuilder()
        nav_kb.button(text="🏠 Главное", callback_data=AdminMenuAction(action="main"))
        nav_kb.button(text="🎮 Список", callback_data=GiveawaysAction(action="list", page=page))
        nav_kb.button(text="🔙 Назад", callback_data=EnhancedNavigationAction(action="back"))
        
        nav_kb.adjust(3)
        
        # Комбинируем клавиатуры
        combined_kb = InlineKeyboardBuilder()
        combined_kb.attach(kb)
        combined_kb.attach(nav_kb)
        
        return combined_kb.as_markup()

    @staticmethod
    def create_confirmation_keyboard(action_text: str, 
                                   confirm_callback: str, 
                                   cancel_callback: str,
                                   confirm_text: str = "✅ Подтвердить",
                                   cancel_text: str = "❌ Отмена") -> InlineKeyboardMarkup:
        """Создание клавиатуры подтверждения действия"""
        kb = InlineKeyboardBuilder()
        
        kb.button(text=confirm_text, callback_data=confirm_callback)
        kb.button(text=cancel_text, callback_data=cancel_callback)
        
        kb.adjust(2)
        
        return kb.as_markup()
```

## Реализация обработчиков

### 1. Базовые обработчики навигации

Создадим базовые обработчики для новой системы навигации:

```python
# handlers/super_admin/navigation_handlers.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from filters.is_super_admin import IsSuperAdmin
from keyboards.admin_keyboards import AdminKeyboardFactory, NavigationService

router = Router()

@router.callback_query(IsSuperAdmin(), F.data == "noop")
async def noop_handler(call: CallbackQuery):
    """Обработчик для неактивных кнопок (например, текущая страница в хлебных крошках)"""
    await call.answer("Вы уже находитесь на этой странице", show_alert=False)

@router.callback_query(IsSuperAdmin(), F.data.startswith("enh_nav"))
async def enhanced_navigation_handler(call: CallbackQuery, state: FSMContext):
    """Обработчик улучшенной навигации"""
    nav_service = NavigationService(state)
    
    # Получаем текущий контекст для определения действия
    current_context = await nav_service.nav_context.get_current_context()
    
    if call.data == "enh_nav:back":
        # Возвращаемся к предыдущему контексту
        prev_context = await nav_service.go_back()
        if prev_context:
            # Перенаправляем в соответствующий обработчик
            if prev_context == "users":
                from .users_handler import show_users_menu
                await show_users_menu(call)
            elif prev_context == "giveaways":
                from .giveaways_handler import show_giveaways_main_menu
                await show_giveaways_main_menu(call, call.db_session)
            elif prev_context == "stats":
                from .stats_handler import show_stats_main
                await show_stats_main(call, call.db_session)
            else:
                # По умолчанию возвращаемся в главное меню
                from .admin_base import admin_menu_callback
                await admin_menu_callback(call, call.db_session)
        else:
            # Если стек пуст, возвращаемся в главное меню
            from .admin_base import admin_menu_callback
            await admin_menu_callback(call, call.db_session)
    elif call.data == "enh_nav:main":
        # Переход в главное меню
        from .admin_base import admin_menu_callback
        await admin_menu_callback(call, call.db_session)
    elif call.data.startswith("enh_nav:forward"):
        # Обработка перехода вперед (например, следующая страница)
        # Извлекаем номер страницы из данных
        parts = call.data.split(":")
        if len(parts) >= 3:
            try:
                new_page = int(parts[2])
                # В зависимости от текущего контекста вызываем соответствующий обработчик
                if current_context == "user_list":
                    from .users_handler import show_users_list
                    await show_users_list(call, call.db_session)
                elif current_context == "giveaway_list":
                    from .giveaways_handler import show_giveaways_list
                    await show_giveaways_list(call, call.db_session)
            except ValueError:
                await call.answer("Ошибка при обработке страницы", show_alert=True)
    elif call.data == "enh_nav:refresh":
        # Обновление текущей страницы
        if current_context == "users":
            from .users_handler import show_users_menu
            await show_users_menu(call)
        elif current_context == "giveaways":
            from .giveaways_handler import show_giveaways_main_menu
            await show_giveaways_main_menu(call, call.db_session)
        elif current_context == "stats":
            from .stats_handler import show_stats_main
            await show_stats_main(call, call.db_session)
        else:
            from .admin_base import admin_menu_callback
            await admin_menu_callback(call, call.db_session)

@router.callback_query(IsSuperAdmin(), F.data.startswith("breadcrumb"))
async def breadcrumb_navigation_handler(call: CallbackQuery, state: FSMContext):
    """Обработчик навигации по хлебным крошкам"""
    nav_service = NavigationService(state)
    
    # Извлекаем данные из callback
    parts = call.data.split(":")
    if len(parts) >= 3:
        try:
            position = int(parts[1])
            target_section = parts[2]
            
            # Пытаемся перейти к целевому контексту
            success = await nav_service.nav_context.jump_to_context(target_section)
            
            if success:
                # Обновляем страницу в зависимости от целевого контекста
                if target_section in ["users", "user_list", "user_search"]:
                    from .users_handler import show_users_menu
                    await show_users_menu(call)
                elif target_section in ["giveaways", "giveaway_list"]:
                    from .giveaways_handler import show_giveaways_main_menu
                    await show_giveaways_main_menu(call, call.db_session)
                elif target_section == "stats":
                    from .stats_handler import show_stats_main
                    await show_stats_main(call, call.db_session)
                else:
                    from .admin_base import admin_menu_callback
                    await admin_menu_callback(call, call.db_session)
            else:
                await call.answer("Невозможно перейти к выбранному разделу", show_alert=True)
        except ValueError:
            await call.answer("Ошибка при обработке хлебной крошки", show_alert=True)
```

### 2. Обработчики управления пользователями

Обновим обработчики управления пользователями:

```python
# handlers/super_admin/enhanced_users_handler.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from filters.is_super_admin import IsSuperAdmin
from database.models.user import User
from keyboards.admin_keyboards import AdminKeyboardFactory, NavigationService
from keyboards.callback_data import UserManagementAction

router = Router()

class EnhancedUserState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_username = State()

@router.callback_query(IsSuperAdmin(), UserManagementAction.filter(F.action == "view"))
async def show_user_detail(call: CallbackQuery, 
                          callback_data: UserManagementAction, 
                          session: AsyncSession, 
                          state: FSMContext):
    """Показать детали пользователя"""
    nav_service = NavigationService(state)
    await nav_service.navigate_to("user_detail")
    
    user_id = callback_data.user_id
    
    # Ищем пользователя в базе данных
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь с таким ID не найден.", show_alert=True)
        return
    
    # Отображаем информацию о пользователе
    premium_status = "✅ Да" if user.is_premium else "❌ Нет"
    created_date = user.created_at.strftime("%d.%m.%Y %H:%M") if user.created_at else "Неизвестно"
    
    user_info = (
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"🆔 ID: <code>{user.user_id}</code>\n"
        f"👤 Имя: {user.full_name}\n"
        f"💬 Username: @{user.username or 'Не указан'}\n"
        f"⭐ Премиум: {premium_status}\n"
        f"📅 Дата регистрации: {created_date}\n"
    )
    
    # Создаем клавиатуру управления пользователем
    kb = AdminKeyboardFactory.create_user_management_menu(
        user_id=user.user_id,
        from_section=callback_data.from_section,
        page=callback_data.page,
        is_super_admin=True
    )
    
    await call.message.edit_text(user_info, reply_markup=kb)

@router.callback_query(IsSuperAdmin(), UserManagementAction.filter(F.action == "grant_premium"))
async def grant_premium_enhanced(call: CallbackQuery, 
                               callback_data: UserManagementAction, 
                               session: AsyncSession, 
                               state: FSMContext):
    """Выдать премиум пользователю"""
    nav_service = NavigationService(state)
    
    user_id = callback_data.user_id
    
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    # Проверка, есть ли уже премиум
    if user.is_premium:
        await call.answer("⚠️ У пользователя уже есть премиум.", show_alert=True)
        return
    
    # Подтверждение действия
    confirm_kb = AdminKeyboardFactory.create_confirmation_keyboard(
        action_text="Выдать премиум пользователю?",
        confirm_callback=UserManagementAction(
            action="grant_premium_confirmed", 
            user_id=user_id,
            from_section=callback_data.from_section,
            page=callback_data.page
        ).pack(),
        cancel_callback=UserManagementAction(
            action="view", 
            user_id=user_id,
            from_section=callback_data.from_section,
            page=callback_data.page
        ).pack()
    )
    
    await call.message.edit_text(
        f"⚠️ <b>Подтверждение действия</b>\n\n"
        f"Вы действительно хотите выдать премиум пользователю {user.full_name} (ID: {user.user_id})?",
        reply_markup=confirm_kb
    )

@router.callback_query(IsSuperAdmin(), UserManagementAction.filter(F.action == "grant_premium_confirmed"))
async def grant_premium_confirmed(call: CallbackQuery, 
                                callback_data: UserManagementAction, 
                                session: AsyncSession, 
                                state: FSMContext):
    """Подтвержденное выдача премиума пользователю"""
    user_id = callback_data.user_id
    
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    user.is_premium = True
    await session.commit()
    
    # Показываем результат
    await call.message.edit_text(
        f"✅ Премиум-статус выдан пользователю {user.full_name} (ID: {user.user_id})"
    )
    
    # Возвращаемся к просмотру пользователя через короткую задержку
    import asyncio
    await asyncio.sleep(1.5)
    
    # Показываем обновленную информацию о пользователе
    await show_user_detail(
        call, 
        UserManagementAction(
            action="view", 
            user_id=user_id,
            from_section=callback_data.from_section,
            page=callback_data.page
        ), 
        session, 
        state
    )

@router.callback_query(IsSuperAdmin(), UserManagementAction.filter(F.action == "revoke_premium"))
async def revoke_premium_enhanced(call: CallbackQuery, 
                                callback_data: UserManagementAction, 
                                session: AsyncSession, 
                                state: FSMContext):
    """Снять премиум с пользователя"""
    nav_service = NavigationService(state)
    
    user_id = callback_data.user_id
    
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    # Проверка, есть ли премиум
    if not user.is_premium:
        await call.answer("⚠️ У пользователя нет премиума.", show_alert=True)
        return
    
    # Подтверждение действия
    confirm_kb = AdminKeyboardFactory.create_confirmation_keyboard(
        action_text="Снять премиум с пользователя?",
        confirm_callback=UserManagementAction(
            action="revoke_premium_confirmed", 
            user_id=user_id,
            from_section=callback_data.from_section,
            page=callback_data.page
        ).pack(),
        cancel_callback=UserManagementAction(
            action="view", 
            user_id=user_id,
            from_section=callback_data.from_section,
            page=callback_data.page
        ).pack()
    )
    
    await call.message.edit_text(
        f"⚠️ <b>Подтверждение действия</b>\n\n"
        f"Вы действительно хотите снять премиум с пользователя {user.full_name} (ID: {user.user_id})?",
        reply_markup=confirm_kb
    )

@router.callback_query(IsSuperAdmin(), UserManagementAction.filter(F.action == "revoke_premium_confirmed"))
async def revoke_premium_confirmed(call: CallbackQuery, 
                                 callback_data: UserManagementAction, 
                                 session: AsyncSession, 
                                 state: FSMContext):
    """Подтвержденное снятие премиума с пользователя"""
    user_id = callback_data.user_id
    
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    user.is_premium = False
    await session.commit()
    
    # Показываем результат
    await call.message.edit_text(
        f"❌ Премиум-статус снят с пользователя {user.full_name} (ID: {user.user_id})"
    )
    
    # Возвращаемся к просмотру пользователя через короткую задержку
    import asyncio
    await asyncio.sleep(1.5)
    
    # Показываем обновленную информацию о пользователе
    await show_user_detail(
        call, 
        UserManagementAction(
            action="view", 
            user_id=user_id,
            from_section=callback_data.from_section,
            page=callback_data.page
        ), 
        session, 
        state
    )

@router.callback_query(IsSuperAdmin(), UserManagementAction.filter(F.action == "block"))
async def block_user_enhanced(call: CallbackQuery, 
                            callback_data: UserManagementAction, 
                            session: AsyncSession, 
                            state: FSMContext):
    """Заблокировать пользователя"""
    user_id = callback_data.user_id
    
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    # Подтверждение действия
    confirm_kb = AdminKeyboardFactory.create_confirmation_keyboard(
        action_text="Заблокировать пользователя?",
        confirm_callback=UserManagementAction(
            action="block_confirmed", 
            user_id=user_id,
            from_section=callback_data.from_section,
            page=callback_data.page
        ).pack(),
        cancel_callback=UserManagementAction(
            action="view", 
            user_id=user_id,
            from_section=callback_data.from_section,
            page=callback_data.page
        ).pack()
    )
    
    await call.message.edit_text(
        f"⚠️ <b>Подтверждение действия</b>\n\n"
        f"Вы действительно хотите заблокировать пользователя {user.full_name} (ID: {user.user_id})?\n\n"
        f"<b>Внимание:</b> Это действие может повлиять на доступ пользователя к боту.",
        reply_markup=confirm_kb
    )

@router.callback_query(IsSuperAdmin(), UserManagementAction.filter(F.action == "unblock"))
async def unblock_user_enhanced(call: CallbackQuery, 
                              callback_data: UserManagementAction, 
                              session: AsyncSession, 
                              state: FSMContext):
    """Разблокировать пользователя"""
    user_id = callback_data.user_id
    
    user = await session.get(User, user_id)
    if not user:
        await call.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    # Подтверждение действия
    confirm_kb = AdminKeyboardFactory.create_confirmation_keyboard(
        action_text="Разблокировать пользователя?",
        confirm_callback=UserManagementAction(
            action="unblock_confirmed", 
            user_id=user_id,
            from_section=callback_data.from_section,
            page=callback_data.page
        ).pack(),
        cancel_callback=UserManagementAction(
            action="view", 
            user_id=user_id,
            from_section=callback_data.from_section,
            page=callback_data.page
        ).pack()
    )
    
    await call.message.edit_text(
        f"⚠️ <b>Подтверждение действия</b>\n\n"
        f"Вы действительно хотите разблокировать пользователя {user.full_name} (ID: {user.user_id})?",
        reply_markup=confirm_kb
    )
```

## План поэтапной реализации

### Этап 1: Подготовительные работы (неделя 1)

1. **Обновление callback data** (`keyboards/callback_data.py`)
   - Добавление новых классов для улучшенной навигации
   - Тестирование совместимости с существующими обработчиками

2. **Создание сервиса навигации** (`core/services/navigation_service.py`)
   - Реализация классов `NavigationContext` и `NavigationService`
   - Написание юнит-тестов для проверки работы стека контекста

3. **Обновление фабрики клавиатур** (`keyboards/admin_keyboards.py`)
   - Добавление методов для создания улучшенных клавиатур
   - Обеспечение обратной совместимости

### Этап 2: Реализация базовой навигации (неделя 2)

1. **Создание обработчиков навигации** (`handlers/super_admin/navigation_handlers.py`)
   - Реализация обработчиков для хлебных крошек
   - Добавление поддержки контекстно-зависимого возврата

2. **Интеграция навигации в существующие обработчики**
   - Обновление `users_handler.py` для использования новой навигации
   - Добавление хлебных крошек в основные разделы

### Этап 3: Улучшение управления пользователями (неделя 3)

1. **Реализация улучшенных обработчиков пользователей**
   - Создание `enhanced_users_handler.py` с новыми возможностями
   - Добавление подтверждения для критических действий

2. **Обновление отображения списка пользователей**
   - Реализация инлайн-кнопок для пользователей
   - Добавление пагинации и фильтрации

### Этап 4: Улучшение управления розыгрышами (неделя 4)

1. **Обновление обработчиков розыгрышей**
   - Добавление улучшенного отображения списка розыгрышей
   - Реализация массовых действий

2. **Интеграция с системой навигации**
   - Обеспечение согласованной навигации между разделами

### Этап 5: Тестирование и отладка (неделя 5)

1. **Комплексное тестирование**
   - Проверка всех сценариев навигации
   - Тестирование обработки ошибок

2. **Оптимизация производительности**
   - Оптимизация запросов к базе данных
   - Улучшение скорости отклика интерфейса

### Этап 6: Документация и деплой (неделя 6)

1. **Создание документации**
   - Документация для разработчиков
   - Руководство по использованию для администраторов

2. **Деплой и мониторинг**
   - Развертывание в тестовой среде
   - Мониторинг стабильности работы

## Ожидаемые результаты

После реализации всех этапов плана будет достигнуто:

1. **Улучшенная навигация**:
   - Хлебные крошки для понимания текущего местоположения
   - Контекстно-зависимые кнопки возврата
   - Быстрый доступ к любому уровню иерархии

2. **Улучшенный UX**:
   - Инлайн-кнопки для быстрого доступа к объектам
   - Подтверждение критических действий
   - Визуальная обратная связь

3. **Расширенная функциональность**:
   - Возможность массового управления
   - Улучшенные фильтры и сортировка
   - Расширенная статистика

4. **Улучшенная масштабируемость**:
   - Модульная архитектура системы навигации
   - Простота добавления новых разделов
   - Единый подход к управлению контекстом

Этот план обеспечивает постепенное и безопасное внедрение улучшений без нарушения текущей функциональности системы.