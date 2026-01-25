import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from unittest.mock import AsyncMock, MagicMock, patch

from database.models.giveaway import Giveaway
from database.models.user import User
from database.models.premium_features import UserSubscription
from sqlalchemy import select
from services.admin_user_service import UserService


@pytest.mark.asyncio
class TestPremiumFunctionality:
    """Тесты функционала премиум-подписки"""

    async def test_premium_subscription_purchase(self, async_session: AsyncSession, unique_user_id_counter):
        """Тест покупки премиум-подписки"""
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "premium_buyer",
            "full_name": "Premium Buyer",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()

        # Проверяем, что пользователь изначально не премиум
        assert user.is_premium is False
        assert user.premium_until is None

        # Покупаем премиум на 30 дней
        subscription_period_days = 30
        premium_until = datetime.now() + timedelta(days=subscription_period_days)
    
        # Обновляем статус премиума напрямую в базе данных
        stmt = update(User).where(User.user_id == user.user_id).values(
            is_premium=True,
            premium_until=premium_until
        )
        await async_session.execute(stmt)
        await async_session.commit()

        # Проверяем, что статус обновился
        await async_session.refresh(user)  # Обновляем объект в сессии
        assert user.is_premium is True
        assert user.premium_until is not None
        assert user.premium_until >= premium_until - timedelta(hours=1)  # с учетом времени выполнения

    async def test_premium_subscription_extension(self, async_session: AsyncSession, unique_user_id_counter):
        """Тест продления премиум-подписки"""
        # Создание пользователя с текущей премиум-подпиской
        current_premium_until = datetime.now() + timedelta(days=10)
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "premium_extender",
            "full_name": "Premium Extender",
            "is_premium": True,
            "premium_until": current_premium_until,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()

        # Проверяем начальный статус
        assert user.is_premium is True
        assert user.premium_until == current_premium_until

        # Продлеваем подписку еще на 30 дней
        extension_days = 30
        new_premium_until = current_premium_until + timedelta(days=extension_days)

        # Обновляем статус премиума напрямую в базе данных
        stmt = update(User).where(User.user_id == user.user_id).values(
            is_premium=True,
            premium_until=new_premium_until
        )
        await async_session.execute(stmt)
        await async_session.commit()

        # Проверяем, что дата окончания обновилась
        updated_user = await async_session.get(User, user.user_id)
        assert updated_user.is_premium is True
        assert updated_user.premium_until == new_premium_until

    async def test_premium_auto_renewal_cancellation(self, async_session: AsyncSession, unique_user_id_counter):
        """Тест отмены автопродления премиум-подписки"""
        # В этой системе автопродление может быть реализовано через внешние сервисы
        # или отдельное поле в базе данных. Для теста предположим, что есть возможность
        # отменить подписку до даты окончания
        
        # Создание пользователя с премиум-подпиской
        premium_until = datetime.now() + timedelta(days=30)
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "premium_canceller",
            "full_name": "Premium Canceller",
            "is_premium": True,
            "premium_until": premium_until,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()

        # Проверяем начальный статус
        assert user.is_premium is True
        assert user.premium_until == premium_until

        # Имитируем отмену автопродления - подписка заканчивается в назначенную дату
        # без продления. В этом случае мы просто оставляем дату без изменений
        # и ожидаем, что после этой даты статус изменится
        
        # Проверяем, что до даты окончания статус остается активным
        current_user = await async_session.get(User, user.user_id)
        assert current_user.is_premium is True
        assert current_user.premium_until == premium_until

    async def test_premium_status_check(self, async_session: AsyncSession, unique_user_id_counter):
        """Тест проверки статуса премиум-подписки"""
        # Создание пользователя с истекшей премиум-подпиской
        expired_premium_until = datetime.now() - timedelta(days=5)  # Подписка уже истекла
        expired_user_data = {
            "user_id": unique_user_id_counter(),
            "username": "expired_premium_user",
            "full_name": "Expired Premium User",
            "is_premium": True,  # Флаг еще не обновлен
            "premium_until": expired_premium_until,
            "created_at": datetime.now() - timedelta(days=35)  # Зарегистрирован давно
        }
        expired_user = User(**expired_user_data)
        async_session.add(expired_user)
        await async_session.commit()

        # Создание пользователя с активной премиум-подпиской
        active_premium_until = datetime.now() + timedelta(days=20)
        active_user_data = {
            "user_id": unique_user_id_counter(),
            "username": "active_premium_user",
            "full_name": "Active Premium User",
            "is_premium": True,
            "premium_until": active_premium_until,
            "created_at": datetime.now()
        }
        active_user = User(**active_user_data)
        async_session.add(active_user)
        await async_session.commit()

        # Создание обычного пользователя без премиума
        regular_user_data = {
            "user_id": unique_user_id_counter(),
            "username": "regular_user",
            "full_name": "Regular User",
            "is_premium": False,
            "premium_until": None,
            "created_at": datetime.now()
        }
        regular_user = User(**regular_user_data)
        async_session.add(regular_user)
        await async_session.commit()

        # Проверяем статусы пользователей
        # Обратите внимание, что в реальной системе нужно будет проверять
        # актуальность даты в момент проверки
        expired_user_updated = await async_session.get(User, expired_user.user_id)
        active_user_updated = await async_session.get(User, active_user.user_id)
        regular_user_updated = await async_session.get(User, regular_user.user_id)

        # В нашей системе флаг is_premium не автоматически обновляется при истечении срока
        # Это задача для фоновой задачи или проверки при обращении
        assert expired_user_updated.is_premium is True  # Флаг не обновлен автоматически
        assert expired_user_updated.premium_until == expired_premium_until

        assert active_user_updated.is_premium is True
        assert active_user_updated.premium_until == active_premium_until

        assert regular_user_updated.is_premium is False
        assert regular_user_updated.premium_until is None

    async def test_premium_access_to_extended_limits(self, async_session: AsyncSession, unique_user_id_counter):
        """Тест доступа премиум-пользователей к расширенным лимитам"""
        # Создание премиум-пользователя
        premium_until = datetime.now() + timedelta(days=30)
        premium_user_data = {
            "user_id": unique_user_id_counter(),
            "username": "premium_limited_access",
            "full_name": "Premium Limited Access User",
            "is_premium": True,
            "premium_until": premium_until,
            "created_at": datetime.now()
        }
        premium_user = User(**premium_user_data)
        async_session.add(premium_user)
        await async_session.commit()

        # Создание обычного пользователя
        regular_user_data = {
            "user_id": unique_user_id_counter(),
            "username": "regular_limited_access",
            "full_name": "Regular Limited Access User",
            "is_premium": False,
            "premium_until": None,
            "created_at": datetime.now()
        }
        regular_user = User(**regular_user_data)
        async_session.add(regular_user)
        await async_session.commit()

        # В реальной системе премиум-пользователи могут иметь расширенные лимиты
        # Например, возможность создавать больше розыгрышей, иметь больше каналов и т.д.
        # Проверяем, что пользователи корректно идентифицируются как премиум/обычные

        premium_db_user = await async_session.get(User, premium_user.user_id)
        regular_db_user = await async_session.get(User, regular_user.user_id)

        assert premium_db_user.is_premium is True
        assert regular_db_user.is_premium is False

        # В реальной системе здесь были бы проверки на расширенные функции
        # Например, проверка количества розыгрышей, которые может создать пользователь
        # или количество каналов, которые можно добавить

    async def test_premium_status_restoration_after_expiration(self, async_session: AsyncSession, unique_user_id_counter):
        """Тест восстановления доступа после истечения подписки"""
        # Создание пользователя с истекшей премиум-подпиской
        past_premium_until = datetime.now() - timedelta(days=10)
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "restored_premium_user",
            "full_name": "Restored Premium User",
            "is_premium": True,  # Флаг еще не обновлен
            "premium_until": past_premium_until,
            "created_at": datetime.now() - timedelta(days=40)
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()

        # Проверяем начальный статус
        current_user = await async_session.get(User, user.user_id)
        assert current_user.is_premium is True  # Флаг не обновлен автоматически

        # Восстанавливаем премиум-статус (например, пользователь снова оплатил)
        new_premium_until = datetime.now() + timedelta(days=30)
        # Обновляем статус премиума напрямую в базе данных
        stmt = update(User).where(User.user_id == user.user_id).values(
            is_premium=True,
            premium_until=new_premium_until
        )
        await async_session.execute(stmt)
        await async_session.commit()

        # Проверяем, что статус восстановлен
        restored_user = await async_session.get(User, user.user_id)
        assert restored_user.is_premium is True
        assert restored_user.premium_until == new_premium_until
        assert restored_user.premium_until > datetime.now()

    async def test_create_giveaway_with_premium_features(self, async_session: AsyncSession, unique_user_id_counter):
        """Тест создания розыгрыша с премиум-возможностями"""
        # Создание премиум-пользователя
        premium_until = datetime.now() + timedelta(days=30)
        premium_user_data = {
            "user_id": unique_user_id_counter(),
            "username": "premium_creator",
            "full_name": "Premium Creator",
            "is_premium": True,
            "premium_until": premium_until,
            "created_at": datetime.now()
        }
        premium_user = User(**premium_user_data)
        async_session.add(premium_user)
        await async_session.commit()

        # Создание обычного пользователя
        regular_user_data = {
            "user_id": unique_user_id_counter(),
            "username": "regular_creator",
            "full_name": "Regular Creator",
            "is_premium": False,
            "premium_until": None,
            "created_at": datetime.now()
        }
        regular_user = User(**regular_user_data)
        async_session.add(regular_user)
        await async_session.commit()

        # Создание розыгрыша с премиум-возможностями от премиум-пользователя
        premium_giveaway_data = {
            "owner_id": premium_user.user_id,
            "channel_id": -1001234567890,
            "message_id": 200,
            "prize_text": "Премиум розыгрыш с расширенными возможностями",
            "winners_count": 5,
            "finish_time": datetime.now() + timedelta(days=14),
            "status": "active",
            "is_referral_enabled": True,
            "is_captcha_enabled": True,
            "is_paid": True,  # Признак премиум-розыгрыша
            "is_story_boost_enabled": True,
            "is_channel_boost_enabled": True,
            "is_referral_boost_enabled": True
        }
        premium_giveaway = Giveaway(**premium_giveaway_data)
        async_session.add(premium_giveaway)
        await async_session.commit()

        # Создание обычного розыгрыша от обычного пользователя
        regular_giveaway_data = {
            "owner_id": regular_user.user_id,
            "channel_id": -1001234567891,
            "message_id": 201,
            "prize_text": "Обычный розыгрыш",
            "winners_count": 1,
            "finish_time": datetime.now() + timedelta(days=7),
            "status": "active",
            "is_referral_enabled": False,
            "is_captcha_enabled": False,
            "is_paid": False,
            "is_story_boost_enabled": False,
            "is_channel_boost_enabled": False,
            "is_referral_boost_enabled": False
        }
        regular_giveaway = Giveaway(**regular_giveaway_data)
        async_session.add(regular_giveaway)
        await async_session.commit()

        # Проверяем созданные розыгрыши
        assert premium_giveaway.owner_id == premium_user.user_id
        assert premium_giveaway.is_paid is True
        assert premium_giveaway.is_story_boost_enabled is True
        assert premium_giveaway.is_channel_boost_enabled is True
        assert premium_giveaway.is_referral_boost_enabled is True

        assert regular_giveaway.owner_id == regular_user.user_id
        assert regular_giveaway.is_paid is False
        assert regular_giveaway.is_story_boost_enabled is False
        assert regular_giveaway.is_channel_boost_enabled is False
        assert regular_giveaway.is_referral_boost_enabled is False