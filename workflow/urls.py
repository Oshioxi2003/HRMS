from django.urls import path
from . import views

urlpatterns = [
    # Employee workflow views
    path('my-workflows/', views.my_workflows, name='my_workflows'),
    path('my-approvals/', views.my_approval_requests, name='my_approval_requests'),
    
    # Workflow details
    path('view/<int:instance_id>/', views.workflow_detail, name='workflow_detail'),
    path('approve/<int:step_instance_id>/', views.approve_workflow_step, name='approve_workflow_step'),
    
    # Admin workflow definition
    path('definitions/', views.workflow_definitions, name='workflow_definitions'),
    path('definitions/create/', views.workflow_definition_create, name='workflow_definition_create'),
    path('definitions/<int:workflow_id>/', views.workflow_definition_detail, name='workflow_definition_detail'),
    path('definitions/<int:workflow_id>/edit/', views.workflow_definition_edit, name='workflow_definition_edit'),
    path('definitions/<int:workflow_id>/delete/', views.workflow_definition_delete, name='workflow_definition_delete'),
    
    # Workflow steps
    path('step/create/<int:workflow_id>/', views.workflow_step_create, name='workflow_step_create'),
    path('step/<int:step_id>/edit/', views.workflow_step_edit, name='workflow_step_edit'),
    path('step/<int:step_id>/delete/', views.workflow_step_delete, name='workflow_step_delete'),
    path('step/reorder/<int:workflow_id>/', views.workflow_step_reorder, name='workflow_step_reorder'),
    
    # Reports
    path('report/', views.workflow_report, name='workflow_report'),
]