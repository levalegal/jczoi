from datetime import date, timedelta
from typing import List, Dict
from app.database import Database
from app.models import ObjectRepository, MeterRepository, ReadingRepository

class NotificationService:
    def __init__(self, db: Database):
        self.db = db
        self.object_repo = ObjectRepository(db)
        self.meter_repo = MeterRepository(db)
        self.reading_repo = ReadingRepository(db)
    
    def check_verification_due(self, days_ahead: int = 30) -> List[Dict]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        check_date = date.today() + timedelta(days=days_ahead)
        
        cursor.execute("""
            SELECT m.id, m.type, m.serial_number, m.next_verification_date,
                   o.address
            FROM Meters m
            JOIN Objects o ON m.object_id = o.id
            WHERE m.next_verification_date <= ? AND m.is_active = 1
            ORDER BY m.next_verification_date
        """, (check_date,))
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                'type': 'verification',
                'meter_id': row[0],
                'meter_type': row[1],
                'serial_number': row[2],
                'verification_date': row[3],
                'address': row[4],
                'message': f"Счетчик {row[1]} ({row[2]}) требует поверки до {row[3]}"
            })
        
        conn.close()
        return notifications
    
    def check_readings_due(self, days_before: int = 3) -> List[Dict]:
        today = date.today()
        month_start = date(today.year, today.month, 1)
        last_month_end = month_start - timedelta(days=1)
        last_month_start = date(last_month_end.year, last_month_end.month, 1)
        
        deadline = today + timedelta(days=days_before)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT m.id, m.type, m.serial_number, o.address,
                   MAX(r.reading_date) as last_reading_date
            FROM Meters m
            JOIN Objects o ON m.object_id = o.id
            LEFT JOIN Readings r ON m.id = r.meter_id
            WHERE m.is_active = 1
            GROUP BY m.id, m.type, m.serial_number, o.address
            HAVING last_reading_date IS NULL 
                OR last_reading_date < ?
        """, (last_month_start,))
        
        notifications = []
        for row in cursor.fetchall():
            last_date = row[4] if row[4] else "никогда"
            notifications.append({
                'type': 'reading_due',
                'meter_id': row[0],
                'meter_type': row[1],
                'serial_number': row[2],
                'address': row[3],
                'last_reading': last_date,
                'message': f"Требуется передать показания счетчика {row[1]} ({row[2]}) до {deadline}"
            })
        
        conn.close()
        return notifications
    
    def get_all_notifications(self) -> List[Dict]:
        notifications = []
        notifications.extend(self.check_verification_due())
        notifications.extend(self.check_readings_due())
        return notifications
    
    def create_notification(self, user_id: int, object_id: int, 
                          notification_type: str, message: str):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Notifications (user_id, object_id, type, message)
            VALUES (?, ?, ?, ?)
        """, (user_id, object_id, notification_type, message))
        conn.commit()
        conn.close()
    
    def mark_as_read(self, notification_id: int):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Notifications SET is_read = 1 WHERE id = ?
        """, (notification_id,))
        conn.commit()
        conn.close()

