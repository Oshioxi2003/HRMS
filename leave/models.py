from django.db import models
from employee.models import Employee
from datetime import date, datetime


class LeaveRequest(models.Model):
    LEAVE_TYPE_CHOICES = (
        ('Annual Leave', 'Annual Leave'),
        ('Sick Leave', 'Sick Leave'),
        ('Maternity Leave', 'Maternity Leave'),
        ('Personal Leave', 'Personal Leave'),
        ('Other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
    )
    
    request_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey('employee.Employee', on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    leave_days = models.DecimalField(max_digits=3, decimal_places=1)
    reason = models.TextField(null=True, blank=True)
    attached_file = models.FileField(upload_to='leave_attachments/', null=True, blank=True)
    approved_by = models.ForeignKey('employee.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approval_date = models.DateField(null=True, blank=True)
    approval_notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type} ({self.status})"
    
    def can_cancel(self):
        """Check if leave can be cancelled"""
        return self.status == 'Pending' or (self.status == 'Approved' and self.start_date > date.today())
    
    def can_edit(self):
        """Check if leave can be edited"""
        return self.status == 'Pending'



class LeaveBalance(models.Model):
    """Model to track employee leave balances by year and type"""
    balance_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    year = models.IntegerField()
    leave_type = models.CharField(max_length=20, choices=LeaveRequest.LEAVE_TYPE_CHOICES)
    total_days = models.DecimalField(max_digits=5, decimal_places=1)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    carry_over = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'year', 'leave_type')
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type} ({self.year})"
    
    @property
    def remaining_days(self):
        return self.total_days - self.used_days
    
    @property
    def is_exhausted(self):
        return self.remaining_days <= 0

