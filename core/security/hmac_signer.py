# core/security/hmac_signer.py
import hashlib
import hmac
from config import config

def _generate_hash(data_string: str) -> str:
    """Внутренняя функция хеширования"""
    return hmac.new(
        config.SECRET_KEY.encode(),
        data_string.encode(),
        hashlib.sha256
    ).hexdigest()[:12]  # Берем первые 12 символов для экономии места

def sign_data(action: str, entity_id: int, admin_id: int) -> str:
    """Создает подпись: action + id + admin_id"""
    data = f"{action}:{entity_id}:{admin_id}"
    return _generate_hash(data)

def verify_signature(action: str, entity_id: int, admin_id: int, received_sig: str) -> bool:
    """Проверяет подпись. Защищает от подмены ID и User ID"""
    expected_sig = sign_data(action, entity_id, admin_id)
    return hmac.compare_digest(expected_sig, received_sig)