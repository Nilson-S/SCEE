from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from calculadora.views import CustomLoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Rutas de autenticación
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # Rutas de la app principal
    path('', include('calculadora.urls')),
]
