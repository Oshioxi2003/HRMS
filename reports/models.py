from django.db import models
from employee.models import Employee

class HRReport(models.Model):
    REPORT_TYPE_CHOICES = (
        ('Personnel Changes', 'Personnel Changes'),
        ('Performance', 'Performance'),
        ('Salary', 'Salary'),
        ('Overview', 'Overview'),
        ('Other', 'Other'),
    )
    
    report_id = models.AutoField(primary_key=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField(null=True, blank=True)
    report_period = models.DateField(null=True, blank=True)
    report_file = models.FileField(upload_to='hr_reports/', null=True, blank=True)
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class AnalyticsData(models.Model):
    data_id = models.AutoField(primary_key=True)
    metric = models.CharField(max_length=100)
    value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=20, null=True, blank=True)
    period = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.metric}: {self.value} {self.unit or ''}"