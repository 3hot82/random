import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging():
    """
    Настройка системы логирования для админ-панели
    """
    # Создаем директорию для логов, если она не существует
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Настройка формата логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler(
        'logs/admin_panel.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Настройка логгеров для конкретных модулей
    admin_logger = logging.getLogger('admin')
    admin_logger.setLevel(logging.INFO)
    
    broadcast_logger = logging.getLogger('broadcast')
    broadcast_logger.setLevel(logging.INFO)
    
    return root_logger