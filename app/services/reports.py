import os
from datetime import date, datetime
from typing import List, Dict, Optional
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from app.database import Database
from app.models import ObjectRepository, MeterRepository, ReadingRepository
from app.services.calculations import CalculationService

class ReportGenerator:
    def __init__(self, db: Database):
        self.db = db
        self.object_repo = ObjectRepository(db)
        self.meter_repo = MeterRepository(db)
        self.reading_repo = ReadingRepository(db)
        self.calc_service = CalculationService(db)
    
    def generate_consumption_report(self, object_id: int, 
                                   start_date: date, end_date: date) -> pd.DataFrame:
        conn = self.db.get_connection()
        
        query = """
            SELECT 
                m.type as 'Тип счетчика',
                m.serial_number as 'Серийный номер',
                r.reading_date as 'Дата',
                r.value as 'Показание',
                c.consumption as 'Расход',
                c.amount as 'Сумма',
                m.unit as 'Ед. изм.'
            FROM Readings r
            JOIN Meters m ON r.meter_id = m.id
            LEFT JOIN Calculations c ON r.id = c.reading_id
            WHERE m.object_id = ? 
            AND r.reading_date BETWEEN ? AND ?
            ORDER BY m.type, r.reading_date DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(object_id, start_date, end_date))
        conn.close()
        return df
    
    def export_to_excel(self, df: pd.DataFrame, filename: str):
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'
        df.to_excel(filename, index=False, engine='openpyxl')
        return filename
    
    def create_consumption_chart(self, meter_id: int, months: int = 12, chart_type: str = 'line'):
        data = self.calc_service.get_monthly_consumption(meter_id, months)
        
        if not data:
            return None
        
        dates = [row['date'] for row in data]
        consumption = [row['consumption'] for row in data]
        amounts = [row['amount'] for row in data]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == 'bar':
            ax.bar(range(len(dates)), consumption, color='steelblue', alpha=0.7)
            ax.set_xticks(range(len(dates)))
            ax.set_xticklabels([str(d) for d in dates], rotation=45, ha='right')
        elif chart_type == 'area':
            ax.fill_between(range(len(dates)), consumption, alpha=0.5, color='steelblue')
            ax.plot(range(len(dates)), consumption, marker='o', linewidth=2, markersize=6)
            ax.set_xticks(range(len(dates)))
            ax.set_xticklabels([str(d) for d in dates], rotation=45, ha='right')
        else:
            ax.plot(dates, consumption, marker='o', linewidth=2, markersize=6, label='Расход')
            plt.xticks(rotation=45)
        
        ax.set_xlabel('Дата')
        ax.set_ylabel('Расход')
        ax.set_title('График потребления')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        return fig
    
    def create_comparison_chart(self, object_id: int, start_date: date, end_date: date):
        stats = self.calc_service.get_statistics(object_id, start_date, end_date)
        
        if not stats:
            return None
        
        meter_types = list(stats.keys())
        consumptions = [stats[mt]['consumption'] for mt in meter_types]
        amounts = [stats[mt]['amount'] for mt in meter_types]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        ax1.bar(meter_types, consumptions, color='steelblue', alpha=0.7)
        ax1.set_xlabel('Тип счетчика')
        ax1.set_ylabel('Расход')
        ax1.set_title('Расход по типам счетчиков')
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3, axis='y')
        
        ax2.bar(meter_types, amounts, color='coral', alpha=0.7)
        ax2.set_xlabel('Тип счетчика')
        ax2.set_ylabel('Сумма (руб.)')
        ax2.set_title('Сумма к оплате по типам счетчиков')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        return fig
    
    def create_summary_report(self, object_id: int, 
                            start_date: date, end_date: date) -> Dict:
        stats = self.calc_service.get_statistics(object_id, start_date, end_date)
        obj = self.object_repo.get_by_id(object_id)
        
        report = {
            'object': obj.address if obj else 'Неизвестно',
            'period': f"{start_date} - {end_date}",
            'statistics': stats,
            'total_amount': sum(s['amount'] for s in stats.values())
        }
        
        return report

class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.canvas = None
    
    def set_chart(self, fig):
        if self.canvas:
            self.layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
        
        self.canvas = FigureCanvas(fig)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()

