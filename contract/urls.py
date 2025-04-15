from django.urls import path
from . import views

urlpatterns = [
    # Contract management
    path('', views.contract_list, name='contract_list'),
    path('create/', views.contract_create, name='contract_create'),
    path('<int:pk>/', views.contract_detail, name='contract_detail'),
    path('<int:pk>/edit/', views.contract_update, name='contract_update'),
    path('<int:pk>/terminate/', views.contract_terminate, name='contract_terminate'),
    path('<int:pk>/renew/', views.contract_renew, name='contract_renew'),
    
    # Employee contracts
    path('employee/<int:employee_id>/', views.employee_contracts, name='employee_contracts'),
    path('employee/<int:employee_id>/create/', views.employee_contract_create, name='employee_contract_create'),
    
    # Export
    path('export/', views.export_contracts, name='export_contracts'),
    
    # Reports
    path('expiring/', views.expiring_contracts, name='expiring_contracts'),
    path('report/', views.contract_report, name='contract_report'),
    
    # My contracts (for employees)
    path('my-contracts/', views.my_contracts, name='my_contracts'),
]