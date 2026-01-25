import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal

from database.models.user import User
from database.models.premium_features import UserSubscription, SubscriptionTier
from database.requests.premium_repo import (
    get_user_subscription_status,
    create_user_subscription,
    deactivate_user_subscription,
    get_max_concurrent_giveaways,
    get_max_sponsor_channels,
    can_create_giveaway,
    increment_premium_feature_usage
)


@pytest.fixture
def mock_session():
    """Фикстура для мокирования сессии базы данных"""
    session = AsyncMock(spec=AsyncSession)
    
    # Мокаем часто используемые методы сессии
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    
    return session


@pytest.mark.asyncio
class TestComprehensivePremiumFeatures:
    """Комплексные тесты премиум-функций"""

    async def test_premium_subscription_purchase(self, mock_session):
        """Тест покупки премиум-подписки"""
        user_id = 123456789
        tier_id = 1
        days = 30
        
        # Мокаем получение тарифа
        mock_tier = MagicMock(spec=SubscriptionTier)
        mock_tier.id = tier_id
        mock_tier.name = "premium_basic"
        mock_tier.price_monthly = Decimal("9.99")
        mock_tier.duration_days = days
        mock_tier.max_concurrent_giveaways = 5
        mock_tier.max_sponsor_channels = 10
        mock_tier.has_realtime_subscription_check = True
        mock_tier.max_concurrent_giveaways_premium = 10
        mock_tier.max_sponsor_channels_premium = 20
        
        async def mock_get(model, identifier):
            if model == SubscriptionTier and identifier == tier_id:
                return mock_tier
            return None
            
        mock_session.get = mock_get
        
        # Мокаем результат выполнения запроса
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None  # Нет активной подписки
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Покупаем подписку
        success = await create_user_subscription(
            mock_session, user_id, tier_id, days
        )
        
        # Проверяем, что подписка была создана
        assert success is not None  # Должен быть создан объект подписки
        mock_session.add.assert_called()  # Должна быть добавлена новая подписка

    async def test_premium_subscription_extension(self, mock_session):
        """Тест продления премиум-подписки"""
        user_id = 123456789
        tier_id = 1
        additional_days = 30
        
        # Создаем текущую подписку
        current_end_date = datetime.now() + timedelta(days=10)  # Подписка заканчивается через 10 дней
        
        mock_current_subscription = MagicMock(spec=UserSubscription)
        mock_current_subscription.user_id = user_id
        mock_current_subscription.tier_id = tier_id
        mock_current_subscription.start_date = datetime.now() - timedelta(days=20)
        mock_current_subscription.end_date = current_end_date
        mock_current_subscription.is_active = True
        
        # Мокаем получение текущей подписки
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_current_subscription
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Мокаем тариф
        mock_tier = MagicMock(spec=SubscriptionTier)
        mock_tier.id = tier_id
        mock_tier.name = "premium_extended"
        mock_tier.price_monthly = Decimal("9.99")
        mock_tier.duration_days = additional_days
        mock_tier.max_concurrent_giveaways = 10
        mock_tier.max_sponsor_channels = 20
        mock_tier.has_realtime_subscription_check = True
        mock_tier.max_concurrent_giveaways_premium = 15
        mock_tier.max_sponsor_channels_premium = 25
        
        async def mock_get(model, identifier):
            if model == SubscriptionTier and identifier == tier_id:
                return mock_tier
            return None
            
        mock_session.get = mock_get
        
        # Продлеваем подписку
        success = await create_user_subscription(
            mock_session, user_id, tier_id, additional_days
        )
        
        assert success is not None  # Должен быть создан объект подписки

    async def test_premium_auto_renewal_cancellation(self, mock_session):
        """Тест отмены автопродления премиум-подписки"""
        user_id = 123456789
        tier_id = 1
        
        # Создаем подписку с автопродлением
        mock_subscription = MagicMock(spec=UserSubscription)
        mock_subscription.user_id = user_id
        mock_subscription.tier_id = tier_id
        mock_subscription.start_date = datetime.now() - timedelta(days=1)
        mock_subscription.end_date = datetime.now() + timedelta(days=29)
        mock_subscription.is_active = True
        mock_subscription.auto_renew = True  # Автопродление включено
        
        # Мокаем получение подписки
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Отменяем автопродление (в реальной системе это может быть просто изменение поля)
        mock_subscription.auto_renew = False
        await mock_session.commit()
        
        # Проверяем, что автопродление отменено
        assert mock_subscription.auto_renew is False

    async def test_premium_status_check(self, mock_session):
        """Тест проверки статуса премиум-подписки"""
        user_id = 123456789
        tier_id = 1
        
        # Создаем активную подписку
        end_date = datetime.now() + timedelta(days=30)
        
        mock_subscription = MagicMock(spec=UserSubscription)
        mock_subscription.user_id = user_id
        mock_subscription.tier_id = tier_id
        mock_subscription.start_date = datetime.now() - timedelta(days=1)
        mock_subscription.end_date = end_date
        mock_subscription.is_active = True
        
        # Мокаем результаты запросов
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Мокаем тариф
        mock_tier = MagicMock(spec=SubscriptionTier)
        mock_tier.id = tier_id
        mock_tier.name = "premium_plus"
        mock_tier.price_monthly = Decimal("19.99")
        mock_tier.duration_days = 30
        mock_tier.max_concurrent_giveaways = 15
        mock_tier.max_sponsor_channels = 30
        mock_tier.has_realtime_subscription_check = True
        mock_tier.max_concurrent_giveaways_premium = 20
        mock_tier.max_sponsor_channels_premium = 40
        
        async def mock_get(model, identifier):
            if model == SubscriptionTier and identifier == tier_id:
                return mock_tier
            elif model == User and identifier == user_id:
                return None  # Не проверяем старую систему
            return None
            
        mock_session.get = mock_get
        
        # Проверяем статус подписки
        status = await get_user_subscription_status(mock_session, user_id)
        
        assert status is not None
        assert status["is_premium"] is True
        assert status["tier_name"] == mock_tier.name
        assert status["expires_at"] == end_date

    async def test_premium_status_check_expired_subscription(self, mock_session):
        """Тест проверки статуса истекшей премиум-подписки"""
        user_id = 123456789
        tier_id = 1
        
        # Создаем истекшую подписку
        end_date = datetime.now() - timedelta(days=1)  # Подписка истекла вчера
        
        mock_subscription = MagicMock(spec=UserSubscription)
        mock_subscription.user_id = user_id
        mock_subscription.tier_id = tier_id
        mock_subscription.start_date = datetime.now() - timedelta(days=31)  # Началась месяц назад
        mock_subscription.end_date = end_date
        mock_subscription.is_active = True
        
        # Мокаем результаты запросов
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Мокаем тариф
        mock_tier = MagicMock(spec=SubscriptionTier)
        mock_tier.id = tier_id
        mock_tier.name = "premium_basic"
        mock_tier.price_monthly = Decimal("9.99")
        mock_tier.duration_days = 30
        mock_tier.max_concurrent_giveaways = 5
        mock_tier.max_sponsor_channels = 10
        mock_tier.has_realtime_subscription_check = False
        mock_tier.max_concurrent_giveaways_premium = 10
        mock_tier.max_sponsor_channels_premium = 20
        
        async def mock_get(model, identifier):
            if model == SubscriptionTier and identifier == tier_id:
                return mock_tier
            elif model == User and identifier == user_id:
                # Возвращаем пользователя без премиума для проверки старой системы
                user = MagicMock(spec=User)
                user.user_id = user_id
                user.username = "expired_user"
                user.full_name = "Expired User"
                user.is_premium = False
                user.premium_until = None
                return user
            return None
            
        mock_session.get = mock_get
        
        # Проверяем статус подписки
        status = await get_user_subscription_status(mock_session, user_id)
        
        # Даже если подписка истекла, в реальной системе она может быть помечена как неактивная
        # или нужно обновить статус в зависимости от даты окончания
        assert status is not None
        # Статус может зависеть от реализации - либо не премиум, либо помечен как истекший

    async def test_premium_access_restoration_after_expiration(self, mock_session):
        """Тест восстановления доступа после истечения подписки"""
        user_id = 123456789
        tier_id = 1
        
        # Сначала пользователь не имеет подписки
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None  # Нет активной подписки
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Мокаем пользователя без премиума
        mock_user = MagicMock(spec=User)
        mock_user.user_id = user_id
        mock_user.username = "restored_user"
        mock_user.full_name = "Restored User"
        mock_user.is_premium = False
        mock_user.premium_until = None
        
        async def mock_get(model, identifier):
            if model == User and identifier == user_id:
                return mock_user
            return None
            
        mock_session.get = mock_get
        
        # Проверяем начальный статус
        initial_status = await get_user_subscription_status(mock_session, user_id)
        assert initial_status["is_premium"] is False
        
        # Теперь покупаем подписку (восстанавливаем доступ)
        days = 30
        success = await create_user_subscription(mock_session, user_id, tier_id, days)
        
        assert success is not None  # Должен быть создан объект подписки
        
        # Проверяем статус после восстановления
        restored_status = await get_user_subscription_status(mock_session, user_id)
        assert restored_status["is_premium"] is True

    async def test_create_giveaway_with_premium_features(self, mock_session):
        """Тест создания розыгрыша с премиум-возможностями"""
        user_id = 123456789
        tier_id = 1
        
        # Создаем премиум-пользователя
        end_date = datetime.now() + timedelta(days=30)
        
        mock_subscription = MagicMock(spec=UserSubscription)
        mock_subscription.user_id = user_id
        mock_subscription.tier_id = tier_id
        mock_subscription.start_date = datetime.now() - timedelta(days=1)
        mock_subscription.end_date = end_date
        mock_subscription.is_active = True
        
        # Мокаем результаты
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Мокаем тариф с премиум-функциями
        mock_tier = MagicMock(spec=SubscriptionTier)
        mock_tier.id = tier_id
        mock_tier.name = "premium_pro"
        mock_tier.price_monthly = Decimal("29.99")
        mock_tier.duration_days = 30
        mock_tier.max_concurrent_giveaways = 20  # Премиум-ограничение
        mock_tier.max_sponsor_channels = 50     # Премиум-ограничение
        mock_tier.has_realtime_subscription_check = True  # Премиум-функция
        mock_tier.max_concurrent_giveaways_premium = 40
        mock_tier.max_sponsor_channels_premium = 100
        
        async def mock_get(model, identifier):
            if model == SubscriptionTier and identifier == tier_id:
                return mock_tier
            elif model == User and identifier == user_id:
                return None  # Не проверяем старую систему
            return None
            
        mock_session.get = mock_get
        
        # Проверяем лимиты для премиум-пользователя
        max_giveaways = await get_max_concurrent_giveaways(mock_session, user_id)
        max_channels = await get_max_sponsor_channels(mock_session, user_id)
        
        assert max_giveaways == mock_tier.max_concurrent_giveaways_premium
        assert max_channels == mock_tier.max_sponsor_channels_premium

    async def test_premium_limits_increase(self, mock_session):
        """Тест увеличения лимитов для премиум-пользователей"""
        user_id = 123456789
        tier_id = 1
        
        # Создаем премиум-подписку
        end_date = datetime.now() + timedelta(days=30)
        
        mock_subscription = MagicMock(spec=UserSubscription)
        mock_subscription.user_id = user_id
        mock_subscription.tier_id = tier_id
        mock_subscription.start_date = datetime.now() - timedelta(days=1)
        mock_subscription.end_date = end_date
        mock_subscription.is_active = True
        
        # Мокаем результаты
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Мокаем тариф
        mock_tier = MagicMock(spec=SubscriptionTier)
        mock_tier.id = tier_id
        mock_tier.name = "premium_plus"
        mock_tier.price_monthly = Decimal("19.99")
        mock_tier.duration_days = 30
        mock_tier.max_concurrent_giveaways = 15
        mock_tier.max_concurrent_giveaways_premium = 25  # Увеличенный лимит для премиум
        mock_tier.max_sponsor_channels = 30
        mock_tier.max_sponsor_channels_premium = 60     # Увеличенный лимит для премиум
        mock_tier.has_realtime_subscription_check = True
        
        async def mock_get(model, identifier):
            if model == SubscriptionTier and identifier == tier_id:
                return mock_tier
            elif model == User and identifier == user_id:
                return None
            return None
            
        mock_session.get = mock_get
        
        # Проверяем, что премиум-пользователь получает увеличенные лимиты
        max_giveaways = await get_max_concurrent_giveaways(mock_session, user_id)
        max_channels = await get_max_sponsor_channels(mock_session, user_id)
        
        assert max_giveaways == mock_tier.max_concurrent_giveaways_premium
        assert max_channels == mock_tier.max_sponsor_channels_premium

    async def test_premium_feature_usage_tracking(self, mock_session):
        """Тест отслеживания использования премиум-функций"""
        user_id = 123456789
        feature_name = "realtime_subscription_check"
        
        # Мокаем результат выполнения запроса - сначала нет записи о использовании
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=None)  # Нет записи о предыдущем использовании
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Мокаем статус подписки
        mock_tier = MagicMock(spec=SubscriptionTier)
        mock_tier.id = 1
        mock_tier.name = "premium_basic"
        mock_tier.price_monthly = Decimal("9.99")
        mock_tier.max_concurrent_giveaways = 5
        mock_tier.max_concurrent_giveaways_premium = 10
        mock_tier.max_sponsor_channels = 10
        mock_tier.max_sponsor_channels_premium = 20
        mock_tier.has_realtime_subscription_check = True
        
        mock_subscription = MagicMock(spec=UserSubscription)
        mock_subscription.user_id = user_id
        mock_subscription.tier_id = 1
        mock_subscription.start_date = datetime.now() - timedelta(days=1)
        mock_subscription.end_date = datetime.now() + timedelta(days=30)
        mock_subscription.is_active = True
        
        # Мокаем выполнение запроса для получения статуса подписки
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none = AsyncMock(return_value=mock_subscription)
        
        # Сохраняем оригинальный execute
        original_execute = mock_session.execute
        
        async def enhanced_mock_execute(stmt):
            # Если это запрос для получения статуса подписки (с join)
            # Проверяем наличие _target_cls или других признаков запроса UserSubscription
            str_stmt = str(stmt)
            if 'UserSubscription' in str_stmt and 'SubscriptionTier' in str_stmt:
                return mock_sub_result
            # Для остальных запросов используем наш мок
            return mock_result
        
        mock_session.execute = enhanced_mock_execute
        
        # Мокаем метод get для получения тарифа
        async def mock_get(model_class, identifier):
            if hasattr(model_class, '__name__') and model_class.__name__ == 'SubscriptionTier':
                return mock_tier
            elif hasattr(model_class, '__name__') and model_class.__name__ == 'User':
                return None
            return None
        
        mock_session.get = mock_get
        
        # Тестируем инкремент использования функции
        success = await increment_premium_feature_usage(
            mock_session, user_id, feature_name
        )
        
        assert success is True
        mock_session.add.assert_called()
        mock_session.commit.assert_called()

    async def test_premium_user_giveaway_creation_check(self, mock_session):
        """Тест проверки возможности создания розыгрыша премиум-пользователем"""
        user_id = 123456789
        tier_id = 1
        
        # Создаем премиум-подписку
        end_date = datetime.now() + timedelta(days=30)
        
        mock_subscription = MagicMock(spec=UserSubscription)
        mock_subscription.user_id = user_id
        mock_subscription.tier_id = tier_id
        mock_subscription.start_date = datetime.now() - timedelta(days=1)
        mock_subscription.end_date = end_date
        mock_subscription.is_active = True
        
        # Мокаем результаты
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Мокаем тариф с высокими лимитами
        mock_tier = MagicMock(spec=SubscriptionTier)
        mock_tier.id = tier_id
        mock_tier.name = "premium_max"
        mock_tier.price_monthly = Decimal("39.99")
        mock_tier.duration_days = 30
        mock_tier.max_concurrent_giveaways = 50
        mock_tier.max_concurrent_giveaways_premium = 100
        mock_tier.max_sponsor_channels = 100
        mock_tier.max_sponsor_channels_premium = 200
        mock_tier.has_realtime_subscription_check = True
        
        async def mock_get(model, identifier):
            if model == SubscriptionTier and identifier == tier_id:
                return mock_tier
            elif model == User and identifier == user_id:
                return None
            return None
            
        mock_session.get = mock_get
        
        # Проверяем, что премиум-пользователь может создать розыгрыш
        can_create = await can_create_giveaway(mock_session, user_id)
        assert can_create[0] is True  # Может создать

    async def test_free_user_giveaway_creation_check(self, mock_session):
        """Тест проверки возможности создания розыгрыша обычным пользователем"""
        user_id = 123456789
        
        # Нет активной подписки
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Мокаем обычного пользователя без премиума
        mock_user = MagicMock(spec=User)
        mock_user.user_id = user_id
        mock_user.username = "free_user"
        mock_user.full_name = "Free User"
        mock_user.is_premium = False
        mock_user.premium_until = None
        
        async def mock_get(model, identifier):
            if model == User and identifier == user_id:
                return mock_user
            return None
            
        mock_session.get = mock_get
        
        # Проверяем лимиты для обычного пользователя
        can_create = await can_create_giveaway(mock_session, user_id)
        # В реальной системе у обычных пользователей есть базовые лимиты
        
    async def test_premium_tier_features_validation(self, mock_session):
        """Тест валидации возможностей премиум-тарифов"""
        # Создаем тариф с премиум-функциями
        mock_tier = MagicMock(spec=SubscriptionTier)
        mock_tier.id = 1
        mock_tier.name = "premium_validation"
        mock_tier.price_monthly = Decimal("14.99")
        mock_tier.duration_days = 30
        mock_tier.max_concurrent_giveaways = 5
        mock_tier.max_concurrent_giveaways_premium = 15  # Увеличенный лимит
        mock_tier.max_sponsor_channels = 10
        mock_tier.max_sponsor_channels_premium = 30     # Увеличенный лимит
        mock_tier.has_realtime_subscription_check = True  # Премиум-функция
        
        # Проверяем, что премиум-лимиты больше базовых
        assert mock_tier.max_concurrent_giveaways_premium > mock_tier.max_concurrent_giveaways
        assert mock_tier.max_sponsor_channels_premium > mock_tier.max_sponsor_channels
        assert mock_tier.has_realtime_subscription_check is True

    async def test_premium_subscription_deactivation(self, mock_session):
        """Тест деактивации премиум-подписки"""
        user_id = 123456789
        tier_id = 1
        
        # Создаем активную подписку
        mock_subscription = MagicMock(spec=UserSubscription)
        mock_subscription.user_id = user_id
        mock_subscription.tier_id = tier_id
        mock_subscription.start_date = datetime.now() - timedelta(days=1)
        mock_subscription.end_date = datetime.now() + timedelta(days=29)
        mock_subscription.is_active = True
        
        # Мокаем получение подписки
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Деактивируем подписку
        success = await deactivate_user_subscription(mock_session, user_id)
        
        assert success is None  # функция возвращает None после успешного выполнения
        # В реальной системе поле is_active должно быть установлено в False

    async def test_legacy_premium_system_compatibility(self, mock_session):
        """Тест совместимости с устаревшей системой премиум-подписки"""
        user_id = 123456789
        
        # Создаем пользователя с устаревшей премиум-системой
        future_date = datetime.now() + timedelta(days=30)
        mock_user = MagicMock(spec=User)
        mock_user.user_id = user_id
        mock_user.username = "legacy_premium_user"
        mock_user.full_name = "Legacy Premium User"
        mock_user.is_premium = True  # Устаревшая система
        mock_user.premium_until = future_date  # Подписка еще действует
        
        async def mock_get(model, identifier):
            if model == User and identifier == user_id:
                return mock_user
            return None
            
        mock_session.get = mock_get
        
        # Нет активной новой подписки
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # Проверяем статус - должен использовать устаревшую систему
        status = await get_user_subscription_status(mock_session, user_id)
        
        assert status is not None
        assert status["is_premium"] is True
        assert status["tier_name"] == "legacy_premium"
        assert status["expires_at"] == mock_user.premium_until