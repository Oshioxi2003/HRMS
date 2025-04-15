from django.urls import path
from . import views

urlpatterns = [
    path('', views.search, name='search'),
    path('advanced/', views.advanced_search, name='advanced_search'),
    path('global/', views.global_search, name='global_search'),
    path('employees/', views.employee_search, name='employee_search'),
    path('documents/', views.document_search, name='document_search'),
]