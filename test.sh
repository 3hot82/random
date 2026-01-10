#!/bin/bash
# Установка тестовых переменных окружения
export BOT_TOKEN="test_token"
export ADMIN_IDS="[123]"
export DB_DNS="postgresql+asyncpg://user:password@localhost/test_db"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="test_secret_key"

source ~/Desktop/ytb/venv/bin/activate
cd ~/Desktop/ytb/random
python -m pytest tests/test_admin_panel.py -v