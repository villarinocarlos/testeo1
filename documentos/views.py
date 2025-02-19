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
        # Llamamos a la función que busca el usuario en Firebase
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


# placeholders de momento
def crud_empresas(request):
    return render(request, 'crud_empresas.html')


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

        # Verificar si el correo ya existe
        usuarios = db.child("Usuarios").get().val() or {}
        for key, data in usuarios.items():
            if data.get("correo") == correo:
                messages.error(request, "El usuario ya está en uso.")
                return redirect('documentos:crear_usuario')

        # Si el rol es Alumno, verificar que cumpla con los requisitos mínimos
        if rol == "Alumno":
            c = int(creditos) if creditos else 0
            s = int(semestre) if semestre else 0
            if c < 180 or s < 7:
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

        # Verificar si el correo ya existe en otro usuario
        usuarios = db.child("Usuarios").get().val() or {}
        for key, data in usuarios.items():
            if key != user_id and data.get("correo") == correo:
                messages.error(request, "El usuario ya está en uso.")
                return redirect('documentos:editar_usuario', user_id=user_id)

        # Si rol Alumno, verificar requisitos
        if rol == "Alumno":
            c = int(creditos) if creditos else 0
            s = int(semestre) if semestre else 0
            if c < 180 or s < 7:
                messages.error(request, "No cumples con los requisitos para presentar estadía.")
                return redirect('documentos:editar_usuario', user_id=user_id)

        updates = {
            "correo": correo,
            "rol": rol
        }
        # Actualizar contraseña solo si se ingresó una nueva
        if nueva_contraseña:
            updates["contraseña"] = nueva_contraseña
        if rol == "Alumno":
            updates["creditos"] = int(creditos) if creditos else 0
            updates["semestre"] = int(semestre) if semestre else 0
        else:
            updates["creditos"] = None
            updates["semestre"] = None

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