import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional
from app.database import Database
from app.config import Config

class BackupService:
    def __init__(self, db: Database):
        self.db = db
        self.backup_thread = None
        self.running = False
        self.backup_interval_hours = 24
    
    def start_auto_backup(self, interval_hours: int = 24):
        self.backup_interval_hours = interval_hours
        self.running = True
        self.backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
        self.backup_thread.start()
    
    def stop_auto_backup(self):
        self.running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=5)
    
    def _backup_loop(self):
        while self.running:
            try:
                self.create_backup()
                time.sleep(self.backup_interval_hours * 3600)
            except Exception as e:
                print(f"Ошибка при создании резервной копии: {e}")
                time.sleep(3600)
    
    def create_backup(self, backup_path: Optional[str] = None) -> str:
        if backup_path is None:
            backup_dir = Config.get_backup_dir()
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
        
        return self.db.backup_database(backup_path)
    
    def cleanup_old_backups(self, days_to_keep: int = 30):
        backup_dir = Config.get_backup_dir()
        if not os.path.exists(backup_dir):
            return
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for filename in os.listdir(backup_dir):
            if filename.startswith("backup_") and filename.endswith(".db"):
                filepath = os.path.join(backup_dir, filename)
                try:
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_time < cutoff_date:
                        os.remove(filepath)
                except Exception as e:
                    print(f"Ошибка при удалении старой резервной копии {filename}: {e}")

