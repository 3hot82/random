# core/logic/randomizer.py
import secrets
from database.models.giveaway import Giveaway

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