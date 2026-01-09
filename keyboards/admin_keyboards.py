from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

from .callback_data import (
    AdminMenuAction,
    StatsAction,
    UsersAction,
    GiveawaysAction,
    BroadcastAction,
    SecurityAction,
    SettingsAction,
    LogsAction
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
    def create_back_button(action: str = "main") -> InlineKeyboardMarkup:
        """Создание клавиатуры с одной кнопкой 'Назад'"""
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 Назад", callback_data=AdminMenuAction(action=action))
        return kb.as_markup()
    
    @staticmethod
    def create_stats_menu() -> InlineKeyboardMarkup:
        """Создание клавиатуры раздела статистики"""
        kb = InlineKeyboardBuilder()
        kb.button(text="📊 Общая статистика", callback_data=StatsAction(action="main"))
        kb.button(text="📈 Рост пользователей", callback_data=StatsAction(action="growth"))
        kb.button(text="⭐ Премиум статистика", callback_data=StatsAction(action="premium"))
        kb.button(text="🎮 Розыгрыши", callback_data=StatsAction(action="giveaways"))
        kb.button(text="🎯 Участия", callback_data=StatsAction(action="participations"))
        kb.button(text="🔄 Обновить", callback_data=StatsAction(action="refresh"))
        kb.button(text="🔙 Назад", callback_data=AdminMenuAction(action="main"))
        kb.adjust(2, 2, 2, 1)
        return kb.as_markup()
    
    @staticmethod
    def create_users_menu(is_super_admin: bool = False) -> InlineKeyboardMarkup:
        """Создание клавиатуры раздела управления пользователями"""
        kb = InlineKeyboardBuilder()
        kb.button(text="🔍 Поиск пользователя", callback_data=UsersAction(action="search"))
        kb.button(text="📋 Список пользователей", callback_data=UsersAction(action="list", page=1))
        kb.button(text="⭐ Премиум-пользователи", callback_data=UsersAction(action="premium_list", page=1))
        
        # Только для супер-админа
        if is_super_admin:
            kb.button(text="🔒 Заблокированные пользователи", callback_data=UsersAction(action="blocked_list", page=1))
        
        kb.button(text="🔙 Назад", callback_data=AdminMenuAction(action="main"))
        kb.adjust(1, 1, 1)
        return kb.as_markup()
    
    @staticmethod
    def create_giveaways_menu(is_super_admin: bool = False) -> InlineKeyboardMarkup:
        """Создание клавиатуры раздела розыгрышей"""
        kb = InlineKeyboardBuilder()
        kb.button(text="📋 Все розыгрыши", callback_data=GiveawaysAction(action="list", page=1))
        kb.button(text="🔍 Поиск розыгрыша", callback_data=GiveawaysAction(action="search"))
        
        # Только для супер-админа
        if is_super_admin:
            kb.button(text="筛选 Фильтр", callback_data=GiveawaysAction(action="filter"))
            kb.button(text="📊 Статистика розыгрышей", callback_data=GiveawaysAction(action="stats"))
            kb.button(text="➕ Создать розыгрыш", callback_data=GiveawaysAction(action="create"))
        
        kb.button(text="🔙 Назад", callback_data=AdminMenuAction(action="main"))
        kb.adjust(1, 1, 1, 1)
        return kb.as_markup()
    
    @staticmethod
    def create_broadcast_menu() -> InlineKeyboardMarkup:
        """Создание клавиатуры раздела рассылки (только для супер-админа)"""
        kb = InlineKeyboardBuilder()
        kb.button(text="📝 Создать рассылку", callback_data=BroadcastAction(action="create"))
        kb.button(text="📊 Статус рассылки", callback_data=BroadcastAction(action="status"))
        kb.button(text="🔙 Назад", callback_data=AdminMenuAction(action="main"))
        kb.adjust(2, 1)
        return kb.as_markup()
    
    @staticmethod
    def create_security_menu() -> InlineKeyboardMarkup:
        """Создание клавиатуры раздела безопасности (только для супер-админа)"""
        kb = InlineKeyboardBuilder()
        kb.button(text="🚨 Подозрительные действия", callback_data=SecurityAction(action="suspicious"))
        kb.button(text="🔒 Блокировка IP", callback_data=SecurityAction(action="block_ip"))
        kb.button(text="📋 Логи безопасности", callback_data=SecurityAction(action="logs"))
        kb.button(text="🔙 Назад", callback_data=AdminMenuAction(action="main"))
        kb.adjust(2, 1)
        return kb.as_markup()
    
    @staticmethod
    def create_settings_menu() -> InlineKeyboardMarkup:
        """Создание клавиатуры раздела настроек (только для супер-админа)"""
        kb = InlineKeyboardBuilder()
        kb.button(text="⚙️ Общие настройки", callback_data=SettingsAction(action="general"))
        kb.button(text="🔐 Настройки безопасности", callback_data=SettingsAction(action="security"))
        kb.button(text="💾 Резервное копирование", callback_data=SettingsAction(action="backup"))
        kb.button(text="🔙 Назад", callback_data=AdminMenuAction(action="main"))
        kb.adjust(2, 1)
        return kb.as_markup()
    
    @staticmethod
    def create_logs_menu() -> InlineKeyboardMarkup:
        """Создание клавиатуры раздела логов (только для супер-админа)"""
        kb = InlineKeyboardBuilder()
        kb.button(text="📋 Логи пользователей", callback_data=LogsAction(action="users"))
        kb.button(text="🔧 Логи ошибок", callback_data=LogsAction(action="errors"))
        kb.button(text="👤 Логи администраторов", callback_data=LogsAction(action="admin"))
        kb.button(text="📤 Экспорт логов", callback_data=LogsAction(action="export"))
        kb.button(text="🔙 Назад", callback_data=AdminMenuAction(action="main"))
        kb.adjust(2, 2, 1)
        return kb.as_markup()

    @staticmethod
    def create_giveaway_detail_menu(giveaway_id: int, is_super_admin: bool = False) -> InlineKeyboardMarkup:
        """Создание клавиатуры управления конкретным розыгрышем"""
        kb = InlineKeyboardBuilder()
        kb.button(text="🕹️ Завершить", callback_data=GiveawaysAction(action="finish", giveaway_id=giveaway_id))
        kb.button(text="🗑 Удалить", callback_data=GiveawaysAction(action="delete", giveaway_id=giveaway_id))
        kb.button(text="✏️ Редактировать", callback_data=GiveawaysAction(action="edit", giveaway_id=giveaway_id))
        kb.button(text="👥 Участники", callback_data=GiveawaysAction(action="participants", giveaway_id=giveaway_id))
        
        # Только для супер-админа
        if is_super_admin:
            kb.button(text="🎲 Определить победителя", callback_data=GiveawaysAction(action="rig", giveaway_id=giveaway_id))
            kb.button(text="📥 Экспорт", callback_data=GiveawaysAction(action="export", giveaway_id=giveaway_id))
            kb.button(text="📋 Статистика", callback_data=GiveawaysAction(action="stats", giveaway_id=giveaway_id))
        
        kb.button(text="🔙 Назад к списку", callback_data=GiveawaysAction(action="list", page=1))
        kb.adjust(1, 1, 1, 1, 1, 1, 1)
        return kb.as_markup()
    
    @staticmethod
    def create_user_detail_menu(user_id: int, is_super_admin: bool = False) -> InlineKeyboardMarkup:
        """Создание клавиатуры управления конкретным пользователем"""
        kb = InlineKeyboardBuilder()
        kb.button(text="⭐ Выдать премиум", callback_data=UsersAction(action="grant_premium", user_id=user_id))
        kb.button(text="🚫 Снять премиум", callback_data=UsersAction(action="revoke_premium", user_id=user_id))
        
        # Только для супер-админа
        if is_super_admin:
            kb.button(text="🔒 Заблокировать", callback_data=UsersAction(action="block", user_id=user_id))
            kb.button(text="✅ Разблокировать", callback_data=UsersAction(action="unblock", user_id=user_id))
            kb.button(text="📊 Статистика пользователя", callback_data=UsersAction(action="stats", user_id=user_id))
        
        kb.button(text="🔙 Назад к списку", callback_data=UsersAction(action="list", page=1))
        kb.adjust(2, 2, 2)
        return kb.as_markup()