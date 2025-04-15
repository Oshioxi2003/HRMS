from django.db import models
from employee.models import Employee

class EmploymentContract(models.Model):
    CONTRACT_TYPE_CHOICES = (
        ('Probation', 'Probation'),
        ('Fixed-term', 'Fixed-term'),
        ('Indefinite-term', 'Indefinite-term'),
        ('Seasonal', 'Seasonal'),
    )
    
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Expired', 'Expired'),
        ('Terminated', 'Terminated'),
    )
    
    contract_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=15, decimal_places=2)
    allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    attached_file = models.FileField(upload_to='contract_documents/', null=True, blank=True)
    sign_date = models.DateField(null=True, blank=True)
    signed_by = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.contract_type}"