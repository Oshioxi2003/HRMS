from django.urls import path, include
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from . import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'employees', views.EmployeeViewSet, basename='employee')
router.register(r'departments', views.DepartmentViewSet)
router.register(r'positions', views.PositionViewSet)
router.register(r'attendance', views.AttendanceViewSet, basename='attendance')
router.register(r'leave-requests', views.LeaveRequestViewSet, basename='leave-request')
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
# router.register(r'expenses', views.ExpenseClaimViewSet, basename='expense')
# router.register(r'assets', views.AssetViewSet, basename='asset')
# router.register(r'contracts', views.EmploymentContractViewSet, basename='contract')

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
    # Authentication
    path('token/', obtain_auth_token, name='api_token_auth'),
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
    
    # Mobile-specific endpoints
    # path('mobile/dashboard/', views.mobile_dashboard, name='mobile_dashboard'),
    # path('mobile/check-in/', views.mobile_check_in, name='mobile_check_in'),
    # path('mobile/check-out/', views.mobile_check_out, name='mobile_check_out'),
]