from django.urls import path
from . import views

urlpatterns = [
    # Employee attendance management
    path('my-attendance/', views.my_attendance, name='my_attendance'),
    path('check-in/', views.attendance_check_in, name='attendance_check_in'),
    path('check-out/', views.attendance_check_out, name='attendance_check_out'),
    
    # Work shifts
    path('shifts/', views.shift_list, name='shift_list'),
    path('shifts/create/', views.shift_create, name='shift_create'),
    path('shifts/<int:pk>/edit/', views.shift_update, name='shift_update'),
    path('shifts/<int:pk>/delete/', views.shift_delete, name='shift_delete'),
    
    # Shift assignments
    path('assignments/', views.shift_assignment_list, name='shift_assignment_list'),
    path('assignments/create/', views.shift_assignment_create, name='shift_assignment_create'),
    path('assignments/<int:pk>/edit/', views.shift_assignment_update, name='shift_assignment_update'),
    path('assignments/<int:pk>/delete/', views.shift_assignment_delete, name='shift_assignment_delete'),
    
    # Admin attendance management
    path('report/', views.attendance_report, name='attendance_report'),
    path('report/department/<int:department_id>/', views.department_attendance, name='department_attendance'),
    path('report/employee/<int:employee_id>/', views.employee_attendance, name='employee_attendance'),
    path('record/create/', views.attendance_record_create, name='attendance_record_create'),
    path('record/<int:pk>/edit/', views.attendance_record_update, name='attendance_record_update'),
    path('record/<int:pk>/delete/', views.attendance_record_delete, name='attendance_record_delete'),
    
    # Export
    path('export/', views.export_attendance, name='export_attendance'),
    
    # Calendar view
    path('calendar/', views.attendance_calendar, name='attendance_calendar'),
    path('calendar-data/', views.calendar_data, name='attendance_calendar_data'),
]
