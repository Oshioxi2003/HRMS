from django.urls import path
from . import views

urlpatterns = [
    # Onboarding management
    path('', views.onboarding_list, name='onboarding_list'),
    path('create/<int:employee_id>/', views.create_employee_onboarding, name='create_employee_onboarding'),
    path('<int:employee_id>/detail/', views.employee_onboarding_detail, name='employee_onboarding_detail'),
    
    # Task management
    path('tasks/', views.onboarding_task_list, name='onboarding_task_list'),
    path('tasks/create/', views.onboarding_task_create, name='onboarding_task_create'),
    path('tasks/<int:task_id>/edit/', views.onboarding_task_edit, name='onboarding_task_edit'),
    path('tasks/<int:task_id>/delete/', views.onboarding_task_delete, name='onboarding_task_delete'),
    
    # Task status update
    path('update-task/<int:task_status_id>/', views.update_task_status, name='update_onboarding_task_status'),
    
    # Employee view
    path('my-onboarding/', views.my_onboarding, name='my_onboarding'),
    
    # Manager tasks
    path('<int:employee_id>/manager-tasks/', views.manager_onboarding_tasks, name='manager_onboarding_tasks'),
]