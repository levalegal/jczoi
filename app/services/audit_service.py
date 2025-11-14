from datetime import datetime
from typing import Optional, List, Dict
from app.database import Database

class AuditService:
    def __init__(self, db: Database):
        self.db = db
        self.init_audit_table()
    
    def init_audit_table(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AuditLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                description TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_user_id ON AuditLog(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_entity ON AuditLog(entity_type, entity_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_created_at ON AuditLog(created_at)
        """)
        
        conn.commit()
        conn.close()
    
    def log_action(self, user_id: Optional[int], username: Optional[str],
                   action_type: str, entity_type: str, entity_id: Optional[int] = None,
                   old_value: Optional[str] = None, new_value: Optional[str] = None,
                   description: Optional[str] = None, ip_address: Optional[str] = None):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO AuditLog (user_id, username, action_type, entity_type, 
                                entity_id, old_value, new_value, description, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, action_type, entity_type, entity_id,
              old_value, new_value, description, ip_address))
        
        conn.commit()
        conn.close()
    
    def get_logs(self, user_id: Optional[int] = None, entity_type: Optional[str] = None,
                 start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                 limit: int = 100) -> List[Dict]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM AuditLog WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        columns = ['id', 'user_id', 'username', 'action_type', 'entity_type',
                  'entity_id', 'old_value', 'new_value', 'description', 'ip_address', 'created_at']
        
        return [dict(zip(columns, row)) for row in rows]

