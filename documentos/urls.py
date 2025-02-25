from django.urls import path
from . import views

app_name = 'documentos'  

urlpatterns = [
    path('', views.login_view, name='login'),         
     path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    # placeholders
    path('crud-usuarios/', views.crud_usuarios, name='crud_usuarios'),
    path('crud-proyectos/', views.crud_proyectos, name='crud_proyectos'),
    # CRUD de usuarios
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/editar/<str:user_id>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<str:user_id>/', views.eliminar_usuario, name='eliminar_usuario'),
    #CRUD de Empresa
    path('empresas/', views.crud_empresas, name="crud_empresas"),
    path('empresas/crear/', views.crear_empresa, name="crear_empresa"),
    path('empresas/editar/<str:empresa_id>/', views.editar_empresa, name="editar_empresa"),
    path('empresas/eliminar/<str:empresa_id>/', views.eliminar_empresa, name="eliminar_empresa"),
]