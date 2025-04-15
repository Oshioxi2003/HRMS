from django.urls import path
from . import views

urlpatterns = [
    # Salary grades
    path('grades/', views.salary_grade_list, name='salary_grade_list'),
    path('grades/create/', views.salary_grade_create, name='salary_grade_create'),
    path('grades/<int:pk>/edit/', views.salary_grade_update, name='salary_grade_update'),
    path('grades/<int:pk>/delete/', views.salary_grade_delete, name='salary_grade_delete'),
    
    # Seniority allowance
    path('seniority/', views.seniority_allowance_list, name='seniority_allowance_list'),
    path('seniority/create/', views.seniority_allowance_create, name='seniority_allowance_create'),
    path('seniority/<int:pk>/edit/', views.seniority_allowance_update, name='seniority_allowance_update'),
    path('seniority/<int:pk>/delete/', views.seniority_allowance_delete, name='seniority_allowance_delete'),
    
    # Employee salary grade assignment
    path('assignments/', views.employee_salary_grade_list, name='employee_salary_grade_list'),
    path('assignments/create/', views.employee_salary_grade_create, name='employee_salary_grade_create'),
    path('assignments/<int:pk>/edit/', views.employee_salary_grade_update, name='employee_salary_grade_update'),
    path('assignments/<int:pk>/end/', views.employee_salary_grade_end, name='employee_salary_grade_end'),
    
    # Salary advances
    path('advances/', views.salary_advance_list, name='salary_advance_list'),
    path('advances/request/', views.salary_advance_request, name='salary_advance_request'),
    path('advances/<int:pk>/approve/', views.approve_salary_advance, name='approve_salary_advance'),
    path('advances/<int:pk>/reject/', views.reject_salary_advance, name='reject_salary_advance'),
    path('my-advances/', views.my_salary_advances, name='my_salary_advances'),
    
    # Salary processing
    path('admin/', views.salary_admin, name='salary_admin'),
    path('process/', views.process_monthly_salary, name='process_monthly_salary'),
    path('list/<int:year>/<int:month>/', views.salary_list, name='salary_list'),
    path('detail/<int:pk>/', views.salary_detail, name='salary_detail'),
    path('edit/<int:pk>/', views.salary_update, name='salary_update'),
    path('pay/<int:pk>/', views.mark_salary_paid, name='mark_salary_paid'),
    
    # Export
    path('export/<int:year>/<int:month>/', views.export_salary, name='export_salary'),
    
    # Employee salary view
    path('my-salary/', views.my_salary, name='my_salary'),
    path('my-salary/<int:year>/<int:month>/', views.my_salary_detail, name='my_salary_detail'),
    path('my-salary/payslip/<int:salary_id>/', views.my_salary_payslip, name='my_salary_payslip'),
]