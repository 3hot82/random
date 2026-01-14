from datetime import datetime
from core.tools.timezone import to_msk

def format_giveaway_caption(prize_text: str, winners_count: int, finish_time: datetime, participants_count: int, is_hidden: bool = False) -> str:
    # Переводим время в МСК для отображения
    finish_msk = to_msk(finish_time)
    
    # Считаем остаток времени
    now_msk = to_msk(datetime.utcnow())
    delta = finish_msk - now_msk
    
    if delta.total_seconds() < 0:
        time_left = "Завершен"
    elif delta.days > 0:
        time_left = f"{delta.days} дн."
    elif delta.seconds > 3600:
        time_left = f"{delta.seconds // 3600} ч."
    else:
        time_left = "Скоро"

    date_str = finish_msk.strftime("%d.%m.%Y %H:%M MSK")

    # ЛОГИКА СКРЫТИЯ
    if is_hidden:
        part_text = "🔥 Много" # Или "Скрыто", или просто не выводить строку
    else:
        part_text = str(participants_count)

    return (
        f"{prize_text}\n\n"
        f"➖➖➖➖➖\n"
        f"👥 <b>Участников:</b> {part_text}\n"
        f"🏆 <b>Призовых мест:</b> {winners_count}\n"
        f"⏳ <b>Итоги:</b> {date_str} ({time_left})"
    )