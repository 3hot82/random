# План миграции данных для премиум-функций

## 1. Обзор

В этом документе описывается план миграции существующих данных для поддержки новых премиум-функций бота розыгрышей, включая:
- Детализированные отчеты о конверсии участников
- История всех розыгрышей с метриками
- Аналитика по каналам-спонсорам
- Систему тарифов и ограничений

## 2. Существующие данные

### 2.1. Текущие таблицы

- `users` - информация о пользователях (user_id, username, full_name, is_premium, premium_until)
- `giveaways` - информация о розыгрышах (id, owner_id, channel_id, message_id, prize_text, winners_count, finish_time, status)
- `participants` - участники розыгрышей (user_id, giveaway_id, created_at, tickets_count, referrer_id, ticket_code)
- `channels` - каналы пользователей (id, user_id, channel_id, title, username, type, invite_link)
- `giveaway_required_channels` - каналы-спонсоры розыгрышей (id, giveaway_id, channel_id, channel_title, channel_link)

### 2.2. Проблемы с текущими данными

- Отсутствие исторических данных о воронке конверсии
- Нет аналитики по эффективности каналов-спонсоров
- Старая система премиум-статуса не поддерживает тарифы
- Нет данных об удержании подписчиков

## 3. План миграции

### 3.1. Этап 1: Создание новых таблиц

```sql
-- Создание таблиц для новых моделей
CREATE TABLE conversion_funnels (
    id SERIAL PRIMARY KEY,
    giveaway_id INTEGER REFERENCES giveaways(id) ON DELETE CASCADE,
    post_views INTEGER DEFAULT 0,
    unique_clicks INTEGER DEFAULT 0,
    started_join INTEGER DEFAULT 0,
    checked_first_channel INTEGER DEFAULT 0,
    subscribed_all_required INTEGER DEFAULT 0,
    dropped_at_channel_n JSONB DEFAULT '{}',
    completed_captcha INTEGER DEFAULT 0,
    invited_referrals INTEGER DEFAULT 0,
    fully_participated INTEGER DEFAULT 0,
    avg_time_to_complete INTERVAL DEFAULT '0 seconds',
    bounce_rate NUMERIC(5,4) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE giveaway_histories (
    id SERIAL PRIMARY KEY,
    giveaway_id INTEGER UNIQUE REFERENCES giveaways(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'completed',
    total_participants INTEGER DEFAULT 0,
    unique_participants INTEGER DEFAULT 0,
    new_subscribers INTEGER DEFAULT 0,
    total_tickets INTEGER DEFAULT 0,
    sponsors_channels INTEGER[],
    new_subs_per_channel JSONB DEFAULT '{}',
    avg_tickets_per_user NUMERIC(10,2) DEFAULT 0.0,
    referral_conversion NUMERIC(5,4) DEFAULT 0.0,
    boost_participants INTEGER DEFAULT 0,
    still_subscribed_after_7d INTEGER DEFAULT 0,
    still_subscribed_after_30d INTEGER DEFAULT 0,
    prize_cost NUMERIC(12,2) DEFAULT 0.00,
    cost_per_participant NUMERIC(12,2) DEFAULT 0.00,
    roi_subscribers NUMERIC(12,2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE channel_analytics (
    id SERIAL PRIMARY KEY,
    channel_id BIGINT,
    channel_title VARCHAR(255),
    times_used_as_sponsor INTEGER DEFAULT 0,
    total_giveaways INTEGER[],
    new_subscribers_brought INTEGER DEFAULT 0,
    avg_conversion NUMERIC(5,4) DEFAULT 0.0,
    immediate_unsub_rate NUMERIC(5,4) DEFAULT 0.0,
    retention_7d NUMERIC(5,4) DEFAULT 0.0,
    retention_30d NUMERIC(5,4) DEFAULT 0.0,
    engagement_score NUMERIC(5,4) DEFAULT 0.0,
    failed_checks INTEGER DEFAULT 0,
    avg_check_time INTERVAL DEFAULT '0 seconds',
    rank_by_conversion INTEGER DEFAULT 0,
    rank_by_retention INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE subscription_tiers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE,
    display_name VARCHAR(100),
    max_concurrent_giveaways INTEGER DEFAULT 1,
    max_sponsor_channels INTEGER DEFAULT 2,
    max_participants_export INTEGER DEFAULT 1000,
    has_advanced_analytics BOOLEAN DEFAULT FALSE,
    has_custom_branding BOOLEAN DEFAULT FALSE,
    has_priority_support BOOLEAN DEFAULT FALSE,
    max_concurrent_giveaways_premium INTEGER DEFAULT 10,
    max_sponsor_channels_premium INTEGER DEFAULT 20,
    max_participants_export_premium INTEGER DEFAULT 10000,
    has_realtime_subscription_check BOOLEAN DEFAULT FALSE,
    price_monthly NUMERIC(10,2) DEFAULT 0.00,
    price_yearly NUMERIC(10,2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    tier_id INTEGER REFERENCES subscription_tiers(id),
    start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_date TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    auto_renew BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE premium_feature_usage (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    feature_name VARCHAR(100),
    usage_count INTEGER DEFAULT 0,
    usage_limit INTEGER,
    reset_period VARCHAR(20),
    last_reset TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3.2. Этап 2: Заполнение справочника тарифов

```sql
-- Вставка стандартных тарифов
INSERT INTO subscription_tiers (
    name, display_name, 
    max_concurrent_giveaways, max_sponsor_channels, max_participants_export,
    has_advanced_analytics, has_custom_branding, has_priority_support,
    max_concurrent_giveaways_premium, max_sponsor_channels_premium, max_participants_export_premium,
    has_realtime_subscription_check, price_monthly, price_yearly, sort_order
) VALUES
('free', 'Бесплатный', 1, 2, 1000, false, false, false, 1, 2, 1000, false, 0.00, 0.00, 0),
('premium', 'Премиум', 1, 2, 1000, false, false, false, 10, 20, 10000, true, 299.00, 2990.00, 1),
('enterprise', 'Корпоративный', 1, 2, 1000, false, false, false, 9999, 9999, 999999, true, 999.00, 9990.00, 2);
```

### 3.3. Этап 3: Миграция существующих премиум-пользователей

```python
async def migrate_premium_users(session: AsyncSession):
    """
    Миграция существующих премиум-пользователей на новую систему тарифов
    """
    # Получаем всех пользователей с is_premium=True
    stmt = select(User).where(User.is_premium == True)
    premium_users = await session.execute(stmt)
    premium_users = premium_users.scalars().all()
    
    # Находим тариф "premium"
    premium_tier_stmt = select(SubscriptionTier).where(SubscriptionTier.name == "premium")
    premium_tier = await session.execute(premium_tier_stmt)
    premium_tier = premium_tier.scalar_one()
    
    migrated_count = 0
    
    for user in premium_users:
        # Проверяем, не существует ли уже подписка для этого пользователя
        existing_sub = await session.execute(
            select(UserSubscription).where(
                UserSubscription.user_id == user.user_id,
                UserSubscription.is_active == True
            )
        )
        existing_sub = existing_sub.scalar_one_or_none()
        
        if not existing_sub:
            # Создаем новую подписку для пользователя
            user_subscription = UserSubscription(
                user_id=user.user_id,
                tier_id=premium_tier.id,
                start_date=datetime.utcnow(),
                end_date=user.premium_until,
                is_active=True if user.premium_until is None or user.premium_until > datetime.utcnow() else False,
                auto_renew=False  # Не переносим автопродление, т.к. старая система не поддерживала
            )
            session.add(user_subscription)
            migrated_count += 1
    
    await session.commit()
    print(f"Мигрировано {migrated_count} премиум-пользователей")
```

### 3.4. Этап 4: Генерация исторических данных о розыгрышах

```python
async def generate_giveaway_history(session: AsyncSession):
    """
    Генерация исторических данных для существующих розыгрышей
    """
    # Получаем все завершенные розыгрыши
    stmt = select(Giveaway).where(
        or_(Giveaway.status == "finished", Giveaway.status.like("%cancel%"))
    )
    giveaways = await session.execute(stmt)
    giveaways = giveaways.scalars().all()
    
    processed_count = 0
    
    for giveaway in giveaways:
        # Получаем количество участников
        participants_count = await session.execute(
            select(func.count(Participant.user_id)).where(Participant.giveaway_id == giveaway.id)
        )
        participants_count = participants_count.scalar()
        
        # Получаем каналы-спонсоры
        sponsors = await session.execute(
            select(GiveawayRequiredChannel.channel_id).where(
                GiveawayRequiredChannel.giveaway_id == giveaway.id
            )
        )
        sponsors = [row[0] for row in sponsors.fetchall()]
        
        # Создаем запись в истории
        history = GiveawayHistory(
            giveaway_id=giveaway.id,
            finished_at=giveaway.finish_time,
            status=giveaway.status,
            total_participants=participants_count,
            unique_participants=participants_count,  # Пока не можем точно определить
            total_tickets=participants_count,  # Предполагаем по умолчанию 1 билет на участника
            sponsors_channels=sponsors,
            avg_tickets_per_user=1.0,
            created_at=giveaway.finish_time
        )
        session.add(history)
        processed_count += 1
    
    await session.commit()
    print(f"Сгенерировано {processed_count} записей истории розыгрышей")
```

### 3.5. Этап 5: Генерация аналитики по каналам-спонсорам

```python
async def generate_channel_analytics(session: AsyncSession):
    """
    Генерация аналитики для существующих каналов-спонсоров
    """
    # Получаем все каналы-спонсоры из завершенных розыгрышей
    stmt = select(
        GiveawayRequiredChannel.channel_id,
        GiveawayRequiredChannel.channel_title,
        func.count(GiveawayRequiredChannel.giveaway_id).label('times_used')
    ).join(Giveaway).where(
        or_(Giveaway.status == "finished", Giveaway.status.like("%cancel%"))
    ).group_by(GiveawayRequiredChannel.channel_id, GiveawayRequiredChannel.channel_title)
    
    results = await session.execute(stmt)
    channel_stats = results.fetchall()
    
    processed_count = 0
    
    for stat in channel_stats:
        # Получаем количество новых подписчиков для этого канала
        # Это сложный запрос, который зависит от логики отслеживания подписок
        new_subscribers = await calculate_new_subscribers_for_channel(session, stat.channel_id, stat.times_used)
        
        analytics = ChannelAnalytics(
            channel_id=stat.channel_id,
            channel_title=stat.channel_title,
            times_used_as_sponsor=stat.times_used,
            new_subscribers_brought=new_subscribers,
            total_giveaways=[]  # Пока пустой, можно заполнить позже
        )
        session.add(analytics)
        processed_count += 1
    
    await session.commit()
    print(f"Сгенерировано {processed_count} записей аналитики каналов")
```

### 3.6. Этап 6: Создание индексов для производительности

```sql
-- Индексы для новых таблиц
CREATE INDEX idx_conversion_funnels_giveaway_id ON conversion_funnels(giveaway_id);
CREATE INDEX idx_giveaway_histories_giveaway_id ON giveaway_histories(giveaway_id);
CREATE INDEX idx_channel_analytics_channel_id ON channel_analytics(channel_id);
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_tier_id ON user_subscriptions(tier_id);
CREATE INDEX idx_premium_feature_usage_user_id ON premium_feature_usage(user_id);
CREATE INDEX idx_premium_feature_usage_feature_name ON premium_feature_usage(feature_name);

-- Составные индексы для оптимизации частых запросов
CREATE INDEX idx_user_subscriptions_active ON user_subscriptions(user_id, is_active) WHERE is_active = true;
CREATE INDEX idx_giveaway_histories_status ON giveaway_histories(status);
```

## 4. Потенциальные проблемы и решения

### 4.1. Проблема: Недостаток исторических данных о конверсии

**Решение**: 
- Для старых розыгрышей установить минимальные значения метрик
- Использовать статистические данные для оценки отсутствующих значений
- Документировать ограничения в аналитических отчетах

### 4.2. Проблема: Сложность отслеживания удержания подписчиков

**Решение**:
- Использовать дату окончания розыгрыша как точку отсчета
- Проверять статус подписки пользователей через 7 и 30 дней после окончания розыгрыша
- Для старых розыгрышей использовать доступные данные, если возможно

### 4.3. Проблема: Конфликты при миграции данных

**Решение**:
- Выполнить миграцию в режиме обслуживания
- Создать резервную копию базы данных перед миграцией
- Использовать транзакции для обеспечения целостности данных

## 5. План выполнения

1. **Подготовительный этап (1 день)**:
   - Создание резервной копии базы данных
   - Подготовка скриптов миграции
   - Тестирование на тестовой базе данных

2. **Этап 1: Создание новых таблиц (1 час)**:
   - Выполнение SQL-скриптов для создания таблиц
   - Создание индексов

3. **Этап 2: Миграция тарифов и пользователей (4 часа)**:
   - Заполнение справочника тарифов
   - Миграция существующих премиум-пользователей

4. **Этап 3: Генерация исторических данных (8 часов)**:
   - Генерация истории розыгрышей
   - Генерация аналитики по каналам
   - Заполнение воронки конверсии (где возможно)

5. **Финальный этап (2 часа)**:
   - Проверка целостности данных
   - Тестирование функциональности
   - Возврат в нормальный режим работы

## 6. Пост-миграционные действия

- Обновление документации
- Обучение команды работе с новыми функциями
- Мониторинг производительности после миграции
- Корректировка аналитических отчетов для работы с новыми данными