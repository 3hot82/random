# keyboards/callback_data.py
from aiogram.filters.callback_data import CallbackData

class AdminAction(CallbackData, prefix="adm"):
    """
    Данные для админских кнопок.
    sig - это HMAC подпись.
    """
    action: str
    id: int
    sig: str


class GiveawayAction(CallbackData, prefix="gw"):
    """
    Callback data для действий с розыгрышем
    action: manage, view, edit, finish, delete, rig, participants
    giveaway_id: ID розыгрыша
    """
    action: str
    giveaway_id: int

class JoinAction(CallbackData, prefix="join"):
    """
    Данные для кнопки участия.
    """
    giveaway_id: int

# Новые структурированные callback data для иерархического меню
class StatsAction(CallbackData, prefix="stats"):
    """
    Callback data для раздела статистики
    action: main, growth, premium, giveaways, participations, refresh
    """
    action: str

class UsersAction(CallbackData, prefix="users"):
    """
    Callback data для раздела пользователей
    action: main, search, list, manage, grant_premium, revoke_premium, block, unblock, stats, premium_list, blocked_list
    user_id: int (опционально)
    page: int (опционально)
    """
    action: str
    user_id: int = 0
    page: int = 1

class GiveawaysAction(CallbackData, prefix="giveaways"):
    """
    Callback data для раздела розыгрышей
    action: main, list, search, finish, delete, rig, edit, view, participants
    giveaway_id: int (опционально)
    """
    action: str
    giveaway_id: int = 0

class BroadcastAction(CallbackData, prefix="broadcast"):
    """
    Callback data для рассылки
    action: main, create, status, confirm, target
    target: all, premium, regular (для target)
    """
    action: str
    target: str = ""

class SecurityAction(CallbackData, prefix="security"):
    """
    Callback data для безопасности
    action: main, suspicious, block_ip, logs
    """
    action: str

class SettingsAction(CallbackData, prefix="settings"):
    """
    Callback data для настроек
    action: main, general, security, backup
    """
    action: str

class LogsAction(CallbackData, prefix="logs"):
    """
    Callback data для логов
    action: main, users, errors, admin, export
    """
    action: str

class GiveawaysPagination(CallbackData, prefix="gwpag"):
    """
    Callback data для пагинации в списках розыгрышей
    action: prev, next, goto
    page: номер страницы
    filter_status: фильтр по статусу (active, finished, etc.)
    """
    action: str
    page: int = 1
    filter_status: str = ""


class BaseNavigationAction(CallbackData, prefix="nav"):
    """
    Базовая Callback data для навигации
    action: back, main_menu, section
    section: имя раздела для перехода
    """
    action: str
    section: str = ""


class UserMenuAction(CallbackData, prefix="user_menu"):
    """
    Callback data для пользовательского меню
    action: dashboard, giveaways_hub, my_channels, my_giveaways, premium
    """
    action: str


class AdminMenuAction(CallbackData, prefix="admin_menu"):
    """
    Callback data для админ-меню
    action: main, stats, users, giveaways, broadcast, security, settings, logs
    """
    action: str


class UserListAction(CallbackData, prefix="user_list"):
    """
    Callback data для списка пользователей
    action: list, search, manage, premium_list, blocked_list
    user_id: int (опционально)
    page: int (опционально)
    """
    action: str
    user_id: int = 0
    page: int = 1


class PaginationAction(CallbackData, prefix="pagination"):
    """
    Callback data для пагинации
    action: prev, next, goto
    page: номер страницы
    """
    action: str
    page: int = 1
