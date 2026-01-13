# core/logic/randomizer.py
import secrets
from database.models.giveaway import Giveaway
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

def select_winners(giveaway: Giveaway, participant_ids: list[int]) -> list[int]:
    """
    Выбирает победителей.
    1. Если есть predetermined_winner_id - он побеждает первым.
    2. Остальные выбираются честным рандомом (SystemRandom).
    """
    winners = []
    pool = set(participant_ids) # Используем set для уникальности и O(1) удаления

    # 1. Обработка подкрутки (Rigging)
    if giveaway.predetermined_winner_id:
        if giveaway.predetermined_winner_id in pool:
            winners.append(giveaway.predetermined_winner_id)
            pool.remove(giveaway.predetermined_winner_id)
        # Если "блатного" нет в участниках, подкрутка не сработает (защита от дурака)

    # 2. Сколько еще нужно победителей?
    needed = giveaway.winners_count - len(winners)

    if needed > 0:
        pool_list = list(pool)
        if len(pool_list) <= needed:
            # Участников меньше, чем призов -> все побеждают
            winners.extend(pool_list)
        else:
            # Криптографически стойкий выбор
            random_winners = secrets.SystemRandom().sample(pool_list, k=needed)
            winners.extend(random_winners)

    return winners

async def select_winners_sql(session: AsyncSession, giveaway_id: int, winners_count: int, predetermined_winner_id: int = None) -> list[int]:
    """
    Выбирает победителей через SQL запрос, более эффективно для больших объемов
    """
    from database.models.participant import Participant
    
    # Начинаем с подготовки SQL-запроса
    query = select(Participant.user_id).where(
        Participant.giveaway_id == giveaway_id
    )
    
    # Получаем всех участников
    result = await session.execute(query)
    all_participants = result.scalars().all()
    
    # Обрабатываем подкрутку (если есть предопределенный победитель)
    winners = []
    if predetermined_winner_id and predetermined_winner_id in all_participants:
        winners.append(predetermined_winner_id)
        all_participants = [pid for pid in all_participants if pid != predetermined_winner_id]
    
    # Сколько еще нужно победителей?
    remaining_winners_needed = winners_count - len(winners)
    
    if remaining_winners_needed <= 0:
        # Все места уже заняты предопределенным победителем
        return winners
    elif remaining_winners_needed >= len(all_participants):
        # Участников меньше, чем оставшихся мест - все становятся победителями
        winners.extend(all_participants)
        return winners
    else:
        # Выбираем оставшихся победителей случайным образом через SQL
        # Используем ORDER BY RANDOM() для честного выбора
        subquery = select(Participant.user_id).where(
            Participant.giveaway_id == giveaway_id
        ).where(
            Participant.user_id.notin_(winners)  # Исключаем предопределенных победителей
        ).order_by(text('RANDOM()')).limit(remaining_winners_needed)
        
        result = await session.execute(subquery)
        additional_winners = result.scalars().all()
        winners.extend(additional_winners)
        
        return winners