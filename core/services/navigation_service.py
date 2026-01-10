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
        
        # Карта контекстов в читаемые названия иконки
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