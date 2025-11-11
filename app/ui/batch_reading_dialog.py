from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
                             QDateEdit, QHeaderView, QAbstractItemView)
from PyQt6.QtCore import QDate
from datetime import date
from app.database import Database
from app.models import MeterRepository, ReadingRepository, Reading
from app.services import CalculationService

class BatchReadingDialog(QDialog):
    def __init__(self, object_id: int, db: Database, parent=None):
        super().__init__(parent)
        self.object_id = object_id
        self.db = db
        self.meter_repo = MeterRepository(db)
        self.reading_repo = ReadingRepository(db)
        self.calc_service = CalculationService(db)
        self.setWindowTitle("Пакетный ввод показаний")
        self.setModal(True)
        self.resize(700, 500)
        
        layout = QVBoxLayout()
        
        info_label = QLabel("Введите показания для всех счетчиков объекта")
        layout.addWidget(info_label)
        
        date_layout = QHBoxLayout()
        date_label = QLabel("Дата показаний:")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        self.table = QTableWidget()
        meters = self.meter_repo.get_by_object_id(object_id)
        self.table.setRowCount(len(meters))
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Счетчик", "Последнее показание", "Новое показание", "Расход"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        
        self.meters_data = []
        for i, meter in enumerate(meters):
            last_reading = self.reading_repo.get_last_reading(meter.id)
            last_value = last_reading.value if last_reading else 0.0
            
            self.table.setItem(i, 0, QTableWidgetItem(f"{meter.type} ({meter.serial_number or 'без номера'})"))
            self.table.setItem(i, 1, QTableWidgetItem(str(last_value)))
            
            value_item = QTableWidgetItem()
            value_item.setData(0, last_value)
            self.table.setItem(i, 2, value_item)
            
            self.meters_data.append({
                'meter_id': meter.id,
                'meter': meter,
                'last_value': last_value,
                'row': i
            })
        
        layout.addWidget(self.table)
        
        buttons = QHBoxLayout()
        save_btn = QPushButton("Сохранить все")
        save_btn.clicked.connect(self.save_all)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
    
    def save_all(self):
        errors = []
        saved_count = 0
        reading_date = self.date_edit.date().toPyDate()
        
        for data in self.meters_data:
            row = data['row']
            value_item = self.table.item(row, 2)
            
            if not value_item or not value_item.text().strip():
                continue
            
            try:
                new_value = float(value_item.text())
                
                if new_value < 0:
                    errors.append(f"{data['meter'].type}: показание не может быть отрицательным")
                    continue
                
                if new_value < data['last_value']:
                    errors.append(f"{data['meter'].type}: показание ({new_value}) меньше предыдущего ({data['last_value']})")
                    continue
                
                if new_value == data['last_value']:
                    errors.append(f"{data['meter'].type}: показание совпадает с предыдущим")
                    continue
                
                existing_readings = self.reading_repo.get_by_meter_id(data['meter_id'])
                for existing in existing_readings:
                    if existing.reading_date == reading_date and abs(existing.value - new_value) < 0.01:
                        errors.append(f"{data['meter'].type}: показание с такой датой уже существует")
                        break
                else:
                    reading = Reading(
                        id=None,
                        meter_id=data['meter_id'],
                        value=new_value,
                        reading_date=reading_date,
                        previous_reading_id=None,
                        photo_path=None,
                        created_at=None
                    )
                    
                    reading_id = self.reading_repo.create(reading)
                    self.calc_service.process_reading(reading_id)
                    
                    consumption = new_value - data['last_value']
                    self.table.setItem(row, 3, QTableWidgetItem(f"{consumption:.2f}"))
                    saved_count += 1
                
            except ValueError:
                errors.append(f"{data['meter'].type}: неверное значение показания")
            except Exception as e:
                errors.append(f"{data['meter'].type}: ошибка сохранения - {str(e)}")
        
        if errors:
            error_msg = "Ошибки при сохранении:\n" + "\n".join(errors)
            QMessageBox.warning(self, "Ошибки", error_msg)
        
        if saved_count > 0:
            QMessageBox.information(self, "Успех", f"Сохранено показаний: {saved_count}")
            self.accept()

