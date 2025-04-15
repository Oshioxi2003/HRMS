# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Quản lý tài liệu
    path('', views.document_list, name='document_list'),
    path('upload/', views.document_upload, name='document_upload'),
    path('detail/<int:document_id>/', views.document_detail, name='document_detail'),
    path('edit/<int:document_id>/', views.document_edit, name='document_edit'),
    path('delete/<int:document_id>/', views.document_delete, name='document_delete'),
    path('download/<int:document_id>/', views.document_download, name='document_download'),
    
    # Danh mục
    path('categories/', views.document_category_list, name='document_category_list'),
    path('categories/create/', views.document_category_create, name='document_category_create'),
    path('categories/<int:category_id>/edit/', views.document_category_edit, name='document_category_edit'),
    path('categories/<int:category_id>/delete/', views.document_category_delete, name='document_category_delete'),
    
    # Tài liệu của tôi
    path('my-documents/', views.my_documents, name='my_documents'),
    path('department-documents/', views.department_documents, name='department_documents'),
    
    # Tìm kiếm
    path('search/', views.document_search, name='document_search'),
]
