import os
from pathlib import Path

class Config:
    DB_NAME = "meter_reader.db"
    DB_PATH = os.path.join(os.getcwd(), DB_NAME)
    MAP_IMAGE_PATH = "city_map.png"
    BACKUP_DIR = "backups"
    
    DEFAULT_ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = "admin"
    
    VERIFICATION_NOTIFICATION_DAYS = 30
    READING_REMINDER_DAYS = 3
    
    APP_NAME = "Система учета показаний счетчиков ЖКХ"
    APP_VERSION = "1.0.0"
    
    SETTINGS_FILE = "settings.json"
    
    @classmethod
    def ensure_backup_dir(cls):
        backup_path = Path(cls.BACKUP_DIR)
        backup_path.mkdir(exist_ok=True)
        return str(backup_path)
    
    @staticmethod
    def get_backup_dir() -> str:
        backup_path = Path(__file__).parent.parent.parent / "backups"
        backup_path.mkdir(exist_ok=True)
        return str(backup_path)

