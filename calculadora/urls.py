from django.urls import path
from . import views
from . import admin_views 
from calculadora.views import CustomLoginView
from django.contrib import admin

urlpatterns = [
    path('', views.index, name='index'),
    path('usuarios/', admin_views.lista_usuarios, name='usuarios_lista'),
    path('usuarios/crear/', admin_views.crear_usuario, name='usuarios_crear'),
    path('usuarios/<int:usuario_id>/inhabilitar/', views.inhabilitar_usuario, name='inhabilitar_usuario'),
    path('usuarios/<int:usuario_id>/reactivar/', views.reactivar_usuario, name='reactivar_usuario'),
    path('admin/', admin.site.urls),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('usuarios/<int:usuario_id>/hacer_superusuario/', views.hacer_superusuario, name='hacer_superusuario'),
    path('usuarios/<int:usuario_id>/quitar_superusuario/', views.quitar_superusuario, name='quitar_superusuario'),


    path('tasas/', views.ver_tasas, name='ver_tasas'),
    # Ruta para acceder al historial de comandos x usuario
    path('usuarios/<int:usuario_id>/historial-comandos/', views.historial_comandos_usuario, name='historial_comandos_usuario'),  # <-- Cambiar esta línea
]
