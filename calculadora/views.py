import requests
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.views import LoginView
from django.utils.translation import gettext as _
from .forms import UsuarioForm
from .models import HistorialComando  # Importamos el modelo HistorialComando
from bs4 import BeautifulSoup
import requests
import time
from .models import TasaBCV
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from django.utils.dateparse import parse_date



def obtener_tasa_dia():
    hoy = datetime.today().date()

    # Si ya está guardada la tasa del día, úsala
    tasa_guardada = TasaBCV.objects.filter(fecha=hoy).first()
    if tasa_guardada:
        return float(tasa_guardada.valor)

    # Espera para asegurar carga de página
    time.sleep(3)

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://www.bcv.org.ve/estadisticas/indice-de-inversion"
        response = requests.get(url, headers=headers, verify=False, timeout=5)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            celda = soup.find("td", class_="views-field views-field-views-conditional")
            if celda:
                valor_str = celda.get_text(strip=True).replace(".", "").replace(",", ".")
                valor = float(valor_str)

                # Guardar la tasa en la BD
                TasaBCV.objects.create(fecha=hoy, valor=valor)
                return valor
    except Exception:
        return None

# Calcula el total a pagar
def calcular_total(kg, valor_por_kg, tkt, moneda="USD"):
    monto = kg * valor_por_kg
    impuesto_3 = 0
    impuesto_16 = monto * 0.16

    if moneda == "USD" or valor_por_kg in [1, 3]:
        impuesto_3 = monto * 0.03

    total = monto + impuesto_16 + impuesto_3

    if moneda == "USD" :
        comando = f"WX*XB{kg}K{valor_por_kg:.2f}USD*TX{impuesto_3:.2f}6D/{impuesto_16:.2f}YN*ET/{tkt}/E1*S1*N1*FCA"
    else:
        comando = f"WX*XB{kg}K{valor_por_kg:.2f}VES*TX{impuesto_16:.2f}YN*ET/{tkt}/E1*S1*F.MA"

    return comando, total

# Validación de permisos
def es_admin(user):
    return user.is_superuser or user.groups.filter(name="Administrador").exists()

# Vista para crear usuarios
def usuarios_crear(request):
    form = UsuarioForm()

    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, "Usuario creado exitosamente.")
            return redirect("usuarios_lista")

    return render(request, "calculadora/usuarios_crear.html", {"form": form})

# Vista para listar usuarios
@login_required
def usuarios_lista(request):
    usuarios = User.objects.all()
    return render(request, "calculadora/usuarios_lista.html", {"usuarios": usuarios})

# Vista principal de cálculo
@login_required
@csrf_exempt
def index(request):
    if es_admin(request.user):
        return redirect("usuarios_lista")

    tasa = obtener_tasa_dia()
    error = ""
    comando_generado = False
    kg = request.POST.get("kg", "")
    tkt = request.POST.get("tkt", "")
    modo = request.POST.get("modo", "usd")
    tasa_manual = request.POST.get("tasa_manual", "")
    tarifa_base_valor = request.POST.get("tarifa_base_valor", "")
    tarifa_base_moneda = request.POST.get("tarifa_base_moneda", "USD")

    resultado_usd = ""
    resultado_ves = ""
    total_usd = None
    total_ves = None

    if request.method == "POST":
        try:
            if not tkt:
                raise ValueError("Debe ingresar el número de boleto.")
            tkt_int = int(tkt)

            if modo == "usd":
                kg_int = int(kg)
                valor_usd = 1
                resultado_usd, total_usd = calcular_total(kg_int, valor_usd, tkt_int, "USD")

                valor_ves = tasa if tasa else float(tasa_manual)
                resultado_ves, total_ves = calcular_total(kg_int, valor_ves, tkt_int, "VES")

                comando_generado = True

                HistorialComando.objects.create(
                    usuario=request.user,
                    comando=f"Generó comandos USD/VES para {kg_int}kg, boleto {tkt_int}",
                    fecha=datetime.today().date(),
                    hora=datetime.now().strftime("%H:%M:%S")
                )

            elif modo == "lrv":
                kg_int = int(kg)
                resultado_usd, total_usd = calcular_total(kg_int, 3, tkt_int, "USD")

                if tasa:
                    resultado_ves, total_ves = calcular_total(kg_int, tasa * 3, tkt_int, "VES")
                else:
                    if not tasa_manual:
                        raise ValueError("Debe ingresar una tasa manual si no se obtiene la tasa automática.")
                    resultado_ves, total_ves = calcular_total(kg_int, float(tasa_manual) * 3, tkt_int, "VES")

                comando_generado = True

                HistorialComando.objects.create(
                    usuario=request.user,
                    comando=f"Generó comandos LRV USD/VES para {kg_int}kg, boleto {tkt_int}",
                    fecha=datetime.today().date(),
                    hora=datetime.now().strftime("%H:%M:%S")
                )

            elif modo == "tarifa_base":
                kg_int = int(kg)
                if not tarifa_base_valor:
                    raise ValueError("Debe ingresar la tarifa base.")
                valor = float(tarifa_base_valor) * 0.01
                resultado_usd, total_usd = calcular_total(kg_int, valor, tkt_int, tarifa_base_moneda)
                comando_generado = True

            elif modo == "mascota":
                # Modo mascota: 50 USD por mascota (1P)
                kg_int = 1
                valor_mascota_usd = 50

                # Comando USD
                impuesto_3_usd = valor_mascota_usd * 0.03
                impuesto_16_usd = valor_mascota_usd * 0.16
                total_usd = valor_mascota_usd + impuesto_3_usd + impuesto_16_usd
                resultado_usd = f"WX*XB1P{valor_mascota_usd:.2f}USD*TX{impuesto_3_usd:.2f}6D/{impuesto_16_usd:.2f}YN*ET/{tkt_int}/E1*S1*N1*FCA"

                # Comando VES
                if tasa:
                    valor_mascota_ves = tasa * 50
                else:
                    if not tasa_manual:
                        raise ValueError("Debe ingresar una tasa manual si no se obtiene la tasa automática.")
                    valor_mascota_ves = float(tasa_manual) * 50

                impuesto_16_ves = valor_mascota_ves * 0.16
                total_ves = valor_mascota_ves + impuesto_16_ves
                resultado_ves = f"WX*XB1P{valor_mascota_ves:.2f}VES*TX{impuesto_16_ves:.2f}YN*ET/{tkt_int}/E1*S1*F.MA"

                comando_generado = True

                HistorialComando.objects.create(
                    usuario=request.user,
                    comando=f"Generó comandos Mascota USD/VES para boleto {tkt_int}",
                    fecha=datetime.today().date(),
                    hora=datetime.now().strftime("%H:%M:%S")
                )

            else:
                raise ValueError("Modo de cálculo inválido.")

        except ValueError as ve:
            error = str(ve)
        except Exception:
            error = "Ocurrió un error al procesar los datos. Verifique los valores ingresados."

    return render(request, "calculadora/index.html", {
        "resultado_usd": resultado_usd,
        "total_usd": total_usd,
        "resultado_ves": resultado_ves,
        "total_ves": total_ves,
        "tasa": tasa,
        "error": error,
        "comando_generado": comando_generado,
        "kg": kg,
        "tkt": tkt,
        "modo": modo,
        "tasa_manual": tasa_manual,
        "tarifa_base_valor": tarifa_base_valor,
        "tarifa_base_moneda": tarifa_base_moneda,
        "now": datetime.now()
    })
# Inhabilitar usuario
@login_required
@user_passes_test(es_admin)
def inhabilitar_usuario(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)
    if request.user == usuario:
        messages.warning(request, "No puedes inhabilitar tu propio usuario.")
    else:
        usuario.is_active = False
        usuario.save()
    return redirect("usuarios_lista")

# Reactivar usuario
@login_required
@user_passes_test(es_admin)
def reactivar_usuario(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)
    usuario.is_active = True
    usuario.save()
    return redirect("usuarios_lista")

# Hacer superusuario
@login_required
@user_passes_test(es_admin)
def hacer_superusuario(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)
    usuario.is_superuser = True
    usuario.save()
    return redirect("usuarios_lista")

# Quitar superusuario
@login_required
@user_passes_test(es_admin)
def quitar_superusuario(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)
    if usuario != request.user:
        usuario.is_superuser = False
        usuario.save()
    return redirect("usuarios_lista")

# Vista personalizada de login
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def form_invalid(self, form):
        username = self.request.POST.get('username')
        password = self.request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user is not None and not user.is_active:
            form.add_error(None, _("Tu usuario está inhabilitado. Contacta al administrador del sistema."))
        return self.render_to_response(self.get_context_data(form=form))

# Vista para mostrar el historial de comandos x usuario
@login_required
@user_passes_test(es_admin)
def historial_comandos_usuario(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)
    fecha_filtro = request.GET.get('fecha')

    historiales = HistorialComando.objects.filter(usuario=usuario)

    if fecha_filtro:
        try:
            fecha_obj = parse_date(fecha_filtro)
            if fecha_obj:
                historiales = historiales.filter(fecha=fecha_obj)
        except:
            pass

    historiales = historiales.order_by('-fecha', '-hora')

    paginator = Paginator(historiales, 10)
    page = request.GET.get("page")
    historiales_paginados = paginator.get_page(page)

    return render(request, "calculadora/historial_comandos_usuario.html", {
        "historiales": historiales_paginados,
        "usuario": usuario,
        "fecha_filtro": fecha_filtro
    })

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Administrador").exists())
def ver_tasas(request):
    tasas = TasaBCV.objects.all().order_by('-fecha')
    paginator = Paginator(tasas, 10)  # Mostrar 10 por página

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "calculadora/ver_tasas.html", {"page_obj": page_obj})