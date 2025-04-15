from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import permission_views

urlpatterns = [
    # Authentication views
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Password management
    path('password/change/', views.change_password, name='change_password'),
    path('password/reset/', views.password_reset_request, name='password_reset'),
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'), 
        name='password_reset_done'),
    path('password/reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_confirm.html'), 
        name='password_reset_confirm'),
    
    # Account activation
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),
    
    # User profile
    path('profile/', views.my_profile, name='my_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # User management (admin)
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/activate/', views.user_activate, name='user_activate'),
    path('users/<int:user_id>/deactivate/', views.user_deactivate, name='user_deactivate'),
    
    # Permissions
    path('permissions/', permission_views.permission_list, name='permission_list'),
    path('permissions/create/', permission_views.permission_create, name='permission_create'),
    path('permissions/<int:permission_id>/edit/', views.permission_edit, name='permission_edit'),
    path('permissions/<int:permission_id>/delete/', views.permission_delete, name='permission_delete'),
    
    # System logs
    path('logs/', views.system_logs, name='system_logs'),
    
    # Approval pending
    path('approval-pending/', views.approval_pending, name='approval_pending'),
]