from django.db import models
from employee.models import Employee

class KPI(models.Model):
    KPI_TYPE_CHOICES = (
        ('Individual', 'Individual'),
        ('Department', 'Department'),
        ('Company', 'Company'),
    )
    
    kpi_id = models.AutoField(primary_key=True)
    kpi_name = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    min_target = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_target = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight_factor = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
    kpi_type = models.CharField(max_length=20, choices=KPI_TYPE_CHOICES, default='Individual')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.kpi_name

class EmployeeEvaluation(models.Model):
    evaluation_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE)
    month = models.IntegerField()
    year = models.IntegerField()
    result = models.DecimalField(max_digits=10, decimal_places=2)
    target = models.DecimalField(max_digits=10, decimal_places=2)
    achievement_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    evaluation_date = models.DateField()
    evaluated_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='evaluations_given')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'kpi', 'month', 'year')
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.kpi.kpi_name} ({self.month}/{self.year})"
    
    def save(self, *args, **kwargs):
        # Calculate achievement rate if not provided
        if self.achievement_rate is None and self.target > 0:
            self.achievement_rate = (self.result / self.target) * 100
        super().save(*args, **kwargs)

class RewardsAndDisciplinary(models.Model):
    TYPE_CHOICES = (
        ('Reward', 'Reward'),
        ('Disciplinary', 'Disciplinary'),
    )
    
    rad_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    content = models.TextField()
    decision_date = models.DateField()
    decision_number = models.CharField(max_length=50, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    decided_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='decisions_made')
    attached_file = models.FileField(upload_to='rewards_disciplinary/', null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.get_type_display()} ({self.decision_date})"