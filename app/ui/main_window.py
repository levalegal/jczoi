from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QMessageBox, QTabWidget,
                             QTableWidget, QTableWidgetItem, QDialog,
                             QLineEdit, QDateEdit, QDoubleSpinBox, QComboBox,
                             QFileDialog, QGroupBox, QFormLayout, QTextEdit,
                             QHeaderView, QMenu, QAbstractItemView)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QAction, QContextMenuEvent
from datetime import date, datetime, timedelta
import os
from app.database import Database
from app.models import Object, Meter, Reading, ObjectRepository, MeterRepository, ReadingRepository, UserRepository
from app.services import CalculationService, ReportGenerator, ChartWidget, NotificationService, ReceiptGenerator, ImportService, AuditService, AuthService
from app.ui.batch_reading_dialog import BatchReadingDialog

class LoginDialog(QDialog):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = None
        self.user_role = None
        self.setWindowTitle("Вход в систему")
        self.setModal(True)
        self.resize(300, 150)
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        form.addRow("Логин:", self.username_edit)
        form.addRow("Пароль:", self.password_edit)
        
        layout.addLayout(form)
        
        buttons = QHBoxLayout()
        login_btn = QPushButton("Войти")
        login_btn.clicked.connect(self.login)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(login_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
    
    def login(self):
        username = self.username_edit.text()
        password = self.password_edit.text()
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, role, password FROM Users 
            WHERE username = ?
        """, (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user_id, user_role, stored_password = result
            if AuthService.verify_password(password, stored_password):
                self.user_id = user_id
                self.user_role = user_role
                self.accept()
            else:
                QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")

class CityMapWidget(QWidget):
    building_clicked = pyqtSignal(int)
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.object_repo = ObjectRepository(db)
        self.buildings = []
        self.map_image_paths = ["city_map.png", "city_map.jpg", "city_map.jpeg", "map.png", "map.jpg"]
        self.map_image_path = None
        self.cached_pixmap = None
        self.cached_size = None
        self.find_map_image()
        self.load_buildings()
        self.setMinimumSize(800, 600)
    
    def find_map_image(self):
        for path in self.map_image_paths:
            if os.path.exists(path):
                self.map_image_path = path
                self.cached_pixmap = None
                return
        self.map_image_path = None
        self.cached_pixmap = None
    
    def load_buildings(self):
        try:
            self.buildings = self.object_repo.get_all()
        except Exception as e:
            print(f"Ошибка загрузки зданий: {e}")
            self.buildings = []
    
    def get_scaled_pixmap(self):
        if not self.map_image_path or not os.path.exists(self.map_image_path):
            return None
        
        current_size = (self.width(), self.height())
        if self.cached_pixmap is None or self.cached_size != current_size:
            pixmap = QPixmap(self.map_image_path)
            if not pixmap.isNull():
                self.cached_pixmap = pixmap.scaled(
                    self.width(), self.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.cached_size = current_size
            else:
                return None
        
        return self.cached_pixmap
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pixmap = self.get_scaled_pixmap()
        if pixmap:
            x_offset = (self.width() - pixmap.width()) // 2
            y_offset = (self.height() - pixmap.height()) // 2
            painter.drawPixmap(x_offset, y_offset, pixmap)
        else:
            self.draw_placeholder(painter)
        
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.setBrush(QColor(255, 0, 0, 100))
        
        for building in self.buildings:
            if building.building_x is not None and building.building_y is not None:
                x = int(building.building_x * self.width() / 1000)
                y = int(building.building_y * self.height() / 1000)
                w = building.building_width or 50
                h = building.building_height or 50
                
                if 0 <= x < self.width() and 0 <= y < self.height():
                    rect = (x, y, w, h)
                    painter.drawRect(*rect)
                    
                    painter.setPen(QPen(QColor(0, 0, 0), 1))
                    text = building.address[:20] if building.address else ""
                    painter.drawText(x, max(10, y - 5), text)
                    painter.setPen(QPen(QColor(255, 0, 0), 2))
    
    def resizeEvent(self, event):
        self.cached_pixmap = None
        self.cached_size = None
        super().resizeEvent(event)
    
    def refresh(self):
        self.cached_pixmap = None
        self.cached_size = None
        self.load_buildings()
        self.update()
    
    def draw_placeholder(self, painter):
        painter.fillRect(self.rect(), QColor(200, 230, 255))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        text = "Загрузите изображение карты города\n(city_map.png, city_map.jpg, map.png, map.jpg)"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
    
    def mousePressEvent(self, event):
        x = event.position().x()
        y = event.position().y()
        
        for building in self.buildings:
            if building.building_x and building.building_y:
                bx = int(building.building_x * self.width() / 1000)
                by = int(building.building_y * self.height() / 1000)
                bw = building.building_width or 50
                bh = building.building_height or 50
                
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    self.building_clicked.emit(building.id)
                    break

class ObjectDialog(QDialog):
    def __init__(self, obj: Object = None, parent=None):
        super().__init__(parent)
        self.object = obj
        self.setWindowTitle("Объект недвижимости" if obj else "Новый объект")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        self.address_edit = QLineEdit()
        self.area_edit = QDoubleSpinBox()
        self.area_edit.setMaximum(10000)
        self.residents_edit = QLineEdit()
        self.building_edit = QLineEdit()
        self.apartment_edit = QLineEdit()
        
        form.addRow("Адрес:", self.address_edit)
        form.addRow("Площадь (м²):", self.area_edit)
        form.addRow("Жильцов:", self.residents_edit)
        form.addRow("Номер дома:", self.building_edit)
        form.addRow("Номер квартиры:", self.apartment_edit)
        
        layout.addLayout(form)
        
        coords_group = QGroupBox("Координаты на карте (0-1000)")
        coords_layout = QFormLayout()
        self.x_edit = QLineEdit()
        self.y_edit = QLineEdit()
        self.w_edit = QLineEdit()
        self.h_edit = QLineEdit()
        
        coords_layout.addRow("X:", self.x_edit)
        coords_layout.addRow("Y:", self.y_edit)
        coords_layout.addRow("Ширина:", self.w_edit)
        coords_layout.addRow("Высота:", self.h_edit)
        coords_group.setLayout(coords_layout)
        layout.addWidget(coords_group)
        
        if obj:
            self.address_edit.setText(obj.address or "")
            self.area_edit.setValue(obj.area or 0)
            self.residents_edit.setText(str(obj.residents) if obj.residents else "")
            self.building_edit.setText(obj.building_number or "")
            self.apartment_edit.setText(obj.apartment_number or "")
            self.x_edit.setText(str(obj.building_x) if obj.building_x else "")
            self.y_edit.setText(str(obj.building_y) if obj.building_y else "")
            self.w_edit.setText(str(obj.building_width) if obj.building_width else "")
            self.h_edit.setText(str(obj.building_height) if obj.building_height else "")
        
        buttons = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.validate_and_accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
    
    def validate_and_accept(self):
        if not self.address_edit.text().strip():
            QMessageBox.warning(self, "Ошибка валидации", "Адрес обязателен для заполнения")
            self.address_edit.setFocus()
            return
        
        try:
            if self.x_edit.text() and not (0 <= int(self.x_edit.text()) <= 1000):
                raise ValueError("X должен быть от 0 до 1000")
            if self.y_edit.text() and not (0 <= int(self.y_edit.text()) <= 1000):
                raise ValueError("Y должен быть от 0 до 1000")
            if self.w_edit.text() and not (0 < int(self.w_edit.text()) <= 1000):
                raise ValueError("Ширина должна быть от 1 до 1000")
            if self.h_edit.text() and not (0 < int(self.h_edit.text()) <= 1000):
                raise ValueError("Высота должна быть от 1 до 1000")
            if self.residents_edit.text() and not self.residents_edit.text().isdigit():
                raise ValueError("Количество жильцов должно быть числом")
            if self.residents_edit.text() and int(self.residents_edit.text()) < 0:
                raise ValueError("Количество жильцов не может быть отрицательным")
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка валидации", str(e))
            return
        
        self.accept()
    
    def get_object(self) -> Object:
        return Object(
            id=self.object.id if self.object else None,
            address=self.address_edit.text(),
            area=self.area_edit.value() if self.area_edit.value() > 0 else None,
            residents=int(self.residents_edit.text()) if self.residents_edit.text().isdigit() else None,
            building_number=self.building_edit.text() or None,
            apartment_number=self.apartment_edit.text() or None,
            building_x=int(self.x_edit.text()) if self.x_edit.text().isdigit() else None,
            building_y=int(self.y_edit.text()) if self.y_edit.text().isdigit() else None,
            building_width=int(self.w_edit.text()) if self.w_edit.text().isdigit() else None,
            building_height=int(self.h_edit.text()) if self.h_edit.text().isdigit() else None,
            created_at=self.object.created_at if self.object else None
        )

class MeterDialog(QDialog):
    def __init__(self, object_id: int, meter: Meter = None, parent=None):
        super().__init__(parent)
        self.object_id = object_id
        self.meter = meter
        self.setWindowTitle("Счетчик" if meter else "Новый счетчик")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Холодная вода", "Горячая вода", "Электроэнергия", "Газ", "Отопление"])
        
        self.serial_edit = QLineEdit()
        self.location_edit = QLineEdit()
        self.tariff_edit = QDoubleSpinBox()
        self.tariff_edit.setMaximum(10000)
        self.tariff_edit.setDecimals(4)
        
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["м³", "кВт·ч", "Гкал"])
        
        self.installation_date = QDateEdit()
        self.installation_date.setCalendarPopup(True)
        self.installation_date.setDate(QDate.currentDate())
        
        self.verification_date = QDateEdit()
        self.verification_date.setCalendarPopup(True)
        self.verification_date.setDate(QDate.currentDate())
        
        form.addRow("Тип:", self.type_combo)
        form.addRow("Серийный номер:", self.serial_edit)
        form.addRow("Место установки:", self.location_edit)
        form.addRow("Тариф:", self.tariff_edit)
        form.addRow("Единица измерения:", self.unit_combo)
        form.addRow("Дата установки:", self.installation_date)
        form.addRow("Дата поверки:", self.verification_date)
        
        layout.addLayout(form)
        
        if meter:
            index = self.type_combo.findText(meter.type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            self.serial_edit.setText(meter.serial_number or "")
            self.location_edit.setText(meter.location or "")
            self.tariff_edit.setValue(meter.tariff)
            index = self.unit_combo.findText(meter.unit)
            if index >= 0:
                self.unit_combo.setCurrentIndex(index)
            if meter.installation_date:
                self.installation_date.setDate(QDate.fromString(str(meter.installation_date), "yyyy-MM-dd"))
            if meter.verification_date:
                self.verification_date.setDate(QDate.fromString(str(meter.verification_date), "yyyy-MM-dd"))
        
        buttons = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.validate_and_accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
    
    def validate_and_accept(self):
        if not self.type_combo.currentText():
            QMessageBox.warning(self, "Ошибка валидации", "Выберите тип счетчика")
            return
        
        if self.tariff_edit.value() <= 0:
            QMessageBox.warning(self, "Ошибка валидации", "Тариф должен быть больше нуля")
            self.tariff_edit.setFocus()
            return
        
        if self.verification_date.date() > QDate.currentDate().addYears(10):
            QMessageBox.warning(self, "Ошибка валидации", "Дата поверки не может быть более чем на 10 лет в будущем")
            return
        
        self.accept()
    
    def get_meter(self) -> Meter:
        verification_date = self.verification_date.date().toPyDate()
        next_verification = verification_date + timedelta(days=365*4)
        
        return Meter(
            id=self.meter.id if self.meter else None,
            object_id=self.object_id,
            type=self.type_combo.currentText(),
            serial_number=self.serial_edit.text() or None,
            installation_date=self.installation_date.date().toPyDate(),
            verification_date=verification_date,
            next_verification_date=next_verification,
            tariff=self.tariff_edit.value(),
            unit=self.unit_combo.currentText(),
            location=self.location_edit.text() or None,
            is_active=1,
            created_at=self.meter.created_at if self.meter else None
        )

class ReadingDialog(QDialog):
    def __init__(self, meter_id: int, parent=None):
        super().__init__(parent)
        self.meter_id = meter_id
        self.db = parent.db if hasattr(parent, 'db') else None
        self.setWindowTitle("Ввод показаний")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout()
        
        self.last_reading = None
        meter_info = None
        if self.db:
            meter_repo = MeterRepository(self.db)
            meter_info = meter_repo.get_by_id(meter_id)
            reading_repo = ReadingRepository(self.db)
            self.last_reading = reading_repo.get_last_reading(meter_id)
        
        if meter_info:
            info_label = QLabel(f"<b>Счетчик:</b> {meter_info.type}<br>"
                              f"<b>Серийный номер:</b> {meter_info.serial_number or 'не указан'}<br>"
                              f"<b>Тариф:</b> {meter_info.tariff} руб/{meter_info.unit}")
            layout.addWidget(info_label)
        
        form = QFormLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        
        self.value_edit = QDoubleSpinBox()
        self.value_edit.setMaximum(999999)
        self.value_edit.setDecimals(2)
        
        self.photo_path = None
        photo_btn = QPushButton("Выбрать фото")
        photo_btn.clicked.connect(self.select_photo)
        self.photo_label = QLabel("Фото не выбрано")
        self.photo_preview = QLabel()
        self.photo_preview.setMaximumSize(200, 200)
        self.photo_preview.setScaledContents(True)
        self.photo_preview.setStyleSheet("border: 2px dashed gray; background-color: #f0f0f0;")
        self.photo_preview.setText("Перетащите фото сюда\nили нажмите 'Выбрать фото'")
        self.photo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_preview.setAcceptDrops(True)
        self.photo_preview.dragEnterEvent = self.drag_enter_event
        self.photo_preview.dropEvent = self.drop_event
        
        form.addRow("Дата:", self.date_edit)
        form.addRow("Показание:", self.value_edit)
        form.addRow("Фото:", photo_btn)
        form.addRow("", self.photo_label)
        form.addRow("Предпросмотр:", self.photo_preview)
        
        layout.addLayout(form)
        
        if self.last_reading:
            info = QLabel(f"Последнее показание: {self.last_reading.value} от {self.last_reading.reading_date}")
            layout.addWidget(info)
            self.value_edit.setMinimum(self.last_reading.value)
        
        buttons = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.validate_and_accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
    
    def validate_and_accept(self):
        value = self.value_edit.value()
        reading_date = self.date_edit.date().toPyDate()
        
        if value < 0:
            QMessageBox.warning(self, "Ошибка валидации", "Показание не может быть отрицательным")
            self.value_edit.setFocus()
            return
        
        if self.last_reading:
            if value < self.last_reading.value:
                QMessageBox.warning(
                    self, "Ошибка валидации",
                    f"Показание не может быть меньше предыдущего ({self.last_reading.value})"
                )
                self.value_edit.setFocus()
                return
            
            if value == self.last_reading.value:
                reply = QMessageBox.question(
                    self, "Подтверждение",
                    "Показание совпадает с предыдущим. Продолжить?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            consumption = value - self.last_reading.value
            days_diff = (reading_date - self.last_reading.reading_date).days
            if days_diff > 0:
                daily_avg = consumption / days_diff
                if daily_avg > 100:
                    reply = QMessageBox.question(
                        self, "Предупреждение",
                        f"Обнаружено большое потребление: {consumption:.2f} за {days_diff} дней\n"
                        f"(в среднем {daily_avg:.2f} в день). Продолжить?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return
        
        if self.db:
            reading_repo = ReadingRepository(self.db)
            existing_readings = reading_repo.get_by_meter_id(self.meter_id)
            for existing in existing_readings:
                if existing.reading_date == reading_date and abs(existing.value - value) < 0.01:
                    QMessageBox.warning(
                        self, "Ошибка валидации",
                        f"Показание с такой датой и значением уже существует"
                    )
                    return
        
        if self.date_edit.date() > QDate.currentDate():
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Дата показания в будущем. Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.accept()
    
    def select_photo(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выбрать фото", "", "Images (*.png *.jpg *.jpeg)")
        if filename:
            self.set_photo(filename)
    
    def set_photo(self, filepath):
        self.photo_path = filepath
        self.photo_label.setText(os.path.basename(filepath))
        
        pixmap = QPixmap(filepath)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, 
                                         Qt.TransformationMode.SmoothTransformation)
            self.photo_preview.setPixmap(scaled_pixmap)
        else:
            self.photo_preview.clear()
    
    def drag_enter_event(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def drop_event(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            filepath = files[0]
            if filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.set_photo(filepath)
            else:
                QMessageBox.warning(self, "Ошибка", "Поддерживаются только изображения (PNG, JPG, JPEG)")
    
    def get_reading(self) -> Reading:
        return Reading(
            id=None,
            meter_id=self.meter_id,
            value=self.value_edit.value(),
            reading_date=self.date_edit.date().toPyDate(),
            previous_reading_id=None,
            photo_path=self.photo_path,
            created_at=None
        )

class BuildingUsersDialog(QDialog):
    def __init__(self, object_id: int, db: Database, parent=None):
        super().__init__(parent)
        self.object_id = object_id
        self.db = db
        self.object_repo = ObjectRepository(db)
        self.meter_repo = MeterRepository(db)
        self.reading_repo = ReadingRepository(db)
        self.calc_service = CalculationService(db)
        self.user_repo = UserRepository(db)
        self.setWindowTitle("Информация об объекте")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        
        obj = self.object_repo.get_by_id(object_id)
        if obj:
            info_text = f"<h2>{obj.address}</h2>"
            if obj.area:
                info_text += f"<p>Площадь: {obj.area} м²</p>"
            if obj.residents:
                info_text += f"<p>Жильцов: {obj.residents}</p>"
            title = QLabel(info_text)
            layout.addWidget(title)
        
        tabs = QTabWidget()
        
        meters_tab = self.create_meters_tab()
        readings_tab = self.create_readings_tab()
        users_tab = self.create_users_tab()
        
        tabs.addTab(meters_tab, "Счетчики")
        tabs.addTab(readings_tab, "Показания")
        tabs.addTab(users_tab, "Пользователи")
        
        layout.addWidget(tabs)
        
        buttons = QHBoxLayout()
        add_meter_btn = QPushButton("Добавить счетчик")
        add_meter_btn.clicked.connect(self.add_meter)
        add_reading_btn = QPushButton("Ввести показания")
        add_reading_btn.clicked.connect(self.add_reading)
        batch_reading_btn = QPushButton("Пакетный ввод")
        batch_reading_btn.clicked.connect(self.batch_reading_from_building)
        edit_coords_btn = QPushButton("Редактировать координаты")
        edit_coords_btn.clicked.connect(self.edit_building_coordinates)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        
        buttons.addWidget(add_meter_btn)
        buttons.addWidget(add_reading_btn)
        buttons.addWidget(batch_reading_btn)
        buttons.addWidget(edit_coords_btn)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
    
    def create_meters_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.meters_table_building = QTableWidget()
        self.meters_table_building.setColumnCount(6)
        self.meters_table_building.setHorizontalHeaderLabels(["ID", "Тип", "Серийный номер", "Тариф", "Поверка", "Статус"])
        self.meters_table_building.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.meters_table_building.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.meters_table_building.customContextMenuRequested.connect(self.show_building_meters_context_menu)
        self.meters_table_building.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        meters = self.meter_repo.get_by_object_id(self.object_id)
        self.meters_table_building.setRowCount(len(meters))
        
        for i, meter in enumerate(meters):
            self.meters_table_building.setItem(i, 0, QTableWidgetItem(str(meter.id)))
            self.meters_table_building.setItem(i, 1, QTableWidgetItem(meter.type))
            self.meters_table_building.setItem(i, 2, QTableWidgetItem(meter.serial_number or ""))
            self.meters_table_building.setItem(i, 3, QTableWidgetItem(f"{meter.tariff} руб/{meter.unit}"))
            self.meters_table_building.setItem(i, 4, QTableWidgetItem(str(meter.next_verification_date) if meter.next_verification_date else ""))
            self.meters_table_building.setItem(i, 5, QTableWidgetItem("Активен" if meter.is_active else "Неактивен"))
        
        layout.addWidget(self.meters_table_building)
        widget.setLayout(layout)
        return widget
    
    def show_building_meters_context_menu(self, position):
        if self.meters_table_building.itemAt(position) is None:
            return
        
        menu = QMenu(self)
        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(self.edit_meter_from_building)
        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(self.delete_meter_from_building)
        
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        menu.exec(self.meters_table_building.viewport().mapToGlobal(position))
    
    def edit_meter_from_building(self):
        row = self.meters_table_building.currentRow()
        if row < 0:
            return
        
        meter_id = int(self.meters_table_building.item(row, 0).text())
        meter = self.meter_repo.get_by_id(meter_id)
        if not meter:
            return
        
        dialog = MeterDialog(self.object_id, meter, parent=self)
        if dialog.exec():
            updated_meter = dialog.get_meter()
            self.meter_repo.update(updated_meter)
            self.close()
            BuildingUsersDialog(self.object_id, self.db, self.parent()).exec()
    
    def delete_meter_from_building(self):
        row = self.meters_table_building.currentRow()
        if row < 0:
            return
        
        meter_id = int(self.meters_table_building.item(row, 0).text())
        meter = self.meter_repo.get_by_id(meter_id)
        if not meter:
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Вы уверены, что хотите удалить счетчик '{meter.type}'?\nВсе связанные показания также будут удалены.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Meters WHERE id = ?", (meter_id,))
            conn.commit()
            conn.close()
            self.close()
            BuildingUsersDialog(self.object_id, self.db, self.parent()).exec()
    
    def create_readings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["ID", "Счетчик", "Дата", "Показание", "Расход", "Сумма"])
        
        meters = self.meter_repo.get_by_object_id(self.object_id)
        all_readings = []
        for meter in meters:
            readings = self.reading_repo.get_by_meter_id(meter.id)
            for reading in readings:
                calc = self.calc_service.process_reading(reading.id)
                all_readings.append((reading, meter, calc))
        
        table.setRowCount(len(all_readings))
        for i, (reading, meter, calc) in enumerate(all_readings):
            table.setItem(i, 0, QTableWidgetItem(str(reading.id)))
            table.setItem(i, 1, QTableWidgetItem(meter.type))
            table.setItem(i, 2, QTableWidgetItem(str(reading.reading_date)))
            table.setItem(i, 3, QTableWidgetItem(str(reading.value)))
            table.setItem(i, 4, QTableWidgetItem(str(calc.get('consumption', 0)) if calc else "0"))
            table.setItem(i, 5, QTableWidgetItem(str(calc.get('amount', 0)) if calc else "0"))
        
        layout.addWidget(table)
        widget.setLayout(layout)
        return widget
    
    def create_users_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        buttons = QHBoxLayout()
        assign_btn = QPushButton("Привязать пользователя к объекту")
        assign_btn.clicked.connect(self.assign_user_to_object)
        unassign_btn = QPushButton("Отвязать пользователя")
        unassign_btn.clicked.connect(self.unassign_user_from_object)
        buttons.addWidget(assign_btn)
        buttons.addWidget(unassign_btn)
        buttons.addStretch()
        layout.addLayout(buttons)
        
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["ID", "Логин", "ФИО", "Роль", "Привязан"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        users = self.user_repo.get_users_by_object(self.object_id)
        
        table.setRowCount(len(users))
        for i, user in enumerate(users):
            table.setItem(i, 0, QTableWidgetItem(str(user.id)))
            table.setItem(i, 1, QTableWidgetItem(user.username or ""))
            table.setItem(i, 2, QTableWidgetItem(user.full_name or ""))
            table.setItem(i, 3, QTableWidgetItem(user.role or ""))
            table.setItem(i, 4, QTableWidgetItem("Да"))
        
        layout.addWidget(table)
        widget.setLayout(layout)
        return widget
    
    def assign_user_to_object(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Привязка пользователя к объекту")
        dialog.setModal(True)
        layout = QVBoxLayout()
        
        user_label = QLabel("Пользователь:")
        user_combo = QComboBox()
        users = self.user_repo.get_all()
        assigned_user_ids = {u.id for u in self.user_repo.get_users_by_object(self.object_id)}
        for user in users:
            if user.id not in assigned_user_ids:
                user_combo.addItem(f"{user.username} ({user.full_name or 'без имени'})", user.id)
        
        if user_combo.count() == 0:
            QMessageBox.information(self, "Информация", "Все пользователи уже привязаны к этому объекту")
            return
        
        layout.addWidget(user_label)
        layout.addWidget(user_combo)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Привязать")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        dialog.setLayout(layout)
        if dialog.exec():
            user_id = user_combo.currentData()
            self.user_repo.assign_object_to_user(user_id, self.object_id)
            self.parent().cache_service.clear()
            user = self.user_repo.get_by_id(user_id)
            self.parent().audit_service.log_action(
                self.parent().user_id, self.parent().username,
                'UPDATE', 'UserObject', user_id,
                new_value=f"Привязан к объекту ID: {self.object_id}",
                description=f"Пользователь '{user.username if user else user_id}' привязан к объекту '{self.object_repo.get_by_id(self.object_id).address if self.object_repo.get_by_id(self.object_id) else self.object_id}'"
            )
            QMessageBox.information(self, "Успех", "Пользователь привязан к объекту")
            self.close()
            BuildingUsersDialog(self.object_id, self.db, self.parent()).exec()
    
    def unassign_user_from_object(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Отвязка пользователя от объекта")
        dialog.setModal(True)
        layout = QVBoxLayout()
        
        user_label = QLabel("Пользователь:")
        user_combo = QComboBox()
        users = self.user_repo.get_users_by_object(self.object_id)
        if not users:
            QMessageBox.information(self, "Информация", "Нет привязанных пользователей")
            return
        
        for user in users:
            user_combo.addItem(f"{user.username} ({user.full_name or 'без имени'})", user.id)
        
        layout.addWidget(user_label)
        layout.addWidget(user_combo)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Отвязать")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        dialog.setLayout(layout)
        if dialog.exec():
            user_id = user_combo.currentData()
            user = self.user_repo.get_by_id(user_id)
            self.user_repo.unassign_object_from_user(user_id, self.object_id)
            self.parent().cache_service.clear()
            self.parent().audit_service.log_action(
                self.parent().user_id, self.parent().username,
                'UPDATE', 'UserObject', user_id,
                old_value=f"Привязан к объекту ID: {self.object_id}",
                description=f"Пользователь '{user.username if user else user_id}' отвязан от объекта '{self.object_repo.get_by_id(self.object_id).address if self.object_repo.get_by_id(self.object_id) else self.object_id}'"
            )
            QMessageBox.information(self, "Успех", "Пользователь отвязан от объекта")
            self.close()
            BuildingUsersDialog(self.object_id, self.db, self.parent()).exec()
    
    def edit_building_coordinates(self):
        obj = self.object_repo.get_by_id(self.object_id)
        if not obj:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Редактирование координат здания")
        dialog.setModal(True)
        layout = QVBoxLayout()
        
        info_label = QLabel(f"<b>Объект:</b> {obj.address}")
        layout.addWidget(info_label)
        
        coords_group = QGroupBox("Координаты на карте (0-1000)")
        coords_layout = QFormLayout()
        
        x_edit = QLineEdit()
        x_edit.setText(str(obj.building_x) if obj.building_x else "")
        y_edit = QLineEdit()
        y_edit.setText(str(obj.building_y) if obj.building_y else "")
        w_edit = QLineEdit()
        w_edit.setText(str(obj.building_width) if obj.building_width else "50")
        h_edit = QLineEdit()
        h_edit.setText(str(obj.building_height) if obj.building_height else "50")
        
        coords_layout.addRow("X:", x_edit)
        coords_layout.addRow("Y:", y_edit)
        coords_layout.addRow("Ширина:", w_edit)
        coords_layout.addRow("Высота:", h_edit)
        coords_group.setLayout(coords_layout)
        layout.addWidget(coords_group)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Сохранить")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        dialog.setLayout(layout)
        if dialog.exec():
            try:
                old_obj_values = {
                    'building_x': obj.building_x, 'building_y': obj.building_y,
                    'building_width': obj.building_width, 'building_height': obj.building_height
                }
                
                if x_edit.text().strip():
                    x_val = int(x_edit.text())
                    if not (0 <= x_val <= 1000):
                        raise ValueError("X должен быть от 0 до 1000")
                    obj.building_x = x_val
                else:
                    obj.building_x = None
                
                if y_edit.text().strip():
                    y_val = int(y_edit.text())
                    if not (0 <= y_val <= 1000):
                        raise ValueError("Y должен быть от 0 до 1000")
                    obj.building_y = y_val
                else:
                    obj.building_y = None
                
                if w_edit.text().strip():
                    w_val = int(w_edit.text())
                    if not (0 < w_val <= 1000):
                        raise ValueError("Ширина должна быть от 1 до 1000")
                    obj.building_width = w_val
                else:
                    obj.building_width = None
                
                if h_edit.text().strip():
                    h_val = int(h_edit.text())
                    if not (0 < h_val <= 1000):
                        raise ValueError("Высота должна быть от 1 до 1000")
                    obj.building_height = h_val
                else:
                    obj.building_height = None
                
                self.object_repo.update(obj)
                self.parent().cache_service.clear()
                
                new_obj_values = {
                    'building_x': obj.building_x, 'building_y': obj.building_y,
                    'building_width': obj.building_width, 'building_height': obj.building_height
                }
                self.parent().audit_service.log_action(
                    self.parent().user_id, self.parent().username,
                    'UPDATE', 'Object', obj.id,
                    old_value=str(old_obj_values), new_value=str(new_obj_values),
                    description=f"Обновлены координаты объекта '{obj.address}'"
                )
                
                QMessageBox.information(self, "Успех", "Координаты обновлены")
                self.close()
                if hasattr(self.parent(), 'refresh_map'):
                    self.parent().refresh_map()
                BuildingUsersDialog(self.object_id, self.db, self.parent()).exec()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка валидации", str(e))
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось обновить координаты: {str(e)}")
    
    def add_meter(self):
        dialog = MeterDialog(self.object_id, parent=self)
        if dialog.exec():
            meter = dialog.get_meter()
            self.meter_repo.create(meter)
            QMessageBox.information(self, "Успех", "Счетчик добавлен")
            self.close()
            BuildingUsersDialog(self.object_id, self.db, self.parent()).exec()
    
    def refresh_meters_tab(self):
        meters = self.meter_repo.get_by_object_id(self.object_id)
        self.meters_table_building.setRowCount(len(meters))
        
        for i, meter in enumerate(meters):
            self.meters_table_building.setItem(i, 0, QTableWidgetItem(str(meter.id)))
            self.meters_table_building.setItem(i, 1, QTableWidgetItem(meter.type))
            self.meters_table_building.setItem(i, 2, QTableWidgetItem(meter.serial_number or ""))
            self.meters_table_building.setItem(i, 3, QTableWidgetItem(f"{meter.tariff} руб/{meter.unit}"))
            self.meters_table_building.setItem(i, 4, QTableWidgetItem(str(meter.next_verification_date) if meter.next_verification_date else ""))
            self.meters_table_building.setItem(i, 5, QTableWidgetItem("Активен" if meter.is_active else "Неактивен"))
    
    def batch_reading_from_building(self):
        batch_dialog = BatchReadingDialog(self.object_id, self.db, self)
        if batch_dialog.exec():
            self.close()
            BuildingUsersDialog(self.object_id, self.db, self.parent()).exec()
    
    def add_reading(self):
        meters = self.meter_repo.get_by_object_id(self.object_id)
        if not meters:
            QMessageBox.warning(self, "Ошибка", "Нет счетчиков для ввода показаний")
            return
        
        if len(meters) == 1:
            selected_meter_id = meters[0].id
        else:
            meter_dialog = QDialog(self)
            meter_dialog.setWindowTitle("Выбор счетчика")
            meter_dialog.setModal(True)
            layout = QVBoxLayout()
            
            combo = QComboBox()
            for meter in meters:
                combo.addItem(f"{meter.type} ({meter.serial_number or 'без номера'})", meter.id)
            layout.addWidget(combo)
            
            buttons = QHBoxLayout()
            ok_btn = QPushButton("ОК")
            ok_btn.clicked.connect(meter_dialog.accept)
            cancel_btn = QPushButton("Отмена")
            cancel_btn.clicked.connect(meter_dialog.reject)
            buttons.addWidget(ok_btn)
            buttons.addWidget(cancel_btn)
            layout.addLayout(buttons)
            
            meter_dialog.setLayout(layout)
            if not meter_dialog.exec():
                return
            selected_meter_id = combo.currentData()
        
        dialog = ReadingDialog(selected_meter_id, self)
        dialog.db = self.db
        if dialog.exec():
            try:
                reading = dialog.get_reading()
                reading_id = self.reading_repo.create(reading)
                self.calc_service.process_reading(reading_id)
                QMessageBox.information(self, "Успех", "Показания сохранены")
                self.close()
                BuildingUsersDialog(self.object_id, self.db, self.parent()).exec()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить показания: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.object_repo = ObjectRepository(self.db)
        self.meter_repo = MeterRepository(self.db)
        self.reading_repo = ReadingRepository(self.db)
        self.calc_service = CalculationService(self.db)
        self.report_generator = ReportGenerator(self.db)
        self.notification_service = NotificationService(self.db)
        self.receipt_generator = ReceiptGenerator(self.db)
        self.import_service = ImportService(self.db)
        self.user_repo = UserRepository(self.db)
        self.audit_service = AuditService(self.db)
        from app.services.cache_service import CacheService
        self.cache_service = CacheService(default_ttl_seconds=300)
        from app.services.backup_service import BackupService
        self.backup_service = BackupService(self.db)
        self.user_id = None
        self.user_role = None
        self.username = None
        self.readings_current_page = 1
        self.readings_page_size = 50
        
        self.backup_service.start_auto_backup(24)
        self.backup_service.cleanup_old_backups(30)
        
        self.init_ui()
        self.show_login()
    
    def show_login(self):
        login = LoginDialog(self.db, self)
        if login.exec():
            self.user_id = login.user_id
            self.user_role = login.user_role
            self.username = login.username_edit.text()
            self.audit_service.log_action(
                self.user_id, self.username,
                'LOGIN', 'User', self.user_id,
                description=f"Пользователь {self.username} вошел в систему"
            )
            self.setup_ui_for_role()
        else:
            self.close()
    
    def setup_ui_for_role(self):
        if self.user_role == 'admin':
            self.setup_admin_ui()
        else:
            self.setup_user_ui()
    
    def setup_admin_ui(self):
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        
        map_tab = self.create_map_tab()
        audit_tab = self.create_audit_log_tab()
        
        tabs.addTab(map_tab, "Карта города")
        tabs.addTab(audit_tab, "Журнал аудита")
    
    def create_map_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        notifications_widget = self.create_notifications_widget()
        layout.addWidget(notifications_widget)
        
        self.city_map = CityMapWidget(self.db)
        self.city_map.building_clicked.connect(self.on_building_clicked)
        layout.addWidget(self.city_map)
        
        buttons = QHBoxLayout()
        add_building_btn = QPushButton("Добавить здание")
        add_building_btn.clicked.connect(self.add_object)
        refresh_btn = QPushButton("Обновить карту")
        refresh_btn.clicked.connect(self.refresh_map)
        load_map_btn = QPushButton("Загрузить карту")
        load_map_btn.clicked.connect(self.load_map_image)
        
        backup_btn = QPushButton("Создать резервную копию")
        backup_btn.clicked.connect(self.create_manual_backup)
        
        buttons.addWidget(add_building_btn)
        buttons.addWidget(refresh_btn)
        buttons.addWidget(load_map_btn)
        buttons.addWidget(backup_btn)
        buttons.addStretch()
        layout.addLayout(buttons)
        
        widget.setLayout(layout)
        return widget
    
    def create_audit_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        filter_group = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout()
        
        user_filter_label = QLabel("Пользователь:")
        self.audit_user_filter = QComboBox()
        self.audit_user_filter.addItem("Все пользователи", None)
        users = self.user_repo.get_all()
        for user in users:
            self.audit_user_filter.addItem(f"{user.username} ({user.full_name or 'без имени'})", user.id)
        
        entity_filter_label = QLabel("Тип сущности:")
        self.audit_entity_filter = QComboBox()
        self.audit_entity_filter.addItem("Все типы", None)
        self.audit_entity_filter.addItem("Object", "Object")
        self.audit_entity_filter.addItem("Meter", "Meter")
        self.audit_entity_filter.addItem("Reading", "Reading")
        self.audit_entity_filter.addItem("User", "User")
        
        action_filter_label = QLabel("Действие:")
        self.audit_action_filter = QComboBox()
        self.audit_action_filter.addItem("Все действия", None)
        self.audit_action_filter.addItem("CREATE", "CREATE")
        self.audit_action_filter.addItem("UPDATE", "UPDATE")
        self.audit_action_filter.addItem("DELETE", "DELETE")
        self.audit_action_filter.addItem("LOGIN", "LOGIN")
        
        filter_btn = QPushButton("Применить")
        filter_btn.clicked.connect(self.load_audit_logs)
        export_btn = QPushButton("Экспорт")
        export_btn.clicked.connect(self.export_audit_logs)
        
        filter_layout.addWidget(user_filter_label)
        filter_layout.addWidget(self.audit_user_filter)
        filter_layout.addWidget(entity_filter_label)
        filter_layout.addWidget(self.audit_entity_filter)
        filter_layout.addWidget(action_filter_label)
        filter_layout.addWidget(self.audit_action_filter)
        filter_layout.addWidget(filter_btn)
        filter_layout.addWidget(export_btn)
        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(7)
        self.audit_table.setHorizontalHeaderLabels(["Дата", "Пользователь", "Действие", "Тип", "ID", "Описание", "Изменения"])
        self.audit_table.horizontalHeader().setStretchLastSection(True)
        self.audit_table.setSortingEnabled(True)
        self.audit_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.audit_table)
        
        self.load_audit_logs()
        
        widget.setLayout(layout)
        return widget
    
    def load_audit_logs(self):
        user_id = self.audit_user_filter.currentData() if hasattr(self, 'audit_user_filter') else None
        entity_type = self.audit_entity_filter.currentData() if hasattr(self, 'audit_entity_filter') else None
        action_type = self.audit_action_filter.currentData() if hasattr(self, 'audit_action_filter') else None
        
        logs = self.audit_service.get_logs(user_id=user_id, entity_type=entity_type, limit=500)
        
        if action_type:
            logs = [log for log in logs if log.get('action_type') == action_type]
        
        self.audit_table.setRowCount(len(logs))
        for i, log in enumerate(logs):
            created_at = log.get('created_at', '')
            if isinstance(created_at, str):
                date_str = created_at
            else:
                date_str = str(created_at)
            
            username = log.get('username', 'N/A')
            action = log.get('action_type', '')
            entity = log.get('entity_type', '')
            entity_id = str(log.get('entity_id', '')) if log.get('entity_id') else ''
            description = log.get('description', '')
            
            changes = ""
            if log.get('old_value'):
                changes += f"Было: {log['old_value']}\n"
            if log.get('new_value'):
                changes += f"Стало: {log['new_value']}"
            
            self.audit_table.setItem(i, 0, QTableWidgetItem(date_str))
            self.audit_table.setItem(i, 1, QTableWidgetItem(username))
            self.audit_table.setItem(i, 2, QTableWidgetItem(action))
            self.audit_table.setItem(i, 3, QTableWidgetItem(entity))
            self.audit_table.setItem(i, 4, QTableWidgetItem(entity_id))
            self.audit_table.setItem(i, 5, QTableWidgetItem(description))
            self.audit_table.setItem(i, 6, QTableWidgetItem(changes))
    
    def export_audit_logs(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Экспорт логов аудита", "", 
            "CSV файлы (*.csv);;Excel файлы (*.xlsx);;Все файлы (*.*)")
        
        if not filename:
            return
        
        try:
            import pandas as pd
            
            user_id = self.audit_user_filter.currentData() if hasattr(self, 'audit_user_filter') else None
            entity_type = self.audit_entity_filter.currentData() if hasattr(self, 'audit_entity_filter') else None
            action_type = self.audit_action_filter.currentData() if hasattr(self, 'audit_action_filter') else None
            
            logs = self.audit_service.get_logs(user_id=user_id, entity_type=entity_type, limit=10000)
            
            if action_type:
                logs = [log for log in logs if log.get('action_type') == action_type]
            
            df = pd.DataFrame(logs)
            if not df.empty:
                if filename.endswith('.xlsx'):
                    df.to_excel(filename, index=False)
                else:
                    df.to_csv(filename, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "Успех", f"Логи экспортированы: {filename}")
            else:
                QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать логи: {str(e)}")
    
    def create_notifications_widget(self):
        group = QGroupBox("Уведомления")
        layout = QVBoxLayout()
        
        notifications = self.notification_service.get_all_notifications()
        
        if notifications:
            text = QTextEdit()
            text.setReadOnly(True)
            text.setMaximumHeight(150)
            text_content = "\n".join([f"• {n['message']}" for n in notifications[:10]])
            text.setPlainText(text_content)
            layout.addWidget(text)
        else:
            label = QLabel("Нет уведомлений")
            layout.addWidget(label)
        
        group.setLayout(layout)
        return group
    
    def setup_user_ui(self):
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        
        objects_tab = self.create_objects_tab()
        meters_tab = self.create_meters_tab()
        readings_tab = self.create_readings_tab()
        reports_tab = self.create_reports_tab()
        
        tabs.addTab(objects_tab, "Объекты")
        tabs.addTab(meters_tab, "Счетчики")
        tabs.addTab(readings_tab, "Показания")
        tabs.addTab(reports_tab, "Отчеты")
    
    def create_dashboard_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        stats_group = QGroupBox("Статистика")
        stats_layout = QHBoxLayout()
        
        objects = self.object_repo.get_all()
        total_meters = 0
        total_readings = 0
        total_amount = 0.0
        
        today = date.today()
        month_start = date(today.year, today.month, 1)
        
        for obj in objects:
            meters = self.meter_repo.get_by_object_id(obj.id)
            total_meters += len(meters)
            
            for meter in meters:
                readings = self.reading_repo.get_by_meter_id(meter.id)
                month_readings = [r for r in readings if r.reading_date >= month_start]
                total_readings += len(month_readings)
                
                for reading in month_readings:
                    calc = self.calc_service.process_reading(reading.id)
                    if calc:
                        total_amount += calc.get('amount', 0)
        
        stats_layout.addWidget(QLabel(f"<b>Объектов:</b> {len(objects)}"))
        stats_layout.addWidget(QLabel(f"<b>Счетчиков:</b> {total_meters}"))
        stats_layout.addWidget(QLabel(f"<b>Показаний за месяц:</b> {total_readings}"))
        stats_layout.addWidget(QLabel(f"<b>К оплате за месяц:</b> {total_amount:.2f} руб."))
        stats_layout.addStretch()
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        notifications_group = QGroupBox("Актуальные уведомления")
        notifications_layout = QVBoxLayout()
        
        notifications = self.notification_service.get_all_notifications()
        if notifications:
            notifications_text = QTextEdit()
            notifications_text.setReadOnly(True)
            notifications_text.setMaximumHeight(200)
            text_content = "\n".join([f"• {n['message']}" for n in notifications[:15]])
            notifications_text.setPlainText(text_content)
            notifications_layout.addWidget(notifications_text)
        else:
            notifications_layout.addWidget(QLabel("Нет уведомлений"))
        
        notifications_group.setLayout(notifications_layout)
        layout.addWidget(notifications_group)
        
        recent_readings_group = QGroupBox("Последние показания")
        recent_layout = QVBoxLayout()
        
        recent_table = QTableWidget()
        recent_table.setColumnCount(5)
        recent_table.setHorizontalHeaderLabels(["Дата", "Объект", "Счетчик", "Показание", "Расход"])
        recent_table.horizontalHeader().setStretchLastSection(True)
        
        all_recent_readings = []
        for obj in objects:
            meters = self.meter_repo.get_by_object_id(obj.id)
            for meter in meters:
                readings = self.reading_repo.get_by_meter_id(meter.id)
                for reading in readings[:3]:
                    calc = self.calc_service.process_reading(reading.id)
                    all_recent_readings.append((reading, meter, obj, calc))
        
        all_recent_readings.sort(key=lambda x: x[0].reading_date, reverse=True)
        all_recent_readings = all_recent_readings[:10]
        
        recent_table.setRowCount(len(all_recent_readings))
        for i, (reading, meter, obj, calc) in enumerate(all_recent_readings):
            recent_table.setItem(i, 0, QTableWidgetItem(str(reading.reading_date)))
            recent_table.setItem(i, 1, QTableWidgetItem(obj.address))
            recent_table.setItem(i, 2, QTableWidgetItem(meter.type))
            recent_table.setItem(i, 3, QTableWidgetItem(str(reading.value)))
            recent_table.setItem(i, 4, QTableWidgetItem(str(calc.get('consumption', 0)) if calc else "0"))
        
        recent_layout.addWidget(recent_table)
        recent_readings_group.setLayout(recent_layout)
        layout.addWidget(recent_readings_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_objects_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Введите адрес для поиска...")
        search_edit.textChanged.connect(lambda text: self.filter_objects_table(text))
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        
        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить объект")
        add_btn.clicked.connect(self.add_object_from_tab)
        buttons_layout.addWidget(add_btn)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.objects_table = QTableWidget()
        self.objects_table.setColumnCount(4)
        self.objects_table.setHorizontalHeaderLabels(["ID", "Адрес", "Площадь", "Жильцов"])
        self.objects_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.objects_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.objects_table.customContextMenuRequested.connect(self.show_objects_context_menu)
        self.objects_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.load_objects_table()
        
        layout.addWidget(self.objects_table)
        widget.setLayout(layout)
        return widget
    
    def load_objects_table(self):
        self.objects_table.setUpdatesEnabled(False)
        try:
            objects = self.object_repo.get_all()
            self.objects_table.setRowCount(len(objects))
            for i, obj in enumerate(objects):
                self.objects_table.setItem(i, 0, QTableWidgetItem(str(obj.id)))
                self.objects_table.setItem(i, 1, QTableWidgetItem(obj.address))
                self.objects_table.setItem(i, 2, QTableWidgetItem(str(obj.area) if obj.area else ""))
                self.objects_table.setItem(i, 3, QTableWidgetItem(str(obj.residents) if obj.residents else ""))
        finally:
            self.objects_table.setUpdatesEnabled(True)
    
    def filter_objects_table(self, text):
        for i in range(self.objects_table.rowCount()):
            match = False
            for j in range(self.objects_table.columnCount()):
                item = self.objects_table.item(i, j)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.objects_table.setRowHidden(i, not match)
    
    def show_objects_context_menu(self, position):
        if self.objects_table.itemAt(position) is None:
            return
        
        menu = QMenu(self)
        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(self.edit_object_from_table)
        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(self.delete_object_from_table)
        
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        menu.exec(self.objects_table.viewport().mapToGlobal(position))
    
    def add_object_from_tab(self):
        dialog = ObjectDialog(parent=self)
        if dialog.exec():
            try:
                obj = dialog.get_object()
                self.object_repo.create(obj)
                self.load_objects_table()
                QMessageBox.information(self, "Успех", "Объект добавлен")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить объект: {str(e)}")
    
    def edit_object_from_table(self):
        row = self.objects_table.currentRow()
        if row < 0:
            return
        
        try:
            obj_id = int(self.objects_table.item(row, 0).text())
            obj = self.object_repo.get_by_id(obj_id)
            if not obj:
                return
            
            old_address = obj.address
            dialog = ObjectDialog(obj, parent=self)
            if dialog.exec():
                updated_obj = dialog.get_object()
                self.object_repo.update(updated_obj)
                self.cache_service.clear()
                self.audit_service.log_action(
                    self.user_id, self.username,
                    'UPDATE', 'Object', obj_id,
                    old_value=f"Адрес: {old_address}",
                    new_value=f"Адрес: {updated_obj.address}",
                    description=f"Обновлен объект: {old_address} -> {updated_obj.address}"
                )
                self.load_objects_table()
                QMessageBox.information(self, "Успех", "Объект обновлен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить объект: {str(e)}")
    
    def delete_object_from_table(self):
        row = self.objects_table.currentRow()
        if row < 0:
            return
        
        try:
            obj_id = int(self.objects_table.item(row, 0).text())
            obj = self.object_repo.get_by_id(obj_id)
            if not obj:
                return
            
            reply = QMessageBox.question(
                self, "Подтверждение",
                f"Вы уверены, что хотите удалить объект '{obj.address}'?\nВсе связанные счетчики и показания также будут удалены.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                old_address = obj.address
                self.object_repo.delete(obj_id)
                self.cache_service.clear()
                self.audit_service.log_action(
                    self.user_id, self.username,
                    'DELETE', 'Object', obj_id,
                    old_value=f"Адрес: {old_address}",
                    description=f"Удален объект: {old_address}"
                )
                self.load_objects_table()
                QMessageBox.information(self, "Успех", "Объект удален")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить объект: {str(e)}")
    
    def create_meters_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Введите тип или серийный номер...")
        search_edit.textChanged.connect(lambda text: self.filter_meters_table(text))
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        
        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить счетчик")
        add_btn.clicked.connect(self.add_meter_from_tab)
        buttons_layout.addWidget(add_btn)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.meters_table = QTableWidget()
        self.meters_table.setColumnCount(5)
        self.meters_table.setHorizontalHeaderLabels(["ID", "Тип", "Серийный номер", "Тариф", "Объект"])
        self.meters_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.meters_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.meters_table.customContextMenuRequested.connect(self.show_meters_context_menu)
        self.meters_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.load_meters_table()
        
        layout.addWidget(self.meters_table)
        widget.setLayout(layout)
        return widget
    
    def load_meters_table(self):
        self.meters_table.setUpdatesEnabled(False)
        try:
            objects = self.object_repo.get_all()
            all_meters = []
            for obj in objects:
                meters = self.meter_repo.get_by_object_id(obj.id)
                all_meters.extend([(m, obj) for m in meters])
            
            self.meters_table.setRowCount(len(all_meters))
            for i, (meter, obj) in enumerate(all_meters):
                self.meters_table.setItem(i, 0, QTableWidgetItem(str(meter.id)))
                self.meters_table.setItem(i, 1, QTableWidgetItem(meter.type))
                self.meters_table.setItem(i, 2, QTableWidgetItem(meter.serial_number or ""))
                self.meters_table.setItem(i, 3, QTableWidgetItem(str(meter.tariff)))
                self.meters_table.setItem(i, 4, QTableWidgetItem(obj.address))
        finally:
            self.meters_table.setUpdatesEnabled(True)
    
    def filter_meters_table(self, text):
        for i in range(self.meters_table.rowCount()):
            match = False
            for j in range(self.meters_table.columnCount()):
                item = self.meters_table.item(i, j)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.meters_table.setRowHidden(i, not match)
    
    def show_meters_context_menu(self, position):
        if self.meters_table.itemAt(position) is None:
            return
        
        menu = QMenu(self)
        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(self.edit_meter_from_table)
        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(self.delete_meter_from_table)
        
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        menu.exec(self.meters_table.viewport().mapToGlobal(position))
    
    def add_meter_from_tab(self):
        objects = self.object_repo.get_all()
        if not objects:
            QMessageBox.warning(self, "Ошибка", "Сначала добавьте объект недвижимости")
            return
        
        if len(objects) == 1:
            object_id = objects[0].id
        else:
            dialog = QDialog(self)
            dialog.setWindowTitle("Выбор объекта")
            dialog.setModal(True)
            layout = QVBoxLayout()
            
            combo = QComboBox()
            for obj in objects:
                combo.addItem(obj.address, obj.id)
            layout.addWidget(combo)
            
            buttons = QHBoxLayout()
            ok_btn = QPushButton("ОК")
            ok_btn.clicked.connect(dialog.accept)
            cancel_btn = QPushButton("Отмена")
            cancel_btn.clicked.connect(dialog.reject)
            buttons.addWidget(ok_btn)
            buttons.addWidget(cancel_btn)
            layout.addLayout(buttons)
            
            dialog.setLayout(layout)
            if not dialog.exec():
                return
            object_id = combo.currentData()
        
        meter_dialog = MeterDialog(object_id, parent=self)
        if meter_dialog.exec():
            try:
                meter = meter_dialog.get_meter()
                meter_id = self.meter_repo.create(meter)
                obj = self.object_repo.get_by_id(object_id)
                self.audit_service.log_action(
                    self.user_id, self.username,
                    'CREATE', 'Meter', meter_id,
                    new_value=f"Тип: {meter.type}, Серийный номер: {meter.serial_number}, Тариф: {meter.tariff}",
                    description=f"Создан счетчик '{meter.type}' для объекта '{obj.address if obj else object_id}'"
                )
                self.load_meters_table()
                QMessageBox.information(self, "Успех", "Счетчик добавлен")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить счетчик: {str(e)}")
    
    def edit_meter_from_table(self):
        row = self.meters_table.currentRow()
        if row < 0:
            return
        
        try:
            meter_id = int(self.meters_table.item(row, 0).text())
            meter = self.meter_repo.get_by_id(meter_id)
            if not meter:
                return
            
            old_meter_values = {
                'type': meter.type, 'serial_number': meter.serial_number,
                'tariff': meter.tariff, 'location': meter.location
            }
            dialog = MeterDialog(meter.object_id, meter, parent=self)
            if dialog.exec():
                updated_meter = dialog.get_meter()
                self.meter_repo.update(updated_meter)
                obj = self.object_repo.get_by_id(updated_meter.object_id)
                new_meter_values = {
                    'type': updated_meter.type, 'serial_number': updated_meter.serial_number,
                    'tariff': updated_meter.tariff, 'location': updated_meter.location
                }
                self.audit_service.log_action(
                    self.user_id, self.username,
                    'UPDATE', 'Meter', meter_id,
                    old_value=str(old_meter_values), new_value=str(new_meter_values),
                    description=f"Обновлен счетчик '{updated_meter.type}' для объекта '{obj.address if obj else updated_meter.object_id}'"
                )
                self.load_meters_table()
                QMessageBox.information(self, "Успех", "Счетчик обновлен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить счетчик: {str(e)}")
    
    def delete_meter_from_table(self):
        row = self.meters_table.currentRow()
        if row < 0:
            return
        
        try:
            meter_id = int(self.meters_table.item(row, 0).text())
            meter = self.meter_repo.get_by_id(meter_id)
            if not meter:
                return
            
            reply = QMessageBox.question(
                self, "Подтверждение",
                f"Вы уверены, что хотите удалить счетчик '{meter.type}'?\nВсе связанные показания также будут удалены.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                old_meter_values = {
                    'type': meter.type, 'serial_number': meter.serial_number,
                    'tariff': meter.tariff
                }
                obj = self.object_repo.get_by_id(meter.object_id)
                conn = self.db.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Meters WHERE id = ?", (meter_id,))
                conn.commit()
                conn.close()
                self.audit_service.log_action(
                    self.user_id, self.username,
                    'DELETE', 'Meter', meter_id,
                    old_value=str(old_meter_values),
                    description=f"Удален счетчик '{meter.type}' для объекта '{obj.address if obj else meter.object_id}'"
                )
                self.load_meters_table()
                QMessageBox.information(self, "Успех", "Счетчик удален")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить счетчик: {str(e)}")
    
    def create_readings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        filter_group = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout()
        
        date_from_label = QLabel("С:")
        self.readings_date_from = QDateEdit()
        self.readings_date_from.setCalendarPopup(True)
        self.readings_date_from.setDate(QDate.currentDate().addMonths(-1))
        
        date_to_label = QLabel("По:")
        self.readings_date_to = QDateEdit()
        self.readings_date_to.setCalendarPopup(True)
        self.readings_date_to.setDate(QDate.currentDate())
        
        object_filter_label = QLabel("Объект:")
        self.readings_object_filter = QComboBox()
        self.readings_object_filter.addItem("Все объекты", None)
        objects = self.object_repo.get_all()
        for obj in objects:
            self.readings_object_filter.addItem(obj.address, obj.id)
        
        meter_filter_label = QLabel("Счетчик:")
        self.readings_meter_filter = QComboBox()
        self.readings_meter_filter.addItem("Все счетчики", None)
        
        filter_btn = QPushButton("Применить фильтр")
        filter_btn.clicked.connect(self.filter_readings_table)
        reset_filter_btn = QPushButton("Сбросить")
        reset_filter_btn.clicked.connect(self.reset_readings_filter)
        
        filter_layout.addWidget(date_from_label)
        filter_layout.addWidget(self.readings_date_from)
        filter_layout.addWidget(date_to_label)
        filter_layout.addWidget(self.readings_date_to)
        filter_layout.addWidget(object_filter_label)
        filter_layout.addWidget(self.readings_object_filter)
        filter_layout.addWidget(meter_filter_label)
        filter_layout.addWidget(self.readings_meter_filter)
        filter_layout.addWidget(filter_btn)
        filter_layout.addWidget(reset_filter_btn)
        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        buttons = QHBoxLayout()
        add_reading_btn = QPushButton("Ввести показания")
        add_reading_btn.clicked.connect(self.add_reading_from_tab)
        batch_reading_btn = QPushButton("Пакетный ввод")
        batch_reading_btn.clicked.connect(self.batch_reading_from_tab)
        import_btn = QPushButton("Импорт из Excel/CSV")
        import_btn.clicked.connect(self.import_readings)
        buttons.addWidget(add_reading_btn)
        buttons.addWidget(batch_reading_btn)
        buttons.addWidget(import_btn)
        buttons.addStretch()
        layout.addLayout(buttons)
        
        self.readings_table = QTableWidget()
        self.readings_table.setColumnCount(7)
        self.readings_table.setHorizontalHeaderLabels(["ID", "Объект", "Счетчик", "Дата", "Показание", "Расход", "Сумма"])
        self.readings_table.horizontalHeader().setStretchLastSection(True)
        self.readings_table.setSortingEnabled(True)
        self.readings_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        pagination_layout = QHBoxLayout()
        self.readings_page_label = QLabel("Страница: 1")
        prev_btn = QPushButton("◄ Предыдущая")
        prev_btn.clicked.connect(self.prev_readings_page)
        next_btn = QPushButton("Следующая ►")
        next_btn.clicked.connect(self.next_readings_page)
        self.readings_current_page = 1
        self.readings_page_size = 50
        
        pagination_layout.addWidget(self.readings_page_label)
        pagination_layout.addWidget(prev_btn)
        pagination_layout.addWidget(next_btn)
        pagination_layout.addStretch()
        
        self.load_readings_table()
        
        layout.addWidget(self.readings_table)
        layout.addLayout(pagination_layout)
        widget.setLayout(layout)
        return widget
    
    def load_readings_table(self):
        date_from = self.readings_date_from.date().toPyDate() if hasattr(self, 'readings_date_from') else None
        date_to = self.readings_date_to.date().toPyDate() if hasattr(self, 'readings_date_to') else None
        object_id = self.readings_object_filter.currentData() if hasattr(self, 'readings_object_filter') else None
        meter_id = self.readings_meter_filter.currentData() if hasattr(self, 'readings_meter_filter') else None
        
        if hasattr(self, 'readings_object_filter') and not hasattr(self, '_meter_filter_connected'):
            self.readings_object_filter.currentIndexChanged.connect(self.update_meter_filter)
            self._meter_filter_connected = True
        
        objects = self.object_repo.get_all()
        if object_id:
            objects = [obj for obj in objects if obj.id == object_id]
        
        all_readings = []
        for obj in objects:
            meters = self.meter_repo.get_by_object_id(obj.id)
            if meter_id:
                meters = [m for m in meters if m.id == meter_id]
            for meter in meters:
                readings = self.reading_repo.get_by_meter_id(meter.id)
                for reading in readings:
                    if date_from and reading.reading_date < date_from:
                        continue
                    if date_to and reading.reading_date > date_to:
                        continue
                    calc = self.calc_service.process_reading(reading.id)
                    all_readings.append((reading, meter, obj, calc))
        
        all_readings.sort(key=lambda x: x[0].reading_date, reverse=True)
        
        total_pages = (len(all_readings) + self.readings_page_size - 1) // self.readings_page_size if all_readings else 1
        if self.readings_current_page > total_pages:
            self.readings_current_page = max(1, total_pages)
        start_idx = (self.readings_current_page - 1) * self.readings_page_size
        end_idx = start_idx + self.readings_page_size
        page_readings = all_readings[start_idx:end_idx]
        
        if hasattr(self, 'readings_page_label'):
            self.readings_page_label.setText(f"Страница: {self.readings_current_page} из {total_pages} (Всего: {len(all_readings)})")
        
        self.readings_table.setUpdatesEnabled(False)
        try:
            self.readings_table.setRowCount(len(page_readings))
            for i, (reading, meter, obj, calc) in enumerate(page_readings):
                self.readings_table.setItem(i, 0, QTableWidgetItem(str(reading.id)))
                self.readings_table.setItem(i, 1, QTableWidgetItem(obj.address))
                self.readings_table.setItem(i, 2, QTableWidgetItem(meter.type))
                self.readings_table.setItem(i, 3, QTableWidgetItem(str(reading.reading_date)))
                self.readings_table.setItem(i, 4, QTableWidgetItem(str(reading.value)))
                self.readings_table.setItem(i, 5, QTableWidgetItem(str(calc.get('consumption', 0)) if calc else "0"))
                self.readings_table.setItem(i, 6, QTableWidgetItem(str(calc.get('amount', 0)) if calc else "0"))
        finally:
            self.readings_table.setUpdatesEnabled(True)
    
    def prev_readings_page(self):
        if self.readings_current_page > 1:
            self.readings_current_page -= 1
            self.load_readings_table()
    
    def next_readings_page(self):
        self.readings_current_page += 1
        self.load_readings_table()
    
    def filter_readings_table(self):
        self.readings_current_page = 1
        self.load_readings_table()
    
    def reset_readings_filter(self):
        self.readings_current_page = 1
        if hasattr(self, 'readings_date_from'):
            self.readings_date_from.setDate(QDate.currentDate().addMonths(-1))
        if hasattr(self, 'readings_date_to'):
            self.readings_date_to.setDate(QDate.currentDate())
        if hasattr(self, 'readings_object_filter'):
            self.readings_object_filter.setCurrentIndex(0)
        if hasattr(self, 'readings_meter_filter'):
            self.readings_meter_filter.setCurrentIndex(0)
        self.load_readings_table()
    
    def update_meter_filter(self):
        if not hasattr(self, 'readings_meter_filter'):
            return
        
        object_id = self.readings_object_filter.currentData()
        self.readings_meter_filter.clear()
        self.readings_meter_filter.addItem("Все счетчики", None)
        
        if object_id:
            meters = self.meter_repo.get_by_object_id(object_id)
            for meter in meters:
                self.readings_meter_filter.addItem(f"{meter.type} ({meter.serial_number or 'без номера'})", meter.id)
    
    def add_reading_from_tab(self):
        objects = self.object_repo.get_all()
        if not objects:
            QMessageBox.warning(self, "Ошибка", "Нет объектов")
            return
        
        meters = []
        for obj in objects:
            obj_meters = self.meter_repo.get_by_object_id(obj.id)
            for meter in obj_meters:
                meters.append((meter, obj))
        
        if not meters:
            QMessageBox.warning(self, "Ошибка", "Нет счетчиков")
            return
        
        if len(meters) == 1:
            selected_meter_id = meters[0][0].id
        else:
            meter_dialog = QDialog(self)
            meter_dialog.setWindowTitle("Выбор счетчика")
            meter_dialog.setModal(True)
            layout = QVBoxLayout()
            
            combo = QComboBox()
            for meter, obj in meters:
                combo.addItem(f"{obj.address} - {meter.type} ({meter.serial_number or 'без номера'})", meter.id)
            layout.addWidget(combo)
            
            buttons = QHBoxLayout()
            ok_btn = QPushButton("ОК")
            ok_btn.clicked.connect(meter_dialog.accept)
            cancel_btn = QPushButton("Отмена")
            cancel_btn.clicked.connect(meter_dialog.reject)
            buttons.addWidget(ok_btn)
            buttons.addWidget(cancel_btn)
            layout.addLayout(buttons)
            
            meter_dialog.setLayout(layout)
            if not meter_dialog.exec():
                return
            selected_meter_id = combo.currentData()
        
        dialog = ReadingDialog(selected_meter_id, self)
        dialog.db = self.db
        if dialog.exec():
            try:
                reading = dialog.get_reading()
                reading_id = self.reading_repo.create(reading)
                self.calc_service.process_reading(reading_id)
                self.audit_service.log_action(
                    self.user_id, self.username,
                    'CREATE', 'Reading', reading_id,
                    new_value=f"Показание: {reading.value}, Дата: {reading.reading_date}",
                    description=f"Добавлено показание для счетчика ID {reading.meter_id}"
                )
                QMessageBox.information(self, "Успех", "Показания сохранены")
                self.setup_ui_for_role()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка", str(e))
    
    def batch_reading_from_tab(self):
        objects = self.object_repo.get_all()
        if not objects:
            QMessageBox.warning(self, "Ошибка", "Нет объектов")
            return
        
        if len(objects) == 1:
            object_id = objects[0].id
        else:
            dialog = QDialog(self)
            dialog.setWindowTitle("Выбор объекта")
            dialog.setModal(True)
            layout = QVBoxLayout()
            
            combo = QComboBox()
            for obj in objects:
                combo.addItem(obj.address, obj.id)
            layout.addWidget(combo)
            
            buttons = QHBoxLayout()
            ok_btn = QPushButton("ОК")
            ok_btn.clicked.connect(dialog.accept)
            cancel_btn = QPushButton("Отмена")
            cancel_btn.clicked.connect(dialog.reject)
            buttons.addWidget(ok_btn)
            buttons.addWidget(cancel_btn)
            layout.addLayout(buttons)
            
            dialog.setLayout(layout)
            if not dialog.exec():
                return
            object_id = combo.currentData()
        
        batch_dialog = BatchReadingDialog(object_id, self.db, self)
        if batch_dialog.exec():
            self.setup_ui_for_role()
    
    def import_readings(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выбрать файл для импорта", "", 
            "Excel файлы (*.xlsx *.xls);;CSV файлы (*.csv);;Все файлы (*.*)")
        
        if not filename:
            return
        
        try:
            if filename.endswith('.csv'):
                result = self.import_service.import_from_csv(filename)
            else:
                result = self.import_service.import_from_excel(filename)
            
            message = f"Импорт завершен:\nУспешно: {result['success']}\nОшибок: {result['errors']}"
            if result['errors'] > 0 and result.get('error_messages'):
                error_text = "\n".join(result['error_messages'][:10])
                if len(result['error_messages']) > 10:
                    error_text += f"\n... и еще {len(result['error_messages']) - 10} ошибок"
                message += f"\n\nОшибки:\n{error_text}"
            
            if result['success'] > 0:
                QMessageBox.information(self, "Импорт завершен", message)
                self.setup_ui_for_role()
            else:
                QMessageBox.warning(self, "Импорт завершен", message)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", f"Не удалось импортировать данные: {str(e)}")
    
    def create_reports_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        period_group = QGroupBox("Период отчета")
        period_layout = QHBoxLayout()
        
        start_label = QLabel("С:")
        self.report_start_date = QDateEdit()
        self.report_start_date.setCalendarPopup(True)
        self.report_start_date.setDate(QDate.currentDate().addMonths(-1))
        
        end_label = QLabel("По:")
        self.report_end_date = QDateEdit()
        self.report_end_date.setCalendarPopup(True)
        self.report_end_date.setDate(QDate.currentDate())
        
        object_label = QLabel("Объект:")
        self.report_object_combo = QComboBox()
        objects = self.object_repo.get_all()
        self.report_object_combo.addItem("Все объекты", None)
        for obj in objects:
            self.report_object_combo.addItem(obj.address, obj.id)
        
        self.report_start_date.dateChanged.connect(self.update_report_chart)
        self.report_end_date.dateChanged.connect(self.update_report_chart)
        self.report_object_combo.currentIndexChanged.connect(self.update_report_chart)
        
        period_layout.addWidget(start_label)
        period_layout.addWidget(self.report_start_date)
        period_layout.addWidget(end_label)
        period_layout.addWidget(self.report_end_date)
        period_layout.addWidget(object_label)
        period_layout.addWidget(self.report_object_combo)
        period_layout.addStretch()
        period_group.setLayout(period_layout)
        layout.addWidget(period_group)
        
        buttons_layout = QHBoxLayout()
        generate_btn = QPushButton("Сформировать отчет")
        generate_btn.clicked.connect(self.generate_report)
        export_excel_btn = QPushButton("Экспорт в Excel")
        export_excel_btn.clicked.connect(self.export_report)
        export_pdf_btn = QPushButton("Экспорт в PDF")
        export_pdf_btn.clicked.connect(self.export_report_pdf)
        print_receipt_btn = QPushButton("Печать квитанции")
        print_receipt_btn.clicked.connect(self.print_receipt)
        buttons_layout.addWidget(generate_btn)
        buttons_layout.addWidget(export_excel_btn)
        buttons_layout.addWidget(export_pdf_btn)
        buttons_layout.addWidget(print_receipt_btn)
        layout.addLayout(buttons_layout)
        
        chart_group = QGroupBox("Графики")
        chart_layout = QVBoxLayout()
        
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Линейный", "Столбчатый", "Областной"])
        self.chart_type_combo.currentIndexChanged.connect(
            lambda: self.update_chart_in_reports(self.chart_type_combo.currentText()))
        chart_layout.addWidget(QLabel("Тип графика:"))
        chart_layout.addWidget(self.chart_type_combo)
        
        self.report_chart_widget = ChartWidget()
        chart_layout.addWidget(self.report_chart_widget)
        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)
        
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        layout.addWidget(self.report_text)
        
        widget.setLayout(layout)
        return widget
    
    def update_chart_in_reports(self, chart_type: str = None):
        if not hasattr(self, 'report_chart_widget') or not hasattr(self, 'chart_type_combo'):
            return
        
        object_id = self.report_object_combo.currentData()
        if not object_id:
            return
        
        start_date = self.report_start_date.date().toPyDate()
        end_date = self.report_end_date.date().toPyDate()
        
        if chart_type is None:
            chart_type = self.chart_type_combo.currentText()
        
        chart_type_map = {"Линейный": "line", "Столбчатый": "bar", "Областной": "area"}
        chart_type_code = chart_type_map.get(chart_type, "line")
        
        meters = self.meter_repo.get_by_object_id(object_id)
        if meters:
            months = max(1, (end_date - start_date).days // 30)
            try:
                fig = self.report_generator.create_consumption_chart(
                    meters[0].id, months, chart_type_code)
                if fig:
                    self.report_chart_widget.set_chart(fig)
            except Exception:
                pass
    
    def update_report_chart(self):
        if hasattr(self, 'chart_type_combo'):
            self.update_chart_in_reports()
    
    def generate_report(self):
        start_date = self.report_start_date.date().toPyDate()
        end_date = self.report_end_date.date().toPyDate()
        object_id = self.report_object_combo.currentData()
        
        if start_date > end_date:
            QMessageBox.warning(self, "Ошибка", "Дата начала не может быть больше даты окончания")
            return
        
        objects_to_report = []
        if object_id:
            obj = self.object_repo.get_by_id(object_id)
            if obj:
                objects_to_report.append(obj)
        else:
            objects_to_report = self.object_repo.get_all()
        
        if not objects_to_report:
            QMessageBox.warning(self, "Ошибка", "Нет объектов для отчета")
            return
        
        report_text = f"ОТЧЕТ ПО ПОКАЗАНИЯМ СЧЕТЧИКОВ\n"
        report_text += f"Период: {start_date} - {end_date}\n"
        report_text += "=" * 80 + "\n\n"
        
        total_amount = 0.0
        
        for obj in objects_to_report:
            report_text += f"Объект: {obj.address}\n"
            report_text += "-" * 80 + "\n"
            
            stats = self.calc_service.get_statistics(obj.id, start_date, end_date)
            
            if not stats:
                report_text += "Нет данных за указанный период\n\n"
                continue
            
            for meter_type, data in stats.items():
                report_text += f"  {meter_type}:\n"
                report_text += f"    Расход: {data['consumption']:.2f}\n"
                report_text += f"    Сумма: {data['amount']:.2f} руб.\n"
                report_text += f"    Количество показаний: {data['readings_count']}\n"
                total_amount += data['amount']
            
            report_text += "\n"
        
        report_text += "=" * 80 + "\n"
        report_text += f"ИТОГО: {total_amount:.2f} руб.\n"
        
        self.report_text.setPlainText(report_text)
    
    def init_ui(self):
        self.setWindowTitle("Система учета показаний счетчиков ЖКХ")
        self.setGeometry(100, 100, 1200, 800)
    
    def on_building_clicked(self, object_id: int):
        dialog = BuildingUsersDialog(object_id, self.db, self)
        dialog.exec()
    
    def add_object(self):
        dialog = ObjectDialog(parent=self)
        if dialog.exec():
            obj = dialog.get_object()
            self.object_repo.create(obj)
            self.refresh_map()
            QMessageBox.information(self, "Успех", "Объект добавлен")
    
    def refresh_map(self):
        if hasattr(self, 'city_map'):
            self.city_map.refresh()
    
    def load_map_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выбрать изображение карты", "", 
            "Images (*.png *.jpg *.jpeg *.bmp)")
        if filename:
            import shutil
            target_path = "city_map" + os.path.splitext(filename)[1]
            shutil.copy2(filename, target_path)
            self.city_map.find_map_image()
            self.city_map.update()
            QMessageBox.information(self, "Успех", f"Карта загружена: {target_path}")
    
    def create_manual_backup(self):
        try:
            backup_path = self.backup_service.create_backup()
            QMessageBox.information(self, "Успех", f"Резервная копия создана:\n{backup_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать резервную копию: {str(e)}")
    
    def export_report(self):
        start_date = self.report_start_date.date().toPyDate()
        end_date = self.report_end_date.date().toPyDate()
        object_id = self.report_object_combo.currentData()
        
        if start_date > end_date:
            QMessageBox.warning(self, "Ошибка", "Дата начала не может быть больше даты окончания")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет", "", "Excel (*.xlsx)")
        if filename:
            objects_to_export = []
            if object_id:
                obj = self.object_repo.get_by_id(object_id)
                if obj:
                    objects_to_export.append(obj)
            else:
                objects_to_export = self.object_repo.get_all()
            
            if not objects_to_export:
                QMessageBox.warning(self, "Ошибка", "Нет объектов для экспорта")
                return
            
            import pandas as pd
            all_data = []
            
            for obj in objects_to_export:
                df = self.report_generator.generate_consumption_report(
                    obj.id, start_date, end_date)
                if not df.empty:
                    df.insert(0, 'Объект', obj.address)
                    all_data.append(df)
            
            if all_data:
                try:
                    combined_df = pd.concat(all_data, ignore_index=True)
                    self.report_generator.export_to_excel(combined_df, filename)
                    QMessageBox.information(self, "Успех", "Отчет сохранен")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить отчет: {str(e)}")
            else:
                QMessageBox.warning(self, "Ошибка", "Нет данных для экспорта")
    
    def export_report_pdf(self):
        start_date = self.report_start_date.date().toPyDate()
        end_date = self.report_end_date.date().toPyDate()
        object_id = self.report_object_combo.currentData()
        
        if start_date > end_date:
            QMessageBox.warning(self, "Ошибка", "Дата начала не может быть больше даты окончания")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет PDF", "", "PDF (*.pdf)")
        if filename:
            try:
                self.receipt_generator.export_report_to_pdf(
                    object_id, start_date, end_date, filename)
                QMessageBox.information(self, "Успех", "PDF отчет сохранен")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать PDF: {str(e)}")
    
    def print_receipt(self):
        object_id = self.report_object_combo.currentData()
        if not object_id:
            QMessageBox.warning(self, "Ошибка", "Выберите объект для печати квитанции")
            return
        
        start_date = self.report_start_date.date().toPyDate()
        end_date = self.report_end_date.date().toPyDate()
        
        if start_date > end_date:
            QMessageBox.warning(self, "Ошибка", "Дата начала не может быть больше даты окончания")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить квитанцию", "", "PDF (*.pdf)")
        if filename:
            try:
                self.receipt_generator.generate_receipt(
                    object_id, start_date, end_date, filename)
                QMessageBox.information(
                    self, "Успех", 
                    f"Квитанция сохранена: {filename}\nМожно открыть для печати")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать квитанцию: {str(e)}")

