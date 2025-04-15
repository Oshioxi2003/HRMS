from django.urls import path
from . import views

urlpatterns = [
    # Asset management
    path('', views.asset_list, name='asset_list'),
    path('create/', views.create_asset, name='create_asset'),
    path('detail/<int:asset_id>/', views.asset_detail, name='asset_detail'),
    path('edit/<int:asset_id>/', views.edit_asset, name='edit_asset'),
    path('delete/<int:asset_id>/', views.delete_asset, name='delete_asset'),
    
    # Asset assignment
    path('assign/<int:asset_id>/', views.assign_asset, name='assign_asset'),
    path('return/<int:assignment_id>/', views.return_asset, name='return_asset'),
    
    # Asset maintenance
    path('maintenance/<int:asset_id>/', views.asset_maintenance, name='asset_maintenance'),
    path('maintenance/edit/<int:maintenance_id>/', views.edit_maintenance, name='edit_maintenance'),
    path('maintenance/complete/<int:maintenance_id>/', views.complete_maintenance, name='complete_maintenance'),
    
    # Asset requests
    path('my-assets/', views.my_assets, name='my_assets'),
    path('request/', views.request_asset, name='request_asset'),
    path('requests/', views.asset_requests, name='asset_requests'),
    path('requests/<int:request_id>/', views.process_asset_request, name='process_asset_request'),
    
    # Categories
    path('categories/', views.asset_category_list, name='asset_category_list'),
    path('categories/create/', views.asset_category_create, name='asset_category_create'),
    path('categories/<int:category_id>/edit/', views.asset_category_edit, name='asset_category_edit'),
    path('categories/<int:category_id>/delete/', views.asset_category_delete, name='asset_category_delete'),
    
    # Reports
    path('report/', views.asset_report, name='asset_report'),
    path('export/', views.export_assets, name='export_assets'),
]