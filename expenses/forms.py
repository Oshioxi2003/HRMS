from django import forms
from django.core.exceptions import ValidationError
from .models import ExpenseCategory, ExpenseClaim, ExpenseItem
from datetime import date

class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class ExpenseClaimForm(forms.ModelForm):
    class Meta:
        model = ExpenseClaim
        fields = ['claim_title', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class ExpenseItemForm(forms.ModelForm):
    class Meta:
        model = ExpenseItem
        fields = ['category', 'date', 'amount', 'description', 'receipt', 'is_billable']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.TextInput(attrs={'placeholder': 'Brief description of expense'}),
        }
    
    def clean_date(self):
        expense_date = self.cleaned_data.get('date')
        if expense_date and expense_date > date.today():
            raise ValidationError("Expense date cannot be in the future.")
        return expense_date
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount

class ExpenseApprovalForm(forms.ModelForm):
    class Meta:
        model = ExpenseClaim
        fields = ['status', 'rejected_reason']
        widgets = {
            'rejected_reason': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Reason for rejection (if applicable)'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejected_reason = cleaned_data.get('rejected_reason')
        
        if status == 'Rejected' and not rejected_reason:
            self.add_error('rejected_reason', 'Please provide a reason for rejection.')
        
        return cleaned_data

class ExpensePaymentForm(forms.ModelForm):
    class Meta:
        model = ExpenseClaim
        fields = ['payment_method', 'payment_date', 'reference_number']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }
