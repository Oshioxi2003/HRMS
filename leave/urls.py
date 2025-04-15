from django.urls import path
from . import views

urlpatterns = [
    # Employee leave management
    path('my-leaves/', views.my_leave_requests, name='my_leave_requests'),
    path('request/', views.leave_request_create, name='leave_request_create'),
    path('request/<int:pk>/', views.leave_request_detail, name='leave_request_detail'),
    path('request/<int:pk>/edit/', views.leave_request_update, name='leave_request_update'),
    path('request/<int:pk>/cancel/', views.leave_request_cancel, name='leave_request_cancel'),
    
    # Manager leave approval
    path('pending-approvals/', views.pending_leave_requests, name='pending_leave_requests'),
    path('approve/<int:pk>/', views.leave_approval, name='leave_approval'),
    
    # HR leave management
    path('all/', views.all_leave_requests, name='all_leave_requests'),
    path('report/', views.leave_report, name='leave_report'),
    path('report/department/<int:department_id>/', views.department_leave_report, name='department_leave_report'),
    path('report/employee/<int:employee_id>/', views.employee_leave_report, name='employee_leave_report'),
    
    # Export
    path('export/', views.export_leave_requests, name='export_leave_requests'),
    
    # Leave balance view
    path('balance/', views.my_leave_balance, name='my_leave_balance'),
    path('balance/<int:employee_id>/', views.employee_leave_balance, name='employee_leave_balance'),
]