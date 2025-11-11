from datetime import date, timedelta
from typing import Optional, Dict, List
from app.models import Reading, Meter, ReadingRepository, MeterRepository
from app.database import Database

class CalculationService:
    def __init__(self, db: Database):
        self.db = db
        self.reading_repo = ReadingRepository(db)
        self.meter_repo = MeterRepository(db)
    
    def calculate_consumption(self, current_reading: Reading, 
                             previous_reading: Optional[Reading]) -> float:
        if previous_reading is None:
            return 0.0
        return max(0.0, current_reading.value - previous_reading.value)
    
    def calculate_amount(self, consumption: float, tariff: float) -> float:
        return round(consumption * tariff, 2)
    
    def process_reading(self, reading_id: int) -> Dict:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM Readings WHERE id = ?", (reading_id,))
            row = cursor.fetchone()
            if not row:
                return {}
            
            reading = Reading.from_row(row)
            meter = self.meter_repo.get_by_id(reading.meter_id)
            if not meter:
                return {}
            
            previous_reading = self.reading_repo.get_last_reading(reading.meter_id)
            if previous_reading and previous_reading.id == reading.id:
                cursor.execute("""
                    SELECT * FROM Readings 
                    WHERE meter_id = ? AND id != ? 
                    ORDER BY reading_date DESC, id DESC 
                    LIMIT 1
                """, (reading.meter_id, reading.id))
                prev_row = cursor.fetchone()
                previous_reading = Reading.from_row(prev_row) if prev_row else None
            
            consumption = self.calculate_consumption(reading, previous_reading)
            amount = self.calculate_amount(consumption, meter.tariff)
            
            cursor.execute("""
                INSERT OR REPLACE INTO Calculations 
                (reading_id, consumption, amount, tariff)
                VALUES (?, ?, ?, ?)
            """, (reading_id, consumption, amount, meter.tariff))
            
            conn.commit()
            return {
                'consumption': consumption,
                'amount': amount,
                'tariff': meter.tariff,
                'unit': meter.unit
            }
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Ошибка обработки показания {reading_id}: {e}")
            return {}
        finally:
            if conn:
                conn.close()
    
    def get_statistics(self, object_id: int, start_date: date, 
                      end_date: date) -> Dict:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT m.type, SUM(c.consumption) as total_consumption,
                       SUM(c.amount) as total_amount, COUNT(*) as readings_count
                FROM Calculations c
                JOIN Readings r ON c.reading_id = r.id
                JOIN Meters m ON r.meter_id = m.id
                WHERE m.object_id = ? 
                AND r.reading_date BETWEEN ? AND ?
                GROUP BY m.type
            """, (object_id, start_date, end_date))
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = {
                    'consumption': row[1] or 0.0,
                    'amount': row[2] or 0.0,
                    'readings_count': row[3]
                }
            
            return stats
        except Exception as e:
            print(f"Ошибка получения статистики для объекта {object_id}: {e}")
            return {}
        finally:
            if conn:
                conn.close()
    
    def get_monthly_consumption(self, meter_id: int, months: int = 12) -> List[Dict]:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            end_date = date.today()
            start_date = end_date - timedelta(days=months * 30)
            
            cursor.execute("""
                SELECT r.reading_date, c.consumption, c.amount
                FROM Readings r
                JOIN Calculations c ON r.id = c.reading_id
                WHERE r.meter_id = ? AND r.reading_date >= ?
                ORDER BY r.reading_date
            """, (meter_id, start_date))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'date': row[0],
                    'consumption': row[1],
                    'amount': row[2]
                })
            
            return results
        except Exception as e:
            print(f"Ошибка получения месячного потребления для счетчика {meter_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

