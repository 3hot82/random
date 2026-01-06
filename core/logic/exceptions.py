# core/logic/exceptions.py

class BotError(Exception):
    """Базовый класс ошибок бота"""
    pass

class SecurityError(BotError):
    """Ошибка проверки подписи или прав"""
    pass

class GiveawayInvalidError(BotError):
    """Ошибка валидации данных розыгрыша"""
    pass