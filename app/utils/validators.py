from PyQt6.QtWidgets import QLineEdit, QDoubleSpinBox, QDateEdit
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QDate

class FieldValidator:
    @staticmethod
    def set_error_style(widget):
        widget.setStyleSheet("border: 2px solid red;")
    
    @staticmethod
    def clear_error_style(widget):
        widget.setStyleSheet("")
    
    @staticmethod
    def validate_required(widget, value, field_name: str = ""):
        if not value or (isinstance(value, str) and not value.strip()):
            FieldValidator.set_error_style(widget)
            return False, f"Поле '{field_name}' обязательно для заполнения"
        FieldValidator.clear_error_style(widget)
        return True, ""
    
    @staticmethod
    def validate_positive_number(widget, value, field_name: str = ""):
        try:
            num = float(value) if isinstance(value, str) else value
            if num < 0:
                FieldValidator.set_error_style(widget)
                return False, f"Поле '{field_name}' должно быть положительным числом"
            FieldValidator.clear_error_style(widget)
            return True, ""
        except (ValueError, TypeError):
            FieldValidator.set_error_style(widget)
            return False, f"Поле '{field_name}' должно быть числом"
    
    @staticmethod
    def validate_range(widget, value, min_val, max_val, field_name: str = ""):
        try:
            num = float(value) if isinstance(value, str) else value
            if num < min_val or num > max_val:
                FieldValidator.set_error_style(widget)
                return False, f"Поле '{field_name}' должно быть в диапазоне от {min_val} до {max_val}"
            FieldValidator.clear_error_style(widget)
            return True, ""
        except (ValueError, TypeError):
            FieldValidator.set_error_style(widget)
            return False, f"Поле '{field_name}' должно быть числом"
    
    @staticmethod
    def validate_date_not_future(widget, date: QDate, field_name: str = ""):
        if date > QDate.currentDate():
            FieldValidator.set_error_style(widget)
            return False, f"Дата '{field_name}' не может быть в будущем"
        FieldValidator.clear_error_style(widget)
        return True, ""
    
    @staticmethod
    def validate_integer(widget, value, field_name: str = ""):
        try:
            if isinstance(value, str):
                int(value)
            FieldValidator.clear_error_style(widget)
            return True, ""
        except (ValueError, TypeError):
            FieldValidator.set_error_style(widget)
            return False, f"Поле '{field_name}' должно быть целым числом"

