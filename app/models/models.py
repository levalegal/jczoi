from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List
from app.database import Database

@dataclass
class User:
    id: Optional[int]
    username: str
    password: str
    role: str
    full_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    
    @classmethod
    def from_row(cls, row):
        return cls(*row)

@dataclass
class Object:
    id: Optional[int]
    address: str
    area: Optional[float]
    residents: Optional[int]
    building_number: Optional[str]
    apartment_number: Optional[str]
    building_x: Optional[int]
    building_y: Optional[int]
    building_width: Optional[int]
    building_height: Optional[int]
    created_at: Optional[datetime]
    
    @classmethod
    def from_row(cls, row):
        return cls(*row)

@dataclass
class Meter:
    id: Optional[int]
    object_id: int
    type: str
    serial_number: Optional[str]
    installation_date: Optional[date]
    verification_date: Optional[date]
    next_verification_date: Optional[date]
    tariff: float # TO DO REDESIGNER 
    unit: str
    location: Optional[str]
    is_active: int
    created_at: Optional[datetime]
    
    @classmethod
    def from_row(cls, row):
        return cls(*row)

@dataclass
class Reading:
    id: Optional[int]
    meter_id: int
    value: float
    reading_date: date
    previous_reading_id: Optional[int]
    photo_path: Optional[str]
    created_at: Optional[datetime]
    
    @classmethod
    def from_row(cls, row):
        return cls(*row)

class ObjectRepository:
    def __init__(self, db: Database):
        self.db = db
    
    def get_all(self) -> List[Object]:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Objects ORDER BY address")
            rows = cursor.fetchall()
            return [Object.from_row(row) for row in rows]
        except Exception as e:
            print(f"Ошибка получения объектов: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_by_id(self, obj_id: int) -> Optional[Object]:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Objects WHERE id = ?", (obj_id,))
            row = cursor.fetchone()
            return Object.from_row(row) if row else None
        except Exception as e:
            print(f"Ошибка получения объекта по ID {obj_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_by_address(self, address: str) -> Optional[Object]:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Objects WHERE address = ?", (address,))
            row = cursor.fetchone()
            return Object.from_row(row) if row else None
        except Exception as e:
            print(f"Ошибка получения объекта по адресу '{address}': {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def create(self, obj: Object) -> int:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Objects (address, area, residents, building_number, 
                                   apartment_number, building_x, building_y, 
                                   building_width, building_height)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (obj.address, obj.area, obj.residents, obj.building_number,
                  obj.apartment_number, obj.building_x, obj.building_y,
                  obj.building_width, obj.building_height))
            obj_id = cursor.lastrowid
            conn.commit()
            return obj_id
        except Exception as e:
            if conn:
                conn.rollback()
            raise Exception(f"Ошибка создания объекта: {e}")
        finally:
            if conn:
                conn.close()
    
    def update(self, obj: Object):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Objects SET address=?, area=?, residents=?, 
                                 building_number=?, apartment_number=?,
                                 building_x=?, building_y=?, 
                                 building_width=?, building_height=?
                WHERE id=?
            """, (obj.address, obj.area, obj.residents, obj.building_number,
                  obj.apartment_number, obj.building_x, obj.building_y,
                  obj.building_width, obj.building_height, obj.id))
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise Exception(f"Ошибка обновления объекта: {e}")
        finally:
            if conn:
                conn.close()
    
    def delete(self, obj_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Objects WHERE id = ?", (obj_id,))
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise Exception(f"Ошибка удаления объекта: {e}")
        finally:
            if conn:
                conn.close()

class MeterRepository:
    def __init__(self, db: Database):
        self.db = db
    
    def get_by_object_id(self, object_id: int) -> List[Meter]:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Meters WHERE object_id = ?", (object_id,))
            rows = cursor.fetchall()
            return [Meter.from_row(row) for row in rows]
        except Exception as e:
            print(f"Ошибка получения счетчиков для объекта {object_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_by_id(self, meter_id: int) -> Optional[Meter]:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Meters WHERE id = ?", (meter_id,))
            row = cursor.fetchone()
            return Meter.from_row(row) if row else None
        except Exception as e:
            print(f"Ошибка получения счетчика по ID {meter_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_by_serial_number_and_object_id(self, serial_number: str, object_id: int) -> Optional[Meter]:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Meters WHERE serial_number = ? AND object_id = ?", 
                         (serial_number, object_id))
            row = cursor.fetchone()
            return Meter.from_row(row) if row else None
        except Exception as e:
            print(f"Ошибка получения счетчика по серийному номеру {serial_number}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def create(self, meter: Meter) -> int:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Meters (object_id, type, serial_number, installation_date,
                                  verification_date, next_verification_date, tariff,
                                  unit, location, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (meter.object_id, meter.type, meter.serial_number,
                  meter.installation_date, meter.verification_date,
                  meter.next_verification_date, meter.tariff, meter.unit,
                  meter.location, meter.is_active))
            meter_id = cursor.lastrowid
            conn.commit()
            return meter_id
        except Exception as e:
            if conn:
                conn.rollback()
            raise Exception(f"Ошибка создания счетчика: {e}")
        finally:
            if conn:
                conn.close()
    
    def update(self, meter: Meter):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Meters SET object_id=?, type=?, serial_number=?,
                                installation_date=?, verification_date=?,
                                next_verification_date=?, tariff=?, unit=?,
                                location=?, is_active=?
                WHERE id=?
            """, (meter.object_id, meter.type, meter.serial_number,
                  meter.installation_date, meter.verification_date,
                  meter.next_verification_date, meter.tariff, meter.unit,
                  meter.location, meter.is_active, meter.id))
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise Exception(f"Ошибка обновления счетчика: {e}")
        finally:
            if conn:
                conn.close()

class ReadingRepository:
    def __init__(self, db: Database):
        self.db = db
    
    def get_last_reading(self, meter_id: int) -> Optional[Reading]:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM Readings 
                WHERE meter_id = ? 
                ORDER BY reading_date DESC, id DESC 
                LIMIT 1
            """, (meter_id,))
            row = cursor.fetchone()
            return Reading.from_row(row) if row else None
        except Exception as e:
            print(f"Ошибка получения последнего показания для счетчика {meter_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_by_meter_id(self, meter_id: int) -> List[Reading]:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM Readings 
                WHERE meter_id = ? 
                ORDER BY reading_date DESC
            """, (meter_id,))
            rows = cursor.fetchall()
            return [Reading.from_row(row) for row in rows]
        except Exception as e:
            print(f"Ошибка получения показаний для счетчика {meter_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def create(self, reading: Reading) -> int:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            last_reading = self.get_last_reading(reading.meter_id)
            previous_id = last_reading.id if last_reading else None
            
            cursor.execute("""
                INSERT INTO Readings (meter_id, value, reading_date, 
                                    previous_reading_id, photo_path)
                VALUES (?, ?, ?, ?, ?)
            """, (reading.meter_id, reading.value, reading.reading_date,
                  previous_id, reading.photo_path))
            reading_id = cursor.lastrowid
            conn.commit()
            return reading_id
        except Exception as e:
            if conn:
                conn.rollback()
            raise Exception(f"Ошибка создания показания: {e}")
        finally:
            if conn:
                conn.close()

class UserRepository:
    def __init__(self, db: Database):
        self.db = db # TO DO SENSICTION
    
    def get_all(self) -> List[User]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users ORDER BY username")
        rows = cursor.fetchall()
        conn.close()
        return [User.from_row(row) for row in rows]
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return User.from_row(row) if row else None
    
    def get_by_username(self, username: str) -> Optional[User]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return User.from_row(row) if row else None
    
    def get_objects_by_user(self, user_id: int, cache_service=None) -> List[Object]:
        cache_key = f"user_objects_{user_id}"
        if cache_service:
            cached = cache_service.get(cache_key)
            if cached is not None:
                return cached
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.* FROM Objects o
            JOIN UserObjects uo ON o.id = uo.object_id
            WHERE uo.user_id = ?
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        result = [Object.from_row(row) for row in rows]
        
        if cache_service:
            cache_service.set(cache_key, result, ttl_seconds=300)
        
        return result
    
    def get_users_by_object(self, object_id: int) -> List[User]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.* FROM Users u
            JOIN UserObjects uo ON u.id = uo.user_id
            WHERE uo.object_id = ?
        """, (object_id,))
        rows = cursor.fetchall()
        conn.close()
        return [User.from_row(row) for row in rows]
    
    def assign_object_to_user(self, user_id: int, object_id: int):
        conn = self.db.get_connection()
        cursor = conn.cursor() # TO DO SO BAG OR DECSTOP PULL 
        cursor.execute("""
            INSERT OR IGNORE INTO UserObjects (user_id, object_id)
            VALUES (?, ?)
        """, (user_id, object_id))
        conn.commit()
        conn.close()
    
    def unassign_object_from_user(self, user_id: int, object_id: int):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM UserObjects WHERE user_id = ? AND object_id = ?
        """, (user_id, object_id))
        conn.commit()
        conn.close()

