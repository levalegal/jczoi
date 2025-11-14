import sqlite3
import os
from datetime import datetime
from typing import Optional
from app.config import Config

class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DB_PATH
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                full_name TEXT,
                email TEXT,
                phone TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                area REAL,
                residents INTEGER,
                building_number TEXT,
                apartment_number TEXT,
                building_x INTEGER,
                building_y INTEGER,
                building_width INTEGER,
                building_height INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Meters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id INTEGER REFERENCES Objects(id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                serial_number TEXT,
                installation_date DATE,
                verification_date DATE,
                next_verification_date DATE,
                tariff REAL NOT NULL,
                unit TEXT DEFAULT 'м³',
                location TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meter_id INTEGER REFERENCES Meters(id) ON DELETE CASCADE,
                value REAL NOT NULL,
                reading_date DATE NOT NULL,
                previous_reading_id INTEGER REFERENCES Readings(id),
                photo_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(meter_id, reading_date)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reading_id INTEGER REFERENCES Readings(id) ON DELETE CASCADE,
                consumption REAL NOT NULL,
                amount REAL NOT NULL,
                tariff REAL NOT NULL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES Users(id),
                object_id INTEGER REFERENCES Objects(id),
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS UserObjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES Users(id) ON DELETE CASCADE,
                object_id INTEGER REFERENCES Objects(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, object_id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_meters_object_id ON Meters(object_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_objects_user_id ON UserObjects(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_objects_object_id ON UserObjects(object_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_meter_id ON Readings(meter_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_date ON Readings(reading_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_calculations_reading_id ON Calculations(reading_id)
        """)
        
        admin_exists = cursor.execute(
            "SELECT COUNT(*) FROM Users WHERE username = 'admin'"
        ).fetchone()[0]
        
        if admin_exists == 0:
            from app.services.auth_service import AuthService
            hashed_password = AuthService.hash_password(Config.DEFAULT_ADMIN_PASSWORD)
            cursor.execute("""
                INSERT INTO Users (username, password, role, full_name)
                VALUES (?, ?, 'admin', 'Администратор')
            """, (Config.DEFAULT_ADMIN_USERNAME, hashed_password))
        else:
            from app.services.auth_service import AuthService
            cursor.execute("SELECT password FROM Users WHERE username = ?", (Config.DEFAULT_ADMIN_USERNAME,))
            admin_password = cursor.fetchone()
            if admin_password and not admin_password[0].startswith('$2b$'):
                hashed_password = AuthService.hash_password(Config.DEFAULT_ADMIN_PASSWORD)
                cursor.execute("UPDATE Users SET password = ? WHERE username = ?", 
                             (hashed_password, Config.DEFAULT_ADMIN_USERNAME))
        
        conn.commit()
        conn.close()
        
        from app.services.auth_service import AuthService
        AuthService.migrate_passwords(self)
    
    def backup_database(self, backup_path: Optional[str] = None):
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_{timestamp}.db"
        
        source = self.get_connection()
        backup = sqlite3.connect(backup_path)
        source.backup(backup)
        source.close()
        backup.close()
        
        return backup_path

