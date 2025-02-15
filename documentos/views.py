from django.shortcuts import render, redirect
from django.contrib import messages
from .firebase import obtener_usuario_por_correo,db
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse


def login_view(request):
    if request.method == "POST":
        correo = request.POST.get('correo')
        contraseña = request.POST.get('contraseña')
        uid, usuario = obtener_usuario_por_correo(correo)

        if usuario and usuario.get("contraseña") == contraseña:
            request.session['correo'] = correo
            request.session['rol'] = usuario.get('rol')
            messages.success(request, "Inicio de sesión exitoso.")
            
            return redirect('documentos:dashboard')

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