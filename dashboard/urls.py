from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard (router)
    path('', views.dashboard, name='dashboard'),
    
    # Role-specific dashboards
    path('employee/', views.employee_dashboard, name='employee_dashboard'),
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('hr/', views.hr_dashboard, name='hr_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # Employee profile edit
    path('employee/edit-profile/', views.employee_edit_profile, name='employee_edit_profile'),
    
    # Calendar
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar-data/', views.calendar_data, name='calendar_data'),
    
    # Widgets
    # path('widgets/attendance/', views.attendance_widget, name='attendance_widget'),
    # path('widgets/leave/', views.leave_widget, name='leave_widget'),
    # path('widgets/tasks/', views.tasks_widget, name='tasks_widget'),
    # path('widgets/announcements/', views.announcements_widget, name='announcements_widget'),
    # path('widgets/birthday/', views.birthday_widget, name='birthday_widget'),
]
