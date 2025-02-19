from django.urls import path
from . import views

app_name = 'documentos'  

urlpatterns = [
    path('', views.login_view, name='login'),         
     path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    # placeholders
    path('crud-empresas/', views.crud_empresas, name='crud_empresas'),
    path('crud-usuarios/', views.crud_usuarios, name='crud_usuarios'),
    path('crud-proyectos/', views.crud_proyectos, name='crud_proyectos'),
    # CRUD de usuarios
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/editar/<str:user_id>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<str:user_id>/', views.eliminar_usuario, name='eliminar_usuario'),
]