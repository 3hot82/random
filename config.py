from typing import List
from pydantic_settings import BaseSettings
from pydantic import SecretStr, field_validator

class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    # Используем валидатор, чтобы превращать строку "123,456" в список [123, 456]
    ADMIN_IDS: List[int]
    DB_DNS: str
    REDIS_URL: str
    SECRET_KEY: str

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        # Если пришла строка (например "123,456"), сплитим её
        if isinstance(v, str):
            # Удаляем квадратные скобки если пользователь их все-таки написал
            v = v.replace("[", "").replace("]", "")
            if not v:
                return []
            return [int(x.strip()) for x in v.split(",")]
        # Если пришло число (один админ без кавычек и запятых)
        if isinstance(v, int):
            return [v]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

config = Settings()