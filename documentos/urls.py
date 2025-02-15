from django.urls import path
from . import views

app_name = 'documentos'  # Para usar el namespace 'documentos:login' etc

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
]