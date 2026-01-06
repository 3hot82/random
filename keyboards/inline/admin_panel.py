# keyboards/inline/admin_panel.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models.giveaway import Giveaway
from keyboards.callback_data import AdminAction
from core.security.hmac_signer import sign_data

def build_giveaway_list(giveaways: list[Giveaway], admin_id: int):
    """Строит список активных розыгрышей. Кнопки подписаны для конкретного админа."""
    builder = InlineKeyboardBuilder()
    
    for gw in giveaways:
        # Генерируем подписи для действий
        sig_manage = sign_data("manage", gw.id, admin_id)
        
        btn_text = f"🎁 #{gw.id} | {gw.winners_count} winners"
        callback = AdminAction(action="manage", id=gw.id, sig=sig_manage)
        
        builder.button(text=btn_text, callback_data=callback)
    
    builder.adjust(1) # В один столбик
    return builder.as_markup()

def build_manage_menu(gw_id: int, admin_id: int):
    """Меню управления конкретным розыгрышем"""
    builder = InlineKeyboardBuilder()
    
    # Генерация подписей
    sig_del = sign_data("delete", gw_id, admin_id)
    sig_rig = sign_data("rig", gw_id, admin_id) # Кнопка подкрутки
    sig_finish = sign_data("finish", gw_id, admin_id)

    builder.button(text="🛑 Завершить", callback_data=AdminAction(action="finish", id=gw_id, sig=sig_finish))
    builder.button(text="🗑 Удалить", callback_data=AdminAction(action="delete", id=gw_id, sig=sig_del))
    builder.button(text="🎯 Назначить победителя", callback_data=AdminAction(action="rig", id=gw_id, sig=sig_rig))
    
    builder.adjust(1)
    return builder.as_markup()