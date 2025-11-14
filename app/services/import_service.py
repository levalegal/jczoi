from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from app.database import Database
from app.models import MeterRepository, ReadingRepository, Reading
from app.services import CalculationService

class ImportService:
    def __init__(self, db: Database):
        self.db = db
        self.meter_repo = MeterRepository(db)
        self.reading_repo = ReadingRepository(db)
        self.calc_service = CalculationService(db)
    
    def import_from_excel(self, file_path: str) -> Dict[str, int]:
        try:
            df = pd.read_excel(file_path)
            return self._process_dataframe(df)
        except Exception as e:
            raise Exception(f"Ошибка при чтении Excel файла: {str(e)}")
    
    def import_from_csv(self, file_path: str, delimiter: str = ',') -> Dict[str, int]:
        try:
            df = pd.read_csv(file_path, delimiter=delimiter, encoding='utf-8')
            return self._process_dataframe(df)
        except Exception as e:
            try:
                df = pd.read_csv(file_path, delimiter=delimiter, encoding='cp1251')
                return self._process_dataframe(df)
            except:
                raise Exception(f"Ошибка при чтении CSV файла: {str(e)}")
    
    def _process_dataframe(self, df: pd.DataFrame) -> Dict[str, int]:
        required_columns = ['meter_id', 'value', 'reading_date']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise Exception(f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}")
        
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                meter_id = int(row['meter_id'])
                value = float(row['value'])
                reading_date = pd.to_datetime(row['reading_date']).date()
                
                meter = self.meter_repo.get_by_id(meter_id)
                if not meter:
                    error_count += 1
                    errors.append(f"Строка {index + 2}: счетчик с ID {meter_id} не найден")
                    continue
                
                last_reading = self.reading_repo.get_last_reading(meter_id)
                if last_reading and value < last_reading.value:
                    error_count += 1
                    errors.append(f"Строка {index + 2}: показание ({value}) меньше предыдущего ({last_reading.value})")
                    continue
                
                reading = Reading(
                    id=None,
                    meter_id=meter_id,
                    value=value,
                    reading_date=reading_date,
                    previous_reading_id=None,
                    photo_path=None,
                    created_at=None
                )
                
                reading_id = self.reading_repo.create(reading)
                self.calc_service.process_reading(reading_id)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"Строка {index + 2}: {str(e)}")
        
        return {
            'success': success_count,
            'errors': error_count,
            'error_messages': errors
        }
    
    def get_template_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(columns=['meter_id', 'value', 'reading_date'])

