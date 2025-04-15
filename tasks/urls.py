from django.urls import path
from . import views

urlpatterns = [
    # My tasks
    path('my-tasks/', views.my_tasks, name='my_tasks'),
    path('my-tasks/calendar/', views.my_tasks_calendar, name='my_tasks_calendar'),
    
    # Task management
    path('', views.task_list, name='task_list'),
    path('create/', views.create_task, name='create_task'),
    path('view/<int:task_id>/', views.view_task, name='view_task'),
    path('edit/<int:task_id>/', views.edit_task, name='edit_task'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    
    # Task status update
    path('update-status/<int:task_id>/', views.update_task_status, name='update_task_status'),
    
    # Task comments
    path('comment/<int:task_id>/', views.add_task_comment, name='add_task_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_task_comment, name='delete_task_comment'),
    
    # Task dependencies
    path('dependencies/<int:task_id>/', views.add_task_dependencies, name='add_task_dependencies'),
    
    # Department/team tasks
    path('department/', views.department_tasks, name='department_tasks'),
    path('team/', views.team_tasks, name='team_tasks'),
    
    # Task categories
    path('categories/', views.task_category_list, name='task_category_list'),
    path('categories/create/', views.task_category_create, name='task_category_create'),
    path('categories/<int:category_id>/edit/', views.task_category_edit, name='task_category_edit'),
    path('categories/<int:category_id>/delete/', views.task_category_delete, name='task_category_delete'),
    
    # Reports
    path('report/', views.task_report, name='task_report'),
    path('export/', views.export_tasks, name='export_tasks'),
]