from django.urls import path
from . import views

urlpatterns = [
    # Organization chart
    path('chart/', views.organization_chart, name='organization_chart'),
    
    # Department structure
    path('structure/', views.organization_structure, name='organization_structure'),
    path('structure/edit/', views.edit_organization_structure, name='edit_organization_structure'),
    
    # Department details
    path('department/<int:department_id>/', views.department_detail, name='org_department_detail'),
    path('department/<int:department_id>/members/', views.department_members, name='department_members'),
    
    # Team management (for managers)
    path('my-team/', views.my_team, name='my_team'),
    path('my-team/structure/', views.my_team_structure, name='my_team_structure'),
]
