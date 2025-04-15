from django.urls import path
from . import views

urlpatterns = [
    # Employee expense management
    path('my-expenses/', views.my_expenses, name='my_expenses'),
    path('create/', views.create_expense_claim, name='create_expense_claim'),
    path('items/<int:claim_id>/', views.add_expense_items, name='add_expense_items'),
    path('view/<int:claim_id>/', views.view_expense_claim, name='view_expense_claim'),
    path('edit/<int:claim_id>/', views.edit_expense_claim, name='edit_expense_claim'),
    path('delete/<int:claim_id>/', views.delete_expense_claim, name='delete_expense_claim'),
    path('cancel/<int:claim_id>/', views.cancel_expense_claim, name='cancel_expense_claim'),
    
    # Item management
    path('item/<int:item_id>/edit/', views.edit_expense_item, name='edit_expense_item'),
    path('item/<int:item_id>/delete/', views.delete_expense_item, name='delete_expense_item'),
    
    # Manager/HR expense approval
    path('pending/', views.pending_expenses, name='pending_expenses'),
    path('approve/<int:claim_id>/', views.approve_expense, name='approve_expense'),
    
    # Payment processing
    path('payment/<int:claim_id>/', views.process_payment, name='process_payment'),
    path('processed/', views.processed_expenses, name='processed_expenses'),
    
    # Categories
    path('categories/', views.expense_category_list, name='expense_category_list'),
    path('categories/create/', views.expense_category_create, name='expense_category_create'),
    path('categories/<int:category_id>/edit/', views.expense_category_edit, name='expense_category_edit'),
    path('categories/<int:category_id>/delete/', views.expense_category_delete, name='expense_category_delete'),
    
    # Reports
    path('report/', views.expense_report, name='expense_report'),
    path('export/', views.export_expenses, name='export_expenses'),
]