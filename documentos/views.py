from django.shortcuts import render, redirect
from django.contrib import messages
from .firebase import obtener_usuario_por_correo,db
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse


# restringe acceso a admin
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get('rol') != 'Admin':
            messages.error(request, "No tienes permisos para acceder a esta sección.")
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