import bleach
from aiogram.types import Message

# Разрешенные теги (Telegram API поддерживает этот список)
ALLOWED_TAGS = ['b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del', 'a', 'code', 'pre', 'blockquote', 'tg-spoiler']
ALLOWED_ATTRS = {'a': ['href']}

def sanitize_text(text: str) -> str:
    """Очищает HTML от мусора, оставляя безопасные теги Telegram"""
    if not text:
        return ""
    return bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

def get_message_html(message: Message) -> str:
    """
    Превращает сообщение с entities (форматированием Telegram) в HTML-строку.
    Корректно обрабатывает ссылки, жирный текст и т.д.
    """
    text = message.text or message.caption
    if not text:
        return ""

    entities = message.entities or message.caption_entities
    if not entities:
        return text

    # Telegram использует UTF-16 offsets
    utf16_text = text.encode("utf-16-le")
    html_text = ""
    last_offset = 0

    # Сортируем entities по offset
    entities = sorted(entities, key=lambda e: e.offset)

    for entity in entities:
        if entity.offset < last_offset:
            continue
            
        start = entity.offset * 2
        end = (entity.offset + entity.length) * 2
        
        # Текст до энтити
        chunk = utf16_text[last_offset*2 : start].decode("utf-16-le")
        html_text += _escape(chunk)
        
        # Текст внутри энтити
        inner_raw = utf16_text[start:end].decode("utf-16-le")
        inner = _escape(inner_raw)
        
        if entity.type == "bold":
            html_text += f"<b>{inner}</b>"
        elif entity.type == "italic":
            html_text += f"<i>{inner}</i>"
        elif entity.type == "underline":
            html_text += f"<u>{inner}</u>"
        elif entity.type == "strikethrough":
            html_text += f"<s>{inner}</s>"
        elif entity.type == "code":
            html_text += f"<code>{inner}</code>"
        elif entity.type == "pre":
            html_text += f"<pre>{inner}</pre>"
        elif entity.type == "text_link":
            html_text += f'<a href="{entity.url}">{inner}</a>'
        elif entity.type == "text_mention":
            html_text += f'<a href="tg://user?id={entity.user.id}">{inner}</a>'
        elif entity.type == "spoiler":
            html_text += f'<tg-spoiler>{inner}</tg-spoiler>'
        elif entity.type == "blockquote":
            html_text += f'<blockquote>{inner}</blockquote>'
        else:
            html_text += inner
            
        last_offset = entity.offset + entity.length

    # Оставшийся хвост
    tail = utf16_text[last_offset*2:].decode("utf-16-le")
    html_text += _escape(tail)
    
    return html_text

def _escape(text: str) -> str:
    """Экранирование спецсимволов HTML"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")