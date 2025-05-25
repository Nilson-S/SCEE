from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages

# Verificación de si el usuario pertenece al grupo Administrador
def is_admin(user):
    return user.groups.filter(name='Administrador').exists() or user.is_superuser

# Vista para listar todos los usuarios
@login_required
@user_passes_test(is_admin)
def lista_usuarios(request):
    usuarios = User.objects.all()
    return render(request, 'calculadora/usuarios/lista.html', {'usuarios': usuarios})

# Vista para crear un nuevo usuario
@login_required
@user_passes_test(is_admin)
def crear_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, "El nombre de usuario ya existe.")
        else:
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, f"Usuario {username} creado correctamente.")
            return redirect('usuarios_lista')

    return render(request, 'calculadora/usuarios/crear.html')
