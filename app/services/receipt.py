from datetime import date
from typing import Dict, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from app.database import Database
from app.models import ObjectRepository, MeterRepository, ReadingRepository
from app.services.calculations import CalculationService

class ReceiptGenerator:
    def __init__(self, db: Database):
        self.db = db
        self.object_repo = ObjectRepository(db)
        self.meter_repo = MeterRepository(db)
        self.reading_repo = ReadingRepository(db)
        self.calc_service = CalculationService(db)
    
    def generate_receipt(self, object_id: int, period_start: date, period_end: date, filename: str):
        obj = self.object_repo.get_by_id(object_id)
        if not obj:
            raise ValueError("Объект не найден")
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        story.append(Paragraph("КВИТАНЦИЯ НА ОПЛАТУ", title_style))
        story.append(Spacer(1, 12))
        
        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=10,
            leftIndent=0
        )
        
        story.append(Paragraph(f"<b>Объект:</b> {obj.address}", info_style))
        if obj.area:
            story.append(Paragraph(f"<b>Площадь:</b> {obj.area} м²", info_style))
        if obj.residents:
            story.append(Paragraph(f"<b>Жильцов:</b> {obj.residents}", info_style))
        story.append(Paragraph(f"<b>Период:</b> {period_start} - {period_end}", info_style))
        story.append(Spacer(1, 20))
        
        meters = self.meter_repo.get_by_object_id(object_id)
        stats = self.calc_service.get_statistics(object_id, period_start, period_end)
        
        if not stats:
            story.append(Paragraph("Нет данных за указанный период", info_style))
        else:
            data = [['Услуга', 'Расход', 'Тариф', 'Сумма к оплате']]
            total = 0.0
            
            for meter_type, stat_data in stats.items():
                tariff = 0.0
                for meter in meters:
                    if meter.type == meter_type:
                        tariff = meter.tariff
                        break
                
                amount = stat_data['amount']
                total += amount
                data.append([
                    meter_type,
                    f"{stat_data['consumption']:.2f}",
                    f"{tariff:.4f}",
                    f"{amount:.2f} руб."
                ])
            
            data.append(['<b>ИТОГО</b>', '', '', f"<b>{total:.2f} руб.</b>"])
            
            table = Table(data, colWidths=[80*mm, 30*mm, 30*mm, 40*mm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 12),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 30))
            story.append(Paragraph(f"<b>К оплате: {total:.2f} руб.</b>", title_style))
        
        doc.build(story)
        return filename
    
    def export_report_to_pdf(self, object_id: Optional[int], period_start: date, 
                            period_end: date, filename: str):
        objects_to_export = []
        if object_id:
            obj = self.object_repo.get_by_id(object_id)
            if obj:
                objects_to_export.append(obj)
        else:
            objects_to_export = self.object_repo.get_all()
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        story.append(Paragraph("ОТЧЕТ ПО ПОКАЗАНИЯМ СЧЕТЧИКОВ", title_style))
        story.append(Paragraph(f"Период: {period_start} - {period_end}", title_style))
        story.append(Spacer(1, 20))
        
        for obj in objects_to_export:
            story.append(Paragraph(f"<b>Объект: {obj.address}</b>", styles['Heading2']))
            story.append(Spacer(1, 10))
            
            stats = self.calc_service.get_statistics(obj.id, period_start, period_end)
            
            if not stats:
                story.append(Paragraph("Нет данных за указанный период", styles['Normal']))
                story.append(Spacer(1, 20))
                continue
            
            data = [['Услуга', 'Расход', 'Сумма', 'Показаний']]
            total = 0.0
            
            for meter_type, stat_data in stats.items():
                total += stat_data['amount']
                data.append([
                    meter_type,
                    f"{stat_data['consumption']:.2f}",
                    f"{stat_data['amount']:.2f} руб.",
                    str(stat_data['readings_count'])
                ])
            
            data.append(['<b>ИТОГО</b>', '', f"<b>{total:.2f} руб.</b>", ''])
            
            table = Table(data, colWidths=[60*mm, 40*mm, 50*mm, 30*mm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
        
        doc.build(story)
        return filename

