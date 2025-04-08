from django.shortcuts import render, redirect
from django.contrib import messages
from .firebase import obtener_usuario_por_correo,db,firebase
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from datetime import datetime
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.core.files import File
from django.core.files.storage import default_storage
from django.conf import settings
from .utils import generar_pdf_xhtml2pdf, subir_pdf_a_storage
import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# restringe accesoS
def admin_o_empresa_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get('rol') not in ['Admin', 'Empresa', 'Empresario']:
            return redirect('documentos:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get('rol') != 'Admin':
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect('documentos:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

def no_alumno_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get('rol') == 'Alumno':
            return redirect('documentos:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

def alumno_required(view_func):
    """Decorador que restringe el acceso a usuarios con rol Alumno."""
    def wrapper(request, *args, **kwargs):
        if request.session.get('rol') != 'Alumno':
            return redirect('documentos:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

def login_view(request):
    if request.method == "POST":
        correo = request.POST.get('correo')
        contraseña = request.POST.get('contraseña')
        
        uid, user_data = obtener_usuario_por_correo(correo)

        if user_data and user_data.get("contraseña") == contraseña:
            request.session['correo'] = correo
            request.session['rol'] = user_data.get("rol", "Docente")
            messages.success(request, "Inicio de sesión exitoso.")
            return redirect('documentos:dashboard')
        else:
            messages.error(request, "Correo o contraseña incorrectos.")
    return render(request, 'login.html')

def empresario_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get('rol') not in ['Admin', 'Empresa', 'Empresario']:
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect('documentos:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

def dashboard(request):
    if 'correo' not in request.session:
        messages.error(request, "Debes iniciar sesión.")
        return redirect('documentos:login')

    usuarios = db.child("Usuarios").get().val()  
    # Obtener notificaciones
    notificaciones_data = db.child("Notificaciones").get().val() or {}
    notificaciones = []
    for key, notif in notificaciones_data.items():
        # Filtrar las notificaciones por el rol del usuario actual
        if notif.get("rol") == request.session.get("rol"):
            notif["id"] = key
            notificaciones.append(notif)
    
    return render(request, 'dashboard.html', {
        "usuarios": usuarios,
        "usuario_actual": request.session.get("correo"),
        "rol_actual": request.session.get("rol"),
        "notificaciones": notificaciones
    })


def logout_view(request):
    request.session.flush()
    messages.info(request, "Sesión cerrada.")
    return redirect('documentos:login')

@no_alumno_required
def crud_empresas(request):
    empresas = db.child("Empresas").get().val() or {}
    lista_empresas = []
    rol = request.session.get('rol')
    correo_usuario = request.session.get('correo')
    
    if empresas:
        for key, empresa in empresas.items():
            empresa['id'] = key
            # Se asegura que se muestre un número de teléfono (o valor por defecto)
            empresa['telefono'] = empresa.get('telefono') or empresa.get('contacto', 'No disponible')
            # Si el usuario es Empresario o Empresa, solo se incluye la empresa cuyo correo coincida
            if rol in ['Empresa', 'Empresario']:
                if empresa.get("correo") == correo_usuario:
                    lista_empresas.append(empresa)
            else:
                lista_empresas.append(empresa)
    
    return render(request, 'crud_empresas.html', {'empresas': lista_empresas})

@no_alumno_required
def crud_proyectos(request):
    if 'correo' not in request.session:
        messages.error(request, "Debes iniciar sesión.")
        return redirect('documentos:login')

    rol = request.session.get('rol')
    correo_usuario = request.session.get('correo')

    # Obtiene todos los proyectos
    proyectos_data = db.child("Proyectos").get().val() or {}
    proyectos_list = []
    for key, val in proyectos_data.items():
        val['id'] = key
        # Obtiene los datos de la empresa asociada
        empresa_data = db.child("Empresas").child(val.get("empresa_id")).get().val()
        if empresa_data:
            val['empresa_nombre'] = empresa_data.get('nombre', 'Sin Nombre')
        else:
            val['empresa_nombre'] = "Sin Empresa"
        if "estado" not in val:
            val["estado"] = "Abierto"
        proyectos_list.append(val)

    # Si el usuario es Empresa o Empresario, filtra solo los proyectos de su empresa
    if rol in ['Empresa', 'Empresario']:
        empresa_data = db.child("Empresas").order_by_child("correo").equal_to(correo_usuario).get().val() or {}
        if empresa_data:
            empresa_id = list(empresa_data.keys())[0]
            proyectos_list = [p for p in proyectos_list if p.get("empresa_id") == empresa_id]
        else:
            proyectos_list = []  # Si no tiene empresa asociada, no se muestra nada

    paginator = Paginator(proyectos_list, 10)
    page = request.GET.get('page')
    proyectos = paginator.get_page(page)

    # Solo para Admin se cargan todas las empresas (para filtros, etc.)
    empresas = []
    if rol == 'Admin':
        empresas_data = db.child("Empresas").get().val() or {}
        for key, val in empresas_data.items():
            empresas.append({'id': key, 'nombre': val.get('nombre', 'Sin Nombre')})
    
    context = {
        'proyectos': proyectos,
        'empresas': empresas,
    }
    return render(request, 'crud_proyectos.html', context)

@admin_required
def crud_usuarios(request):
    usuarios = db.child("Usuarios").get().val() or {}
    lista_usuarios = []
    for key, user in usuarios.items():
        user['id'] = key
        lista_usuarios.append(user)
    return render(request, 'crud_usuarios.html', {'usuarios': lista_usuarios})

@admin_required
def crear_usuario(request):
    if request.method == "POST":
        correo = request.POST.get('correo', '').strip()
        contraseña = request.POST.get('contraseña', '').strip()
        rol = request.POST.get('rol', '')
        creditos = request.POST.get('creditos', '').strip()
        semestre = request.POST.get('semestre', '').strip()
        
        matricula = request.POST.get('matricula', '').strip()
        telefono = request.POST.get('telefono', '').strip()

        # Verifica si el correo ya existe
        usuarios = db.child("Usuarios").get().val() or {}
        for key, data in usuarios.items():
            if data.get("correo") == correo:
                messages.error(request, "El usuario ya está en uso.")
                return redirect('documentos:crear_usuario')

        # Si el rol es Alumno, verifica que cumpla con los requisitos minimos y que matricula y teléfono estén informados
        if rol == "Alumno":
            c = int(creditos) if creditos else 0
            s = int(semestre) if semestre else 0
            if c < 180 or s < 7 or not matricula or not telefono:
                messages.error(request, "No cumples con los requisitos para presentar estadía.")
                return redirect('documentos:crear_usuario')

        datos = {
            "correo": correo,
            "contraseña": contraseña,
            "rol": rol
        }
        if rol == "Alumno":
            datos["creditos"] = int(creditos) if creditos else 0
            datos["semestre"] = int(semestre) if semestre else 0
            datos["matricula"] = matricula
            datos["telefono"] = telefono

        db.child("Usuarios").push(datos)
        log_event("Creación de usuario", request.session.get("correo"), f"Usuario {correo} creado con rol {rol}")
        messages.success(request, "Usuario creado exitosamente.")
        return redirect('documentos:crud_usuarios')

    return render(request, 'crear_usuario.html')

@admin_required
def editar_usuario(request, user_id):
    usuario_data = db.child("Usuarios").child(user_id).get().val()
    if not usuario_data:
        messages.error(request, "Usuario no encontrado.")
        return redirect('documentos:crud_usuarios')

    if request.method == "POST":
        correo = request.POST.get('correo', '').strip()
        rol = request.POST.get('rol', '')
        nueva_contraseña = request.POST.get('contraseña', '').strip()
        creditos = request.POST.get('creditos', '').strip()
        semestre = request.POST.get('semestre', '').strip()
        matricula = request.POST.get('matricula', '').strip()
        telefono = request.POST.get('telefono', '').strip()

        # Verificar si se cambio el correo a uno ya existente en otro usuario
        usuarios = db.child("Usuarios").get().val() or {}
        for key, data in usuarios.items():
            if key != user_id and data.get("correo") == correo:
                messages.error(request, "El usuario ya está en uso.")
                return redirect('documentos:editar_usuario', user_id=user_id)

        if rol == "Alumno":
            c = int(creditos) if creditos else 0
            s = int(semestre) if semestre else 0
            if c < 180 or s < 7 or not matricula or not telefono:
                messages.error(request, "No cumples con los requisitos para presentar estadía.")
                return redirect('documentos:editar_usuario', user_id=user_id)

        updates = {
            "correo": correo,
            "rol": rol
        }
        if nueva_contraseña:
            updates["contraseña"] = nueva_contraseña
        if rol == "Alumno":
            updates["creditos"] = int(creditos) if creditos else 0
            updates["semestre"] = int(semestre) if semestre else 0
            updates["matricula"] = matricula
            updates["telefono"] = telefono
        else:
            updates["creditos"] = None
            updates["semestre"] = None
            updates["matricula"] = None
            updates["telefono"] = None

        db.child("Usuarios").child(user_id).update(updates)
        log_event("Edición de usuario", request.session.get("correo"), f"Usuario {user_id} actualizado")
        messages.success(request, "Usuario actualizado exitosamente.")
        return redirect('documentos:crud_usuarios')

    return render(request, 'editar_usuario.html', {
        "usuario": usuario_data,
        "user_id": user_id
    })




@admin_required
def eliminar_usuario(request, user_id):
    db.child("Usuarios").child(user_id).remove()
    log_event("Eliminación de usuario", request.session.get("correo"), f"Usuario {user_id} eliminado")
    messages.success(request, "Usuario eliminado.")
    return redirect('documentos:crud_usuarios')


def crear_empresa(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre").strip()
        rfc = request.POST.get("rfc").strip().upper()
        correo = request.POST.get("correo").strip()
        telefono = request.POST.get("telefono").strip()

        # Validaciones
        if not nombre or not rfc or not correo or not telefono:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect("documentos:crear_empresa")

        if len(rfc) != 13:
            messages.error(request, "El RFC debe tener exactamente 13 caracteres.")
            return redirect("documentos:crear_empresa")

        if db.child("Empresas").order_by_child("rfc").equal_to(rfc).get().val():
            messages.error(request, "El RFC ya está registrado.")
            return redirect("documentos:crear_empresa")

        if db.child("Empresas").order_by_child("correo").equal_to(correo).get().val():
            messages.error(request, "El correo ya está registrado.")
            return redirect("documentos:crear_empresa")

        if not telefono.isdigit() or len(telefono) != 10:
            messages.error(request, "El teléfono debe contener 10 dígitos numéricos.")
            return redirect("documentos:crear_empresa")

        
        nueva_empresa = {
            "nombre": nombre,
            "rfc": rfc,
            "correo": correo,
            "telefono": telefono
        }

        db.child("Empresas").push(nueva_empresa)
        log_event("Creación de empresa", request.session.get("correo"), f"Empresa {nombre} creada")
        messages.success(request, "Empresa creada exitosamente.")
        return redirect("documentos:crud_empresas")


    return render(request, "crear_empresa.html")


def editar_empresa(request, empresa_id):
    if request.method == "POST":
        nombre = request.POST.get("nombre").strip()
        rfc = request.POST.get("rfc").strip()
        correo = request.POST.get("correo").strip()
        telefono = request.POST.get("telefono").strip()

        if not (nombre and rfc and correo and telefono):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect("documentos:editar_empresa", empresa_id=empresa_id)

        empresa_ref = db.child("Empresas").child(empresa_id)

        try:
            
            empresa_ref.update({
                "nombre": nombre,
                "rfc": rfc,
                "correo": correo,
                "telefono": telefono
            })
            log_event("Edición de empresa", request.session.get("correo"), f"Empresa {empresa_id} actualizada")
            messages.success(request, "Empresa actualizada correctamente.")
        except Exception as e:
            messages.error(request, f"Error al actualizar empresa: {str(e)}")

        return redirect("documentos:crud_empresas")

    else:
        empresa_data = db.child("Empresas").child(empresa_id).get().val()
        if not empresa_data:
            messages.error(request, "Empresa no encontrada.")
            return redirect("documentos:crud_empresas")

        return render(request, "editar_empresa.html", {"empresa": empresa_data, "empresa_id": empresa_id})
    


def eliminar_empresa(request, empresa_id):
    db.child("Empresas").child(empresa_id).remove()
    log_event("Eliminación de empresa", request.session.get("correo"), f"Empresa {empresa_id} eliminada")
    messages.success(request, "Empresa eliminada correctamente.")
    return redirect('documentos:crud_empresas')


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get('rol') != 'Admin':
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect('documentos:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

@no_alumno_required
def crud_proyectos(request):
    if 'correo' not in request.session:
        messages.error(request, "Debes iniciar sesión.")
        return redirect('documentos:login')
    
    rol = request.session.get('rol')
    correo_usuario = request.session.get('correo')
    
    
    proyectos_data = db.child("Proyectos").get().val() or {}
    proyectos_list = []
    for key, val in proyectos_data.items():
        val['id'] = key
        
        empresa_data = db.child("Empresas").child(val.get("empresa_id")).get().val()
        if empresa_data:
            val['empresa_nombre'] = empresa_data.get('nombre', 'Sin Nombre')
        else:
            val['empresa_nombre'] = "Sin Empresa"
        
        if "estado" not in val:
            val["estado"] = "Abierto"
        proyectos_list.append(val)
    
    
    if rol in ['Empresa', 'Empresario']:
        empresa_data = db.child("Empresas").order_by_child("correo").equal_to(correo_usuario).get().val()
        if empresa_data:
            empresa_id = list(empresa_data.keys())[0]
            proyectos_list = [p for p in proyectos_list if p.get("empresa_id") == empresa_id]
        else:
            messages.warning(request, "No se encontró la empresa asociada a tu usuario.")
    
    # Paginador
    paginator = Paginator(proyectos_list, 10)
    page = request.GET.get('page')
    proyectos = paginator.get_page(page)
    
    
    empresas = []
    if rol == 'Admin':
        empresas_data = db.child("Empresas").get().val() or {}
        for key, val in empresas_data.items():
            empresas.append({'id': key, 'nombre': val.get('nombre', 'Sin Nombre')})
    
    context = {
        'proyectos': proyectos,
        'empresas': empresas,
    }
    return render(request, 'crud_proyectos.html', context)


@empresario_required
def crear_proyecto(request):
    if request.method == "POST":
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        requisitos = request.POST.get('requisitos', '').strip()
        vacantes = request.POST.get('vacantes', '').strip()
        fecha_inicio = request.POST.get('fecha_inicio', '').strip()
        fecha_fin = request.POST.get('fecha_fin', '').strip()
        empresa_id = request.POST.get('empresa_id', '').strip()
        rol = request.session.get('rol')
        
        # Validaciones 
        if not (titulo and descripcion and requisitos and vacantes and fecha_inicio and fecha_fin):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('documentos:crear_proyecto')
        try:
            vacantes_num = int(vacantes)
            if vacantes_num < 1:
                messages.error(request, "El número de vacantes debe ser mayor a 0.")
                return redirect('documentos:crear_proyecto')
        except ValueError:
            messages.error(request, "Vacantes debe ser un número válido.")
            return redirect('documentos:crear_proyecto')
        try:
            inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
            if fin_dt < inicio_dt:
                messages.error(request, "La fecha de fin no puede ser anterior a la de inicio.")
                return redirect('documentos:crear_proyecto')
        except ValueError:
            messages.error(request, "Formato de fecha inválido.")
            return redirect('documentos:crear_proyecto')
        if len(requisitos) < 10:
            messages.error(request, "Debes ingresar al menos uno o dos requisitos.")
            return redirect('documentos:crear_proyecto')
        
        # Para usuarios de tipo Empresa o Empresario, asigna la empresa automaticamente basicamente
        if rol in ['Empresa', 'Empresario']:
            empresa_data = db.child("Empresas").order_by_child("correo").equal_to(request.session.get('correo')).get().val()
            if empresa_data:
                empresa_id = list(empresa_data.keys())[0]
            else:
                messages.error(request, "No se encontró tu empresa asociada.")
                return redirect('documentos:crear_proyecto')
        
        nuevo_proyecto = {
            "titulo": titulo,
            "descripcion": descripcion,
            "requisitos": requisitos,
            "vacantes": vacantes_num,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "empresa_id": empresa_id,
            "estado": "Abierto"
        }
        db.child("Proyectos").push(nuevo_proyecto)
        log_event("Creación de proyecto", request.session.get("correo"), f"Proyecto '{titulo}' creado")
        messages.success(request, "Proyecto creado exitosamente.")
        return redirect('documentos:crud_proyectos')
    else:
        context = {}
        if request.session.get('rol') == 'Admin':
            empresas_data = db.child("Empresas").get().val() or {}
            empresas = []
            for key, val in empresas_data.items():
                empresas.append({'id': key, 'nombre': val.get('nombre', 'Sin Nombre')})
            context['empresas'] = empresas
        else:
            # Para usuarios de tipo Empresa o Empresario, se obtiene la empresa asociada
            empresa_data = db.child("Empresas").order_by_child("correo").equal_to(request.session.get('correo')).get().val()
            if empresa_data:
                empresa_actual = {'id': list(empresa_data.keys())[0]}
                context['empresa_actual'] = empresa_actual
        return render(request, 'crear_proyecto.html', context)


@empresario_required
def editar_proyecto(request, proyecto_id):
    rol = request.session.get('rol')
    proyecto_data = db.child("Proyectos").child(proyecto_id).get().val()
    if not proyecto_data:
        messages.error(request, "Proyecto no encontrado.")
        return redirect('documentos:crud_proyectos')
    # Para usuarios de tipo Empresa o Empresario, verificar que el proyecto pertenezca a su empresa
    if rol in ['Empresa', 'Empresario']:
        empresa_data = db.child("Empresas").order_by_child("correo").equal_to(request.session.get('correo')).get().val()
        if empresa_data:
            empresa_id = list(empresa_data.keys())[0]
            if proyecto_data.get("empresa_id") != empresa_id:
                messages.error(request, "No puedes editar proyectos de otra empresa.")
                return redirect('documentos:crud_proyectos')
        else:
            messages.error(request, "No se encontró tu empresa asociada.")
            return redirect('documentos:crud_proyectos')
    if request.method == "POST":
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        requisitos = request.POST.get('requisitos', '').strip()
        vacantes = request.POST.get('vacantes', '').strip()
        fecha_inicio = request.POST.get('fecha_inicio', '').strip()
        fecha_fin = request.POST.get('fecha_fin', '').strip()
        empresa_id = request.POST.get('empresa_id', '').strip()
        
        if not (titulo and descripcion and requisitos and vacantes and fecha_inicio and fecha_fin):
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect(reverse('documentos:editar_proyecto', args=[proyecto_id]))
        try:
            vacantes_num = int(vacantes)
            if vacantes_num < 1:
                messages.error(request, "El número de vacantes debe ser mayor a 0.")
                return redirect(reverse('documentos:editar_proyecto', args=[proyecto_id]))
        except ValueError:
            messages.error(request, "Vacantes debe ser un número válido.")
            return redirect(reverse('documentos:editar_proyecto', args=[proyecto_id]))
        try:
            inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
            if fin_dt < inicio_dt:
                messages.error(request, "La fecha de fin no puede ser anterior a la de inicio.")
                return redirect(reverse('documentos:editar_proyecto', args=[proyecto_id]))
        except ValueError:
            messages.error(request, "Formato de fecha inválido.")
            return redirect(reverse('documentos:editar_proyecto', args=[proyecto_id]))
        if len(requisitos) < 10:
            messages.error(request, "Debes ingresar al menos uno o dos requisitos.")
            return redirect(reverse('documentos:editar_proyecto', args=[proyecto_id]))
        
        updates = {
            "titulo": titulo,
            "descripcion": descripcion,
            "requisitos": requisitos,
            "vacantes": vacantes_num,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "empresa_id": empresa_id,
        }
        db.child("Proyectos").child(proyecto_id).update(updates)
        log_event("Edición de proyecto", request.session.get("correo"), f"Proyecto {proyecto_id} actualizado")
        messages.success(request, "Proyecto actualizado correctamente.")
        return redirect('documentos:crud_proyectos')
    else:
        context = {'proyecto': proyecto_data, 'proyecto_id': proyecto_id}
        if request.session.get('rol') == 'Admin':
            empresas_data = db.child("Empresas").get().val() or {}
            empresas = []
            for key, val in empresas_data.items():
                empresas.append({'id': key, 'nombre': val.get('nombre', 'Sin Nombre')})
            context['empresas'] = empresas
        return render(request, 'editar_proyecto.html', context)


@empresario_required
def eliminar_proyecto(request, proyecto_id):
    rol = request.session.get('rol')
    proyecto_data = db.child("Proyectos").child(proyecto_id).get().val()
    if not proyecto_data:
        messages.error(request, "Proyecto no encontrado.")
        return redirect('documentos:crud_proyectos')
    if rol in ['Empresa', 'Empresario']:
        empresa_data = db.child("Empresas").order_by_child("correo").equal_to(request.session.get('correo')).get().val()
        if empresa_data:
            empresa_id = list(empresa_data.keys())[0]
            if proyecto_data.get("empresa_id") != empresa_id:
                messages.error(request, "No puedes eliminar proyectos de otra empresa.")
                return redirect('documentos:crud_proyectos')
        else:
            messages.error(request, "No se encontró tu empresa asociada.")
            return redirect('documentos:crud_proyectos')
    db.child("Proyectos").child(proyecto_id).remove()
    log_event("Eliminación de proyecto", request.session.get("correo"), f"Proyecto {proyecto_id} eliminado")
    messages.success(request, "Proyecto eliminado correctamente.")
    return redirect('documentos:crud_proyectos')

@alumno_required
def crear_postulacion(request, proyecto_id):
    if 'correo' not in request.session:
        messages.error(request, "Debes iniciar sesión.")
        return redirect('documentos:login')

    if request.method == "POST":
        # Obtener perfil del alumno usando su correo de sesión
        correo_alumno = request.session.get('correo')
        alumno_data = db.child("Usuarios").order_by_child("correo").equal_to(correo_alumno).get().val() or {}
        if not alumno_data:
            messages.error(request, "No se encontró tu perfil de alumno.")
            return redirect('documentos:dashboard')
        alumno_key = list(alumno_data.keys())[0]

        # Verificar que el alumno no se haya postulado ya al mismo proyecto
        postulaciones_data = db.child("Postulaciones").order_by_child("alumno_id").equal_to(alumno_key).get().val() or {}
        for key, post in postulaciones_data.items():
            if post.get("proyecto_id") == proyecto_id:
                messages.error(request, "Ya te has postulado a este proyecto.")
                return redirect('documentos:mis_postulaciones')

        # Recoger datos adicionales del formulario
        carrera = request.POST.get('carrera', '').strip()
        habilidades = request.POST.get('habilidades', '').strip()
        razon_interes = request.POST.get('razon_interes', '').strip()

        # Crear la nueva postulación
        nueva_postulacion = {
            "alumno_id": alumno_key,
            "proyecto_id": proyecto_id,
            "fecha_postulacion": datetime.now().strftime("%Y-%m-%d"),
            "estado": "Pendiente",
            "motivo_rechazo": "",
            "carrera": carrera,
            "habilidades": habilidades,
            "razon_interes": razon_interes
        }
        db.child("Postulaciones").push(nueva_postulacion)
        log_event("Creación de postulación", request.session.get("correo"), f"Postulación creada para proyecto {proyecto_id}")
        messages.success(request, "Te has postulado correctamente.")

        # Actualizar las vacantes del proyecto:
        proyecto_data = db.child("Proyectos").child(proyecto_id).get().val()
        if proyecto_data:
            current_vacantes = int(proyecto_data.get("vacantes", 0))
            new_vacantes = current_vacantes - 1
            if new_vacantes > 0:
                db.child("Proyectos").child(proyecto_id).update({"vacantes": new_vacantes})
            else:
                # Si no quedan vacantes, se actualiza el estado a "Cerrado" y se pone vacantes en 0
                db.child("Proyectos").child(proyecto_id).update({"vacantes": 0, "estado": "Cerrado"})

        # Enviar notificación al empresario correspondiente
        proyecto = db.child("Proyectos").child(proyecto_id).get().val() or {}
        empresa_id = proyecto.get("empresa_id")
        if empresa_id:
            empresa_data = db.child("Empresas").child(empresa_id).get().val() or {}
            correo_empresario = empresa_data.get("correo")
            if correo_empresario:
                notificacion = {
                    "rol": "Empresario",
                    "mensaje": "Un alumno se ha postulado a tu proyecto.",
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                db.child("Notificaciones").push(notificacion)

        return redirect('documentos:mis_postulaciones')
    return redirect('documentos:dashboard')

@alumno_required
def mis_postulaciones(request):
    if 'correo' not in request.session:
        messages.error(request, "Debes iniciar sesión.")
        return redirect('documentos:login')

    correo_alumno = request.session.get('correo')
    alumno_data = db.child("Usuarios").order_by_child("correo").equal_to(correo_alumno).get().val() or {}
    if not alumno_data:
        messages.error(request, "No se encontró tu perfil de alumno.")
        return redirect('documentos:login')

    alumno_key = list(alumno_data.keys())[0]
    postulaciones_data = db.child("Postulaciones").order_by_child("alumno_id").equal_to(alumno_key).get().val() or {}

    lista_postulaciones = []
    for key, val in postulaciones_data.items():
        # Convertir a minúsculas para la comparación
        estado = val.get("estado", "").strip().lower()
        # Ahora se incluye "pendiente", "aceptada" y "finalizada" (sin importar mayúsculas)
        if estado not in ["pendiente", "aceptada", "finalizada"]:
            continue
        # Normalizamos el campo de estado para que el template lo reciba en formato Title Case
        val["estado"] = estado.capitalize()  # Ejemplo: "Finalizada"
        val["id"] = key
        
        # Obtener el título del proyecto
        proyecto_info = db.child("Proyectos").child(val.get("proyecto_id")).get().val() or {}
        val["proyecto_titulo"] = proyecto_info.get("titulo", "Proyecto desconocido")
        
        # Obtener datos del alumno (correo y matrícula)
        alumno_info = db.child("Usuarios").child(alumno_key).get().val() or {}
        val["alumno_correo"] = alumno_info.get("correo", "")
        val["matricula"] = alumno_info.get("matricula", "")
        
        lista_postulaciones.append(val)

    return render(request, "mis_postulaciones.html", {
        "postulaciones": lista_postulaciones
    })


@admin_o_empresa_required
def listar_postulaciones(request):
    rol = request.session.get('rol')
    correo_usuario = request.session.get('correo')

    postulaciones_data = db.child("Postulaciones").get().val() or {}
    lista_post = []

    for key, val in postulaciones_data.items():
        val["id"] = key
        
        proyecto_info = db.child("Proyectos").child(val.get("proyecto_id")).get().val() or {}
        val["proyecto_titulo"] = proyecto_info.get("titulo", "Proyecto desconocido")
        val["empresa_id"] = proyecto_info.get("empresa_id")
        
        alumno_info = db.child("Usuarios").child(val.get("alumno_id")).get().val() or {}
        val["alumno_correo"] = alumno_info.get("correo", "")
        lista_post.append(val)

    
    lista_post = [p for p in lista_post if p.get("estado") != "Rechazada"]

    
    if rol in ["Empresa", "Empresario"]:
        empresa_data = db.child("Empresas").order_by_child("correo").equal_to(correo_usuario).get().val() or {}
        if empresa_data:
            emp_key = list(empresa_data.keys())[0]
            lista_post = [p for p in lista_post if p.get("empresa_id") == emp_key]

    return render(request, 'crud_postulaciones.html', {
        "postulaciones": lista_post
    })


@admin_o_empresa_required
@admin_o_empresa_required
def actualizar_postulacion(request, postulacion_id):
    post_data = db.child("Postulaciones").child(postulacion_id).get().val()
    if not post_data:
        messages.error(request, "Postulación no encontrada.")
        return redirect('documentos:crud_postulaciones')
    
    if request.method == "POST":
        # Obtener y normalizar el estado del formulario
        nuevo_estado = request.POST.get('estado', '').strip().capitalize()
        nuevo_motivo = request.POST.get('motivo_rechazo', '').strip()
        print("Nuevo estado recibido:", nuevo_estado)  # Para depuración
        
        # Si se selecciona "Finalizada", ignoramos el motivo de rechazo
        if nuevo_estado == "Finalizada":
            updates = {
                "estado": "Finalizada",
                "motivo_rechazo": ""
            }
        else:
            updates = {
                "estado": nuevo_estado,
                "motivo_rechazo": nuevo_motivo if nuevo_estado == "Rechazada" else ""
            }
        
        db.child("Postulaciones").child(postulacion_id).update(updates)
        log_event("Actualización de postulación", request.session.get("correo"), f"Postulación {postulacion_id} actualizada a {nuevo_estado}")

        # Notificar para estados Aceptada y Rechazada
        if nuevo_estado in ["Aceptada", "Rechazada"]:
            alumno = db.child("Usuarios").child(post_data["alumno_id"]).get().val()
            if alumno:
                correo_alumno = alumno.get("correo")
                if correo_alumno:
                    notificacion = {
                        "rol": "Alumno",
                        "mensaje": "Tu postulación ha sido aceptada." if nuevo_estado == "Aceptada" else "Tu postulación ha sido rechazada.",
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    db.child("Notificaciones").push(notificacion)
        
        # Si se actualiza a "Aceptada", decrementa vacantes en el proyecto
        if nuevo_estado == "Aceptada":
            proyecto = db.child("Proyectos").child(post_data["proyecto_id"]).get().val() or {}
            vacantes = int(proyecto.get("vacantes", 0))
            if vacantes > 0:
                vacantes -= 1
                db.child("Proyectos").child(post_data["proyecto_id"]).update({"vacantes": vacantes})
        
        # Si se actualiza a "Finalizada", genera la carta de finalización
        if nuevo_estado == "Finalizada":
            alumno = db.child("Usuarios").child(post_data["alumno_id"]).get().val()
            proyecto = db.child("Proyectos").child(post_data["proyecto_id"]).get().val()
            empresa = db.child("Empresas").child(proyecto["empresa_id"]).get().val()
            
            extra_context = {
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "current_year": datetime.now().year
            }
            pdf_path = generar_pdf_xhtml2pdf(alumno, proyecto, empresa,
                                             template_name="carta_finalizacion.html",
                                             extra_context=extra_context)
            
            relative_path = f"cartas/carta_finalizacion_{postulacion_id}.pdf"
            full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(pdf_path, "rb") as f:
                file_content = File(f)
                saved_path = default_storage.save(relative_path, file_content)
            url_pdf = settings.MEDIA_URL + saved_path
            db.child("Postulaciones").child(postulacion_id).update({"url_carta_finalizacion": url_pdf})
        
        messages.success(request, "La postulación se ha actualizado correctamente.")
        return redirect('documentos:crud_postulaciones')
    else:
        return render(request, "editar_postulacion.html", {
            "postulacion": post_data,
            "postulacion_id": postulacion_id
        })
    
@alumno_required
def cancelar_postulacion(request, postulacion_id):
    """
    Permite al alumno cancelar una postulación si está en estado "Pendiente".
    """
    post_data = db.child("Postulaciones").child(postulacion_id).get().val()
    if not post_data:
        messages.error(request, "Postulación no encontrada.")
        return redirect('documentos:mis_postulaciones')  

    
    correo_alumno = request.session.get('correo')
    alumno_data = db.child("Usuarios").order_by_child("correo").equal_to(correo_alumno).get().val() or {}
    if not alumno_data:
        messages.error(request, "No se encontró tu perfil de alumno.")
        return redirect('documentos:mis_postulaciones')
    
    alumno_key = list(alumno_data.keys())[0]
    if post_data.get("alumno_id") != alumno_key:
        return redirect('documentos:mis_postulaciones')

    if post_data.get("estado") == "Pendiente":
        db.child("Postulaciones").child(postulacion_id).update({"estado": "Cancelada"})
        log_event("Cancelación de postulación", request.session.get("correo"), f"Postulación {postulacion_id} cancelada")
        messages.success(request, "Has cancelado tu postulación.")
    else:
        messages.error(request, "No puedes cancelar esta postulación, ya ha sido revisada.")
    
    return redirect('documentos:mis_postulaciones')

    

@alumno_required
def catalogo_proyectos(request):
    # 1. Obtener perfil del alumno
    correo_alumno = request.session.get("correo")
    alumno_data = db.child("Usuarios").order_by_child("correo").equal_to(correo_alumno).get().val() or {}
    if not alumno_data:
        messages.error(request, "No se encontró tu perfil de alumno.")
        return redirect("documentos:dashboard")
    alumno_key = list(alumno_data.keys())[0]

    # 2. Consultar todas las postulaciones del alumno
    postulaciones_data = db.child("Postulaciones").order_by_child("alumno_id").equal_to(alumno_key).get().val() or {}
    for key, post in postulaciones_data.items():
        # Si tiene una postulación en estado Pendiente o Aceptada, se le redirige
        if post.get("estado") in ["Pendiente", "Aceptada"]:
            messages.error(request, "Ya estás en un proyecto y no puedes ver proyectos disponibles.")
            return redirect("documentos:dashboard")
    
    # 3. Obtener proyectos abiertos y con vacantes disponibles
    proyectos_data = db.child("Proyectos").order_by_child("estado").equal_to("Abierto").get().val() or {}
    proyectos_list = []
    for key, proyecto in proyectos_data.items():
        # Solo se muestran los proyectos con vacantes > 0
        if int(proyecto.get("vacantes", 0)) <= 0:
            continue
        proyecto["id"] = key
        # Obtener el nombre de la empresa asociada
        empresa = db.child("Empresas").child(proyecto.get("empresa_id")).get().val() or {}
        proyecto["empresa_nombre"] = empresa.get("nombre", "Empresa desconocida")
        proyectos_list.append(proyecto)
    
    # 4. Paginación
    paginator = Paginator(proyectos_list, 10)
    page = request.GET.get("page")
    proyectos = paginator.get_page(page)
    
    return render(request, "catalogo_proyectos.html", {"proyectos": proyectos})

def generar_carta_local(request, postulacion_id):
    """
    Genera la carta en PDF a partir de los datos del alumno, proyecto y empresa,
    la guarda localmente en MEDIA_ROOT y actualiza la postulación con la URL del PDF.
    """
    
    post_data = db.child("Postulaciones").child(postulacion_id).get().val()
    if not post_data:
        messages.error(request, "Postulación no encontrada.")
        return redirect('documentos:crud_postulaciones')
    
    
    alumno = db.child("Usuarios").child(post_data["alumno_id"]).get().val()
    proyecto = db.child("Proyectos").child(post_data["proyecto_id"]).get().val()
    empresa = db.child("Empresas").child(proyecto["empresa_id"]).get().val()
    
    
    pdf_path = generar_pdf_xhtml2pdf(alumno, proyecto, empresa)
    
    
    relative_path = f"cartas/carta_{postulacion_id}.pdf"
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    
    
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    
    with open(pdf_path, "rb") as f:
        file_content = File(f)
        saved_path = default_storage.save(relative_path, file_content)
    
   
    url_pdf = settings.MEDIA_URL + saved_path

    
    db.child("Postulaciones").child(postulacion_id).update({"url_carta": url_pdf})
    
    messages.success(request, "La carta se ha generado y está disponible para descarga.")
    return redirect('documentos:crud_postulaciones')

@csrf_exempt
def limpiar_notificaciones(request):
    if request.method == "POST":
        rol_actual = request.session.get("rol")
        notificaciones_data = db.child("Notificaciones").get().val() or {}
        for key, notif in notificaciones_data.items():
            if notif.get("rol") == rol_actual:
                db.child("Notificaciones").child(key).remove()
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Método no permitido"}, status=405)


@admin_o_empresa_required
def listar_seguimientos(request):
    rol = request.session.get("rol")
    correo_usuario = request.session.get("correo")
    
    # Si el usuario es empresario, obtener su empresa
    empresa_id = None
    if rol in ["Empresa", "Empresario"]:
        empresa_data = db.child("Empresas").order_by_child("correo").equal_to(correo_usuario).get().val() or {}
        if empresa_data:
            empresa_id = list(empresa_data.keys())[0]
    
    seguimientos_data = db.child("Seguimientos").get().val() or {}
    lista_seguimientos = []
    for key, seg in seguimientos_data.items():
        seg["id"] = key
        postulacion = db.child("Postulaciones").child(seg.get("postulacion_id", "")).get().val() or {}
        # Si es empresario, filtrar por proyecto que pertenezca a su empresa
        if rol in ["Empresa", "Empresario"]:
            proyecto = db.child("Proyectos").child(postulacion.get("proyecto_id", "")).get().val() or {}
            if proyecto.get("empresa_id") != empresa_id:
                continue
        # Agregar datos para mostrar: correo del alumno, título del proyecto, etc.
        alumno = db.child("Usuarios").child(postulacion.get("alumno_id", "")).get().val() or {}
        seg["alumno_correo"] = alumno.get("correo", "Sin correo")
        proyecto = db.child("Proyectos").child(postulacion.get("proyecto_id", "")).get().val() or {}
        seg["proyecto_titulo"] = proyecto.get("titulo", "Proyecto desconocido")
        lista_seguimientos.append(seg)
    
    paginator = Paginator(lista_seguimientos, 10)
    page = request.GET.get("page")
    seguimientos = paginator.get_page(page)
    return render(request, "crud_seguimientos.html", {"seguimientos": seguimientos})

@admin_o_empresa_required
def crear_seguimiento(request):
    """
    Permite crear un seguimiento nuevo, con opción de subir un archivo (evidencia).
    Sólo se mostrarán las postulaciones con estado "Aceptada".
    Para usuarios de tipo Empresa/Empresario se filtran aquellas postulaciones cuyo proyecto pertenezca a su empresa.
    """
    if request.method == "POST":
        postulacion_id = request.POST.get("postulacion_id", "").strip()
        fecha = request.POST.get("fecha", "").strip()  
        avances = request.POST.get("avances", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()
        
        
        evidencias = []
        if "evidencia" in request.FILES:
            file_obj = request.FILES["evidencia"]
            relative_path = "seguimientos/" + file_obj.name
            saved_path = default_storage.save(relative_path, file_obj)
            url_archivo = settings.MEDIA_URL + saved_path
            evidencias.append({"nombre": file_obj.name, "url": url_archivo})
        
        if not postulacion_id or not fecha:
            messages.error(request, "La postulación y la fecha son obligatorias.")
            return redirect("documentos:crear_seguimiento")
        
        nuevo_seg = {
            "postulacion_id": postulacion_id,
            "fecha": fecha,
            "avances": avances,
            "observaciones": observaciones,
            "evidencias": evidencias
        }
        db.child("Seguimientos").push(nuevo_seg)
        messages.success(request, "Seguimiento creado correctamente.")
        return redirect("documentos:crud_seguimientos")
    
    
    postulaciones_data = db.child("Postulaciones").order_by_child("estado").equal_to("Aceptada").get().val() or {}
    lista_postulaciones = []
    rol = request.session.get("rol")
    if rol in ["Empresa", "Empresario"]:
        correo_usuario = request.session.get("correo")
        empresa_data = db.child("Empresas").order_by_child("correo").equal_to(correo_usuario).get().val() or {}
        if empresa_data:
            empresa_id = list(empresa_data.keys())[0]
        else:
            empresa_id = None

    for key, p in postulaciones_data.items():
        p["id"] = key
        
        alumno = db.child("Usuarios").child(p.get("alumno_id", "")).get().val() or {}
        p["alumno_correo"] = alumno.get("correo", "Sin correo")
        
        if rol in ["Empresa", "Empresario"]:
            proyecto = db.child("Proyectos").child(p.get("proyecto_id", "")).get().val() or {}
            if proyecto.get("empresa_id") == empresa_id:
                lista_postulaciones.append(p)
        else:
            
            lista_postulaciones.append(p)
    
    return render(request, "crear_seguimiento.html", {"postulaciones": lista_postulaciones})



@admin_o_empresa_required
def editar_seguimiento(request, seguimiento_id):
    """
    Permite editar un seguimiento existente.
    """
    seg = db.child("Seguimientos").child(seguimiento_id).get().val()
    if not seg:
        messages.error(request, "Seguimiento no encontrado.")
        return redirect("documentos:crud_seguimientos")
    
    if request.method == "POST":
        postulacion_id = request.POST.get("postulacion_id", "").strip()
        fecha = request.POST.get("fecha", "").strip()
        avances = request.POST.get("avances", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()
        updates = {
            "postulacion_id": postulacion_id,
            "fecha": fecha,
            "avances": avances,
            "observaciones": observaciones
        }
        db.child("Seguimientos").child(seguimiento_id).update(updates)
        messages.success(request, "Seguimiento actualizado correctamente.")
        return redirect("documentos:crud_seguimientos")
    
    return render(request, "editar_seguimiento.html", {"seguimiento": seg, "seguimiento_id": seguimiento_id})


@admin_o_empresa_required
def eliminar_seguimiento(request, seguimiento_id):
    """
    Permite eliminar un seguimiento.
    """
    seg = db.child("Seguimientos").child(seguimiento_id).get().val()
    if not seg:
        messages.error(request, "Seguimiento no encontrado.")
        return redirect("documentos:crud_seguimientos")
    db.child("Seguimientos").child(seguimiento_id).remove()
    messages.success(request, "Seguimiento eliminado correctamente.")
    return redirect("documentos:crud_seguimientos")




@alumno_required
def dashboard_seguimientos_alumno(request):
    correo = request.session.get("correo")
    alumno_data = db.child("Usuarios").order_by_child("correo").equal_to(correo).get().val() or {}
    if not alumno_data:
        messages.error(request, "No se encontró tu perfil de alumno.")
        return redirect("documentos:dashboard")
    alumno_key = list(alumno_data.keys())[0]
    
    
    postulaciones_data = db.child("Postulaciones").order_by_child("alumno_id").equal_to(alumno_key).get().val() or {}
    postulacion_ids = set(postulaciones_data.keys())
    
 
    seguimientos_data = db.child("Seguimientos").get().val() or {}
    timeline = []
    for key, seg in seguimientos_data.items():
        if seg.get("postulacion_id") in postulacion_ids:
            seg["id"] = key
            
            postulacion = db.child("Postulaciones").child(seg.get("postulacion_id")).get().val() or {}
            proyecto = db.child("Proyectos").child(postulacion.get("proyecto_id", "")).get().val() or {}
            empresa = db.child("Empresas").child(proyecto.get("empresa_id", "")).get().val() or {}
            seg["empresa_nombre"] = empresa.get("nombre", "Empresa desconocida")
            timeline.append(seg)
    
    timeline.sort(key=lambda s: s.get("fecha", ""))
    
    return render(request, "seguimientos_alumno.html", {"seguimientos": timeline})


@admin_o_empresa_required
def dashboard_seguimientos(request):
    
    seguimientos_data = db.child("Seguimientos").get().val() or {}
    timeline = []
    for key, seg in seguimientos_data.items():
        seg["id"] = key
        timeline.append(seg)
    
    timeline.sort(key=lambda s: s.get("fecha", ""))
    return render(request, "dashboard_seguimientos.html", {"seguimientos": timeline})

@admin_o_empresa_required
def dashboard_seguimientos(request):
    
    correo_usuario = request.session.get("correo")
    
    empresa_data = db.child("Empresas").order_by_child("correo").equal_to(correo_usuario).get().val() or {}
    if not empresa_data:
        messages.error(request, "No se encontró tu empresa asociada.")
        return redirect('documentos:dashboard')
    empresa_id = list(empresa_data.keys())[0]

    
    proyectos_data = db.child("Proyectos").order_by_child("empresa_id").equal_to(empresa_id).get().val() or {}
    proyectos_ids = set(proyectos_data.keys())

    
    seguimientos_data = db.child("Seguimientos").get().val() or {}
    timeline = []
    for key, seg in seguimientos_data.items():
        seg["id"] = key
        postulacion_id = seg.get("postulacion_id", "")
        postulacion = db.child("Postulaciones").child(postulacion_id).get().val() or {}
       
        if postulacion.get("proyecto_id") not in proyectos_ids:
            continue
        
        alumno_id = postulacion.get("alumno_id", "")
        alumno = db.child("Usuarios").child(alumno_id).get().val() or {}
        seg["alumno_correo"] = alumno.get("correo", "Sin correo")
        
        proyecto_id = postulacion.get("proyecto_id", "")
        proyecto = db.child("Proyectos").child(proyecto_id).get().val() or {}
        seg["proyecto_titulo"] = proyecto.get("titulo", "Proyecto desconocido")
        timeline.append(seg)
    
    
    timeline.sort(key=lambda s: s.get("fecha", ""), reverse=True)
    return render(request, "dashboard_seguimientos.html", {"seguimientos": timeline})


def generar_carta_finalizacion(request, postulacion_id):
    """
    Genera la carta de finalización en PDF a partir de los datos del alumno,
    proyecto y empresa, usando el template 'carta_finalizacion.html'.
    El PDF se guarda localmente (en MEDIA_ROOT) y se actualiza la postulación con la URL.
    """
    # Obtener la postulación desde Firebase
    post_data = db.child("Postulaciones").child(postulacion_id).get().val()
    if not post_data:
        messages.error(request, "Postulación no encontrada.")
        return redirect('documentos:crud_postulaciones')
    
    # Obtener datos del alumno, proyecto y empresa
    alumno = db.child("Usuarios").child(post_data["alumno_id"]).get().val()
    proyecto = db.child("Proyectos").child(post_data["proyecto_id"]).get().val()
    empresa = db.child("Empresas").child(proyecto["empresa_id"]).get().val()

    # Preparar datos adicionales para la carta
    data_extra = {
        "current_date": datetime.now().strftime("%Y-%m-%d"),
        "current_year": datetime.now().year,
    }
    
    # Generar el PDF usando el template 'carta_finalizacion.html'
    # La función generar_pdf_xhtml2pdf debe estar preparada para recibir el nombre del template
    pdf_path = generar_pdf_xhtml2pdf(alumno, proyecto, empresa, template_name="carta_finalizacion.html", extra_context=data_extra)
    
    # Definir la ruta relativa dentro de MEDIA_ROOT para guardar el PDF
    relative_path = f"cartas/carta_finalizacion_{postulacion_id}.pdf"
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    
    # Crear el directorio si no existe
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # Guardar el PDF en el almacenamiento local
    with open(pdf_path, "rb") as f:
        file_content = File(f)
        saved_path = default_storage.save(relative_path, file_content)
    
    # Construir la URL pública (asumiendo que MEDIA_URL está configurado en settings)
    url_pdf = settings.MEDIA_URL + saved_path

    # Actualizar la postulación con la URL del PDF generado
    db.child("Postulaciones").child(postulacion_id).update({"url_carta_finalizacion": url_pdf})
    
    messages.success(request, "La carta de finalización se ha generado y está disponible para descarga.")
    return redirect('documentos:crud_postulaciones')

@alumno_required
def mis_finalizaciones(request):
    """
    Vista para que el alumno vea las cartas de finalización generadas para sus postulaciones.
    Se mostrarán aquellas postulaciones que tengan el estado "Finalizada" y contengan la URL de la carta.
    """
    if 'correo' not in request.session:
        messages.error(request, "Debes iniciar sesión.")
        return redirect('documentos:login')

    correo_alumno = request.session.get('correo')
    alumno_data = db.child("Usuarios").order_by_child("correo").equal_to(correo_alumno).get().val() or {}
    if not alumno_data:
        messages.error(request, "No se encontró tu perfil de alumno.")
        return redirect('documentos:login')

    alumno_key = list(alumno_data.keys())[0]
    postulaciones_data = db.child("Postulaciones").order_by_child("alumno_id").equal_to(alumno_key).get().val() or {}

    finalizaciones = []
    for key, val in postulaciones_data.items():
        estado = val.get("estado", "").strip().lower()
        # Se consideran finalizadas aquellas postulaciones con estado "finalizada"
        # Y que tengan definida la URL de la carta
        if estado == "finalizada" and val.get("url_carta_finalizacion"):
            val["id"] = key
            # Opcionalmente, puedes obtener más datos, por ejemplo el título del proyecto
            proyecto_info = db.child("Proyectos").child(val.get("proyecto_id")).get().val() or {}
            val["proyecto_titulo"] = proyecto_info.get("titulo", "Proyecto desconocido")
            finalizaciones.append(val)

    # Ordenar por fecha de postulación (más reciente primero)
    finalizaciones.sort(key=lambda s: s.get("fecha_postulacion", ""), reverse=True)
    
    return render(request, "mis_finalizaciones.html", {
        "finalizaciones": finalizaciones
    }) 

def log_event(action, user, details):
    """
    Registra un evento en el nodo 'Logs' de Firebase.
    
    :param action: Una cadena que describe la acción (e.g., "Creación de empresa")
    :param user: El correo o identificador del usuario que realiza la acción.
    :param details: Detalles adicionales sobre la acción.
    """
    log_data = {
        "action": action,
        "user": user,
        "details": details,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    db.child("Logs").push(log_data)

@admin_required
def ver_logs(request):
    # Obtener todos los logs desde Firebase
    logs_data = db.child("Logs").get().val() or {}
    logs_list = []
    for key, log in logs_data.items():
        log["id"] = key
        logs_list.append(log)
    # Ordenar los logs por timestamp en orden descendente
    logs_list = sorted(logs_list, key=lambda x: x["timestamp"], reverse=True)
    # Paginación: 10 logs por página
    paginator = Paginator(logs_list, 10)
    page = request.GET.get('page')
    paginated_logs = paginator.get_page(page)
    return render(request, "logs_admin.html", {"logs": paginated_logs})

@csrf_exempt
def actualizar_matricula_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permiten peticiones POST."}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    
    correo = data.get("correo", "").strip()
    matricula = data.get("matricula", "").strip()

    if not correo or not matricula:
        return JsonResponse({"error": "Los campos 'correo' y 'matricula' son obligatorios."}, status=400)
    
    # Busca el usuario en db por correo
    usuarios = db.child("Usuarios").order_by_child("correo").equal_to(correo).get().val() or {}
    if not usuarios:
        return JsonResponse({"error": "Usuario no encontrado."}, status=404)
    
    uid = list(usuarios.keys())[0]
    
    try:
        db.child("Usuarios").child(uid).update({"matricula": matricula})
    except Exception as e:
        return JsonResponse({"error": f"Error al actualizar la matrícula: {str(e)}"}, status=500)
    
    return JsonResponse({"success": True, "message": "Matrícula actualizada correctamente."})