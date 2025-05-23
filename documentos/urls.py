from django.urls import path
from . import views
from .views import limpiar_notificaciones

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
    path('proyectos/', views.crud_proyectos, name='crud_proyectos'),
    path('proyectos/crear/', views.crear_proyecto, name='crear_proyecto'),
    path('proyectos/editar/<str:proyecto_id>/', views.editar_proyecto, name='editar_proyecto'),
    path('proyectos/eliminar/<str:proyecto_id>/', views.eliminar_proyecto, name='eliminar_proyecto'),
    path('postulaciones/mis/', views.mis_postulaciones, name='mis_postulaciones'),
    path('postulaciones/crear/<str:proyecto_id>/', views.crear_postulacion, name='crear_postulacion'),
    path('postulaciones/cancelar/<str:postulacion_id>/', views.cancelar_postulacion, name='cancelar_postulacion'),
    path('postulaciones/', views.listar_postulaciones, name='crud_postulaciones'),
    path('postulaciones/editar/<str:postulacion_id>/', views.actualizar_postulacion, name='actualizar_postulacion'),
    path('proyectos/catalogo/', views.catalogo_proyectos, name='catalogo_proyectos'),
    path('postulaciones/generar_carta_local/<str:postulacion_id>/', views.generar_carta_local, name='generar_carta_local'),
    path("limpiar_notificaciones/", limpiar_notificaciones, name="limpiar_notificaciones"),
    path("seguimientos/", views.listar_seguimientos, name="crud_seguimientos"),
    path("seguimientos/crear/", views.crear_seguimiento, name="crear_seguimiento"),
    path("seguimientos/editar/<str:seguimiento_id>/", views.editar_seguimiento, name="editar_seguimiento"),
    path("seguimientos/eliminar/<str:seguimiento_id>/", views.eliminar_seguimiento, name="eliminar_seguimiento"),
    path("mis_seguimientos/", views.dashboard_seguimientos_alumno, name="mis_seguimientos"),
    path("dashboard_seguimientos/", views.dashboard_seguimientos, name="dashboard_seguimientos"),
    path("mis_finalizaciones/", views.mis_finalizaciones, name="mis_finalizaciones"),
    path("logs/", views.ver_logs, name="ver_logs"),
    path('api/usuarios/actualizar_matricula/', views.actualizar_matricula_api, name='actualizar_matricula_api'),
]

