from django.db import models
from django.contrib.auth import get_user_model
from employee.models import Employee, Department

User = get_user_model()

class ExpenseCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Expense Categories"

class ExpenseClaim(models.Model):
    STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Submitted', 'Submitted'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Paid', 'Paid'),
        ('Cancelled', 'Cancelled'),
    )
    
    claim_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    claim_title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    submission_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    approval_date = models.DateField(null=True, blank=True)
    rejected_reason = models.TextField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    reference_number = models.CharField(max_length=100, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.claim_title}"
    
    def calculate_total(self):
        """Calculate total from expense items"""
        total = self.expenseitem_set.aggregate(models.Sum('amount'))['amount__sum'] or 0
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total

class ExpenseItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    expense_claim = models.ForeignKey(ExpenseClaim, on_delete=models.CASCADE)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=200)
    receipt = models.FileField(upload_to='expense_receipts/', null=True, blank=True)
    is_billable = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.expense_claim.claim_id} - {self.description}"
    
    def save(self, *args, **kwargs):
        """Update parent claim total amount when item is saved/updated"""
        super().save(*args, **kwargs)
        self.expense_claim.calculate_total()