from django.shortcuts import render, redirect
from django.contrib import messages
from .firebase import obtener_usuario_por_correo,db
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from datetime import datetime
from django.core.paginator import Paginator

# restringe accesoS
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
    return render(request, 'dashboard.html', {
        "usuarios": usuarios,
        "usuario_actual": request.session.get('correo'),
        "rol_actual": request.session.get('rol')
    })


def logout_view(request):
    request.session.flush()
    messages.info(request, "Sesión cerrada.")
    return redirect('documentos:login')

@no_alumno_required
def crud_empresas(request):
    empresas = db.child("Empresas").get().val()
    lista_empresas = []

    if empresas:
        for key, empresa in empresas.items():
            empresa['id'] = key
            # Asegurar que siempre haya un número de teléfono mostrado
            empresa['telefono'] = empresa.get('telefono') or empresa.get('contacto', 'No disponible')
            lista_empresas.append(empresa)

    return render(request, 'crud_empresas.html', {'empresas': lista_empresas})


def crud_proyectos(request):
    return render(request, 'crud_proyectos.html')

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

        # Verificar si el correo ya existe
        usuarios = db.child("Usuarios").get().val() or {}
        for key, data in usuarios.items():
            if data.get("correo") == correo:
                messages.error(request, "El usuario ya está en uso.")
                return redirect('documentos:crear_usuario')

        # Si el rol es Alumno, verificar que cumpla con los requisitos minimos y que matricula y teléfono estén informados
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
        messages.success(request, "Usuario actualizado exitosamente.")
        return redirect('documentos:crud_usuarios')

    return render(request, 'editar_usuario.html', {
        "usuario": usuario_data,
        "user_id": user_id
    })




@admin_required
def eliminar_usuario(request, user_id):
    db.child("Usuarios").child(user_id).remove()
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
        # Aseguramos un estado, por defecto "Abierto"
        if "estado" not in val:
            val["estado"] = "Abierto"
        proyectos_list.append(val)
    
    # Si el usuario es Empresario, se muestran solo sus proyectos
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
    messages.success(request, "Proyecto eliminado correctamente.")
    return redirect('documentos:crud_proyectos')