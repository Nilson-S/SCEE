from django.db import models
# Create your models here.
from django.contrib.auth.models import User

class HistorialComando(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="historial_comandos")
    comando = models.CharField(max_length=255)
    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)

    def __str__(self):
        return f"Comando ejecutado por {self.usuario.username} el {self.fecha} a las {self.hora}"
    
class TasaBCV(models.Model):
    fecha = models.DateField(unique=True)
    valor = models.DecimalField(max_digits=10, decimal_places=6)

    def __str__(self):
        return f"{self.fecha} - {self.valor}"
