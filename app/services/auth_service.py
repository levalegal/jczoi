import bcrypt
from typing import Optional
from app.database import Database

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    @staticmethod
    def migrate_passwords(db: Database):
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, password FROM Users")
        users = cursor.fetchall()
        
        for user_id, password in users:
            if not password.startswith('$2b$'):
                hashed = AuthService.hash_password(password)
                cursor.execute("UPDATE Users SET password = ? WHERE id = ?", (hashed, user_id))
        
        conn.commit()
        conn.close()

