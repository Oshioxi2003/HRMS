# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.hr_reports, name='hr_reports'),
    
    # Employee reports
    path('employees/', views.employee_report, name='employee_report'),
    path('employee-turnover/', views.employee_turnover_report, name='employee_turnover_report'),
    path('headcount/', views.headcount_report, name='headcount_report'),
    
    # Payroll reports
    path('salary/', views.salary_report, name='salary_report'),
    path('payroll-summary/', views.payroll_summary_report, name='payroll_summary_report'),
    
    # Attendance reports
    path('attendance/', views.attendance_summary_report, name='attendance_summary_report'),
    path('leave-analysis/', views.leave_analysis_report, name='leave_analysis_report'),
    
    # Performance reports
    path('performance/', views.performance_analysis_report, name='performance_analysis_report'),
    path('kpi-summary/', views.kpi_summary_report, name='kpi_summary_report'),
    
    # Asset and expense reports
    path('asset-utilization/', views.asset_utilization_report, name='asset_utilization_report'),
    path('expense-analysis/', views.expense_analysis_report, name='expense_analysis_report'),
    
    # Comparison tools
    path('compare/', views.report_comparison, name='report_comparison'),
    path('compare-data/', views.comparison_data, name='comparison_data'),
    
    # Export reports
    path('export/<str:report_type>/', views.export_report, name='export_report'),
    
    # Saved reports
    path('saved/', views.saved_report_list, name='saved_report_list'),
    path('saved/<int:report_id>/', views.saved_report_detail, name='saved_report_detail'),
    path('save-current/', views.save_current_report, name='save_current_report'),
]
