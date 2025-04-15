from django.db import models
from employee.models import Employee

class SalaryGrade(models.Model):
    grade_id = models.AutoField(primary_key=True)
    grade_name = models.CharField(max_length=50)
    grade_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    base_salary_amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    status = models.IntegerField(default=1, help_text='1: Active, 0: Inactive')
    
    def __str__(self):
        return f"{self.grade_name} - {self.base_salary_amount}"

class SeniorityAllowance(models.Model):
    allowance_id = models.AutoField(primary_key=True)
    years_of_service = models.IntegerField(unique=True)
    allowance_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    status = models.IntegerField(default=1, help_text='1: Active, 0: Inactive')
    
    def __str__(self):
        return f"{self.years_of_service} years - {self.allowance_percentage}%"

class EmployeeSalaryGrade(models.Model):
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    )
    
    assignment_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    grade = models.ForeignKey(SalaryGrade, on_delete=models.CASCADE)
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    decision_number = models.CharField(max_length=50, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.grade.grade_name}"

class SalaryAdvance(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Repaid', 'Repaid'),
    )
    
    advance_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    advance_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reason = models.TextField(null=True, blank=True)
    deduction_month = models.IntegerField()
    deduction_year = models.IntegerField()
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='approved_advances')
    approval_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.amount}"

class Salary(models.Model):
    salary_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    month = models.IntegerField()
    year = models.IntegerField()
    work_days = models.IntegerField(default=0)
    leave_days = models.IntegerField(default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    base_salary = models.DecimalField(max_digits=15, decimal_places=2)
    allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    seniority_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    income_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    social_insurance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    health_insurance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unemployment_insurance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    advance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'month', 'year')
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.month}/{self.year}"
    
    def save(self, *args, **kwargs):
        # Calculate net salary if not provided
        if self.net_salary is None:
            self.net_salary = (
                self.base_salary 
                + self.allowance 
                + self.seniority_allowance 
                + self.bonus 
                - self.income_tax 
                - self.social_insurance 
                - self.health_insurance 
                - self.unemployment_insurance 
                - self.deductions 
                - self.advance
            )
        super().save(*args, **kwargs)