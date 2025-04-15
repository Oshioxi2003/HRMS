from django.db import models

# Create your models here.
class WorkShift(models.Model):
    shift_id = models.AutoField(primary_key=True)
    shift_name = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    salary_coefficient = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
    description = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    status = models.IntegerField(default=1, help_text='1: Active, 0: Inactive')
    
    def __str__(self):
        return self.shift_name

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('Present', 'Present'),
        ('On Leave', 'On Leave'),
        ('Absent', 'Absent'),
        ('Holiday', 'Holiday'),
        ('Business Trip', 'Business Trip'),
    )
    
    attendance_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey('employee.Employee', on_delete=models.CASCADE)
    work_date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    shift = models.ForeignKey(WorkShift, on_delete=models.SET_NULL, null=True, blank=True)
    actual_work_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Present')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'work_date')
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.work_date}"
    

class ShiftAssignment(models.Model):
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Ended', 'Ended'),
        ('Cancelled', 'Cancelled'),
    )
    
    assignment_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey('employee.Employee', on_delete=models.CASCADE)
    shift = models.ForeignKey(WorkShift, on_delete=models.CASCADE)
    assignment_date = models.DateField()
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.shift.shift_name} ({self.status})"