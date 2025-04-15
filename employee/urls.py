from django.urls import path
from . import views
from . import document_views

urlpatterns = [
    # Employee list and CRUD
    path('employee/', views.employee_list, name='employee_list'),
    path('create/', views.employee_create, name='employee_create'),
    path('<int:pk>/', views.employee_detail, name='employee_detail'),
    path('<int:pk>/edit/', views.employee_update, name='employee_update'),
    path('<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    
    # Import/Export
    path('export/', views.export_employees, name='export_employees'),
    path('import/', views.import_employees, name='import_employees'),
    path('import/errors/', views.import_errors, name='import_errors'),
    
    # Department management
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/', views.department_detail, name='department_detail'),
    path('departments/<int:pk>/edit/', views.department_update, name='department_update'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    
    # Position management
    path('positions/', views.position_list, name='position_list'),
    path('positions/create/', views.position_create, name='position_create'),
    path('positions/<int:pk>/edit/', views.position_update, name='position_update'),
    path('positions/<int:pk>/delete/', views.position_delete, name='position_delete'),
    
    # Education level management
    path('education/', views.education_list, name='education_list'),
    path('education/create/', views.education_create, name='education_create'),
    path('education/<int:pk>/edit/', views.education_update, name='education_update'),
    path('education/<int:pk>/delete/', views.education_delete, name='education_delete'),
    
    # Academic title management
    path('titles/', views.title_list, name='title_list'),
    path('titles/create/', views.title_create, name='title_create'),
    path('titles/<int:pk>/edit/', views.title_update, name='title_update'),
    path('titles/<int:pk>/delete/', views.title_delete, name='title_delete'),
    
    # Employee location
    path('<int:employee_id>/location/', views.employee_location, name='employee_location'),
    path('<int:employee_id>/location/edit/', views.employee_location_update, name='employee_location_update'),
    
    # Insurance and tax
    path('<int:employee_id>/insurance/', views.insurance_tax_detail, name='insurance_tax_detail'),
    path('<int:employee_id>/insurance/create/', views.insurance_tax_create, name='insurance_tax_create'),
    path('<int:employee_id>/insurance/edit/', views.insurance_tax_update, name='insurance_tax_update'),
    
    # Employee certificates
    path('<int:employee_id>/certificates/', views.employee_certificates, name='employee_certificates'),
    path('<int:employee_id>/certificates/add/', views.add_certificate, name='add_employee_certificate'),
    path('certificates/<int:certificate_id>/edit/', views.edit_certificate, name='edit_certificate'),
    path('certificates/<int:certificate_id>/delete/', views.delete_certificate, name='delete_certificate'),
    
    # Certificate types
    path('certificate-types/', views.certificate_type_list, name='certificate_type_list'),
    path('certificate-types/create/', views.certificate_type_create, name='certificate_type_create'),
    path('certificate-types/<int:pk>/edit/', views.certificate_type_update, name='certificate_type_update'),
    path('certificate-types/<int:pk>/delete/', views.certificate_type_delete, name='certificate_type_delete'),
    
    # My certificates (for employees)
    path('my-certificates/', views.my_certificates, name='my_certificates'),
    path('my-certificates/add/', views.add_my_certificate, name='add_my_certificate'),
    
    # Employee approval workflow
    path('<int:pk>/approve/', views.employee_approve, name='employee_approve'),
    path('pending-approval/', views.pending_approval_list, name='pending_approval_list'),
    
    # Document management
    path('<int:employee_id>/documents/', document_views.employee_documents, name='employee_documents'),
    path('<int:employee_id>/documents/upload/', document_views.upload_document, name='upload_document'),
    path('documents/<int:document_id>/view/', document_views.view_document, name='view_document'),
    path('documents/<int:document_id>/delete/', document_views.delete_document, name='delete_document'),
]