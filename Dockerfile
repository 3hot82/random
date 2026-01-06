# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей (если нужны для сборки pg driver)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем пользователя без прав root
RUN useradd -m appuser
USER appuser

CMD ["python", "main.py"]