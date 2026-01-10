import time
from collections import defaultdict
from typing import Dict


class RateLimiter:
    def __init__(self, max_requests: int = 10, window: int = 60):
        """
        Инициализация рейт-лимитера
        :param max_requests: максимальное количество запросов за окно
        :param window: размер окна в секундах
        """
        self.max_requests = max_requests
        self.window = window
        self.requests: Dict[int, list] = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> bool:
        """
        Проверяет, разрешен ли запрос для пользователя
        :param user_id: ID пользователя
        :return: True, если запрос разрешен, иначе False
        """
        now = time.time()
        # Удаляем старые запросы
        self.requests[user_id] = [req_time for req_time in self.requests[user_id] if now - req_time < self.window]
        
        if len(self.requests[user_id]) < self.max_requests:
            self.requests[user_id].append(now)
            return True
        
        return False
    
    def get_reset_time(self, user_id: int) -> float:
        """
        Возвращает время до сброса ограничения
        :param user_id: ID пользователя
        :return: время до сброса в секундах
        """
        if user_id not in self.requests or not self.requests[user_id]:
            return 0
        
        oldest_request = min(self.requests[user_id])
        reset_time = oldest_request + self.window
        now = time.time()
        
        return max(0, reset_time - now)


# Глобальный лимитер для админ-панели
admin_rate_limiter = RateLimiter(max_requests=20, window=60)  # 20 запросов в минуту для админов