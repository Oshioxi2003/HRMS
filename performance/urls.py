from django.urls import path
from . import views

urlpatterns = [
    # KPI management
    path('kpi/', views.kpi_list, name='kpi_list'),
    path('kpi/create/', views.kpi_create, name='kpi_create'),
    path('kpi/<int:pk>/edit/', views.kpi_update, name='kpi_update'),
    path('kpi/<int:pk>/delete/', views.kpi_delete, name='kpi_delete'),
    
    # Employee evaluations
    path('evaluations/', views.performance_evaluations, name='performance_evaluations'),
    path('evaluate/<int:employee_id>/', views.evaluate_employee, name='evaluate_employee'),
    path('evaluation/<int:pk>/', views.evaluation_detail, name='evaluation_detail'),
    path('evaluation/<int:pk>/edit/', views.evaluation_update, name='evaluation_update'),
    path('employee/<int:employee_id>/evaluations/', views.employee_evaluations, name='employee_evaluations'),
    
    # Self evaluation
    path('my-performance/', views.my_performance, name='my_performance'),
    path('my-performance/self-evaluate/', views.self_evaluation, name='self_evaluation'),
    
    # Team performance (for managers)
    path('team/', views.team_performance, name='team_performance'),
    
    # Rewards and disciplinary
    path('rewards-disciplinary/', views.rewards_disciplinary_list, name='rewards_disciplinary_list'),
    path('rewards-disciplinary/create/', views.rewards_disciplinary_create, name='rewards_disciplinary_create'),
    path('rewards-disciplinary/<int:pk>/', views.rewards_disciplinary_detail, name='rewards_disciplinary_detail'),
    path('rewards-disciplinary/<int:pk>/edit/', views.rewards_disciplinary_update, name='rewards_disciplinary_update'),
    path('rewards-disciplinary/<int:pk>/delete/', views.rewards_disciplinary_delete, name='rewards_disciplinary_delete'),
    path('my-rewards-disciplinary/', views.my_rewards_disciplinary, name='my_rewards_disciplinary'),
    
    # Reports
    path('report/', views.performance_report, name='performance_report'),
    path('report/department/<int:department_id>/', views.department_performance, name='department_performance'),
    path('export/', views.export_performance, name='export_performance'),
]