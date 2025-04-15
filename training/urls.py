# training/urls.py (extended)
from django.urls import path
from . import views

urlpatterns = [
    # Course management
    path('courses/', views.course_list, name='course_list'),
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/<int:pk>/edit/', views.course_update, name='course_update'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),
    
    # Course participants
    path('courses/<int:course_id>/participants/', views.course_participants, name='course_participants'),
    path('courses/<int:course_id>/add-participants/', views.add_participants, name='add_participants'),
    path('participation/<int:participation_id>/update/', views.update_participation_status, name='update_participation_status'),
    path('participation/<int:participation_id>/delete/', views.delete_participation, name='delete_participation'),
    
    # Employee training
    path('my-training/', views.my_training, name='my_training'),
    path('register/<int:course_id>/', views.register_for_course, name='register_for_course'),
    path('cancel-registration/<int:participation_id>/', views.cancel_registration, name='cancel_registration'),
    path('feedback/<int:participation_id>/', views.provide_feedback, name='provide_feedback'),
    
    # Admin views
    path('admin/', views.training_admin, name='training_admin'),
    path('report/', views.training_report, name='training_report'),
    path('report/employee/<int:employee_id>/', views.employee_training, name='employee_training'),
    path('report/department/<int:department_id>/', views.department_training, name='department_training'),
    
    # Export/Import
    path('export/', views.export_training, name='export_training'),
    path('import/courses/', views.import_courses, name='import_courses'),
    path('import/participants/', views.import_participants, name='import_participants'),
    
    # Calendar view
    path('calendar/', views.training_calendar, name='training_calendar'),
    path('calendar/data/', views.training_calendar_data, name='training_calendar_data'),
    
    # API endpoints
    path('api/course/<int:course_id>/participants/', views.api_course_participants, name='api_course_participants'),
    
    # Training management
    path('', views.training_list, name='training_list'),
    path('create/', views.training_create, name='training_create'),
    path('<int:pk>/', views.training_detail, name='training_detail'),
    path('<int:pk>/edit/', views.training_edit, name='training_edit'),
    path('<int:pk>/delete/', views.training_delete, name='training_delete'),
    path('participants/<int:pk>/add/', views.add_participant, name='add_participant'),
    path('participants/<int:pk>/remove/', views.remove_participant, name='remove_participant'),
]
