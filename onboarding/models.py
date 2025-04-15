from django.db import models
from employee.models import Employee
from django.contrib.auth import get_user_model

User = get_user_model()

class OnboardingTask(models.Model):
    TASK_TYPE_CHOICES = (
        ('Document', 'Document Submission'),
        ('Training', 'Training'),
        ('Meeting', 'Meeting'),
        ('Account', 'Account Setup'),
        ('Equipment', 'Equipment Assignment'),
        ('Policy', 'Policy Acknowledgement'),
        ('Other', 'Other'),
    )
    
    task_id = models.AutoField(primary_key=True)
    task_name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    is_required = models.BooleanField(default=True)
    department_specific = models.BooleanField(default=False)
    department = models.ForeignKey('employee.Department', on_delete=models.CASCADE, null=True, blank=True)
    position_specific = models.BooleanField(default=False)
    position = models.ForeignKey('employee.Position', on_delete=models.CASCADE, null=True, blank=True)
    duration_days = models.IntegerField(default=7)  # Days to complete after hire
    resources = models.TextField(null=True, blank=True)  # URLs or document references
    responsible_role = models.CharField(max_length=20, choices=[
        ('HR', 'HR'),
        ('Manager', 'Manager'),
        ('IT', 'IT'),
        ('Employee', 'Employee'),
        ('Admin', 'Admin'),
    ], default='HR')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.task_name

class EmployeeOnboarding(models.Model):
    STATUS_CHOICES = (
        ('Not Started', 'Not Started'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Overdue', 'Overdue'),
    )
    
    onboarding_id = models.AutoField(primary_key=True)
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    start_date = models.DateField()
    target_completion_date = models.DateField()
    actual_completion_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Not Started')
    notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Onboarding for {self.employee.full_name}"

class EmployeeTaskStatus(models.Model):
    STATUS_CHOICES = (
        ('Not Started', 'Not Started'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Overdue', 'Overdue'),
        ('Not Applicable', 'Not Applicable'),
    )
    
    status_id = models.AutoField(primary_key=True)
    onboarding = models.ForeignKey(EmployeeOnboarding, on_delete=models.CASCADE)
    task = models.ForeignKey(OnboardingTask, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Not Started')
    completion_date = models.DateField(null=True, blank=True)
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('onboarding', 'task')
    
    def __str__(self):
        return f"{self.task.task_name} - {self.status}"
