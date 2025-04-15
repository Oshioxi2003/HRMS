from django.http import HttpResponse
import csv
import xlsxwriter
from io import BytesIO
from datetime import datetime

class ExportHelper:
    """Helper class for data export functions"""
    
    @staticmethod
    def export_as_csv(queryset, fields, file_name):
        """Export queryset as CSV file"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{file_name}.csv"'
        
        writer = csv.writer(response)
        # Write headers
        headers = [field['display'] for field in fields]
        writer.writerow(headers)
        
        # Write data rows
        for obj in queryset:
            row = []
            for field in fields:
                field_name = field['field']
                # Handle nested attributes
                if '.' in field_name:
                    parts = field_name.split('.')
                    value = obj
                    for part in parts:
                        if value is None:
                            break
                        value = getattr(value, part, None)
                else:
                    value = getattr(obj, field_name, None)
                
                # Format date fields
                if isinstance(value, datetime.date):
                    value = value.strftime('%Y-%m-%d')
                
                row.append(value if value is not None else '')
            writer.writerow(row)
        
        return response
    
    @staticmethod
    def export_as_excel(queryset, fields, file_name):
        """Export queryset as Excel file"""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()
        
        # Add headers
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3f51b5',
            'color': 'white',
            'border': 1
        })
        
        for col_num, field in enumerate(fields):
            worksheet.write(0, col_num, field['display'], header_format)
        
        # Add data rows
        for row_num, obj in enumerate(queryset, 1):
            for col_num, field in enumerate(fields):
                field_name = field['field']
                # Handle nested attributes
                if '.' in field_name:
                    parts = field_name.split('.')
                    value = obj
                    for part in parts:
                        if value is None:
                            break
                        value = getattr(value, part, None)
                else:
                    value = getattr(obj, field_name, None)
                
                # Format date fields
                if isinstance(value, datetime.date):
                    value = value.strftime('%Y-%m-%d')
                
                worksheet.write(row_num, col_num, value if value is not None else '')
        
        # Auto-adjust column widths
        for col_num, field in enumerate(fields):
            worksheet.set_column(col_num, col_num, len(field['display']) + 5)
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{file_name}.xlsx"'
        
        return response