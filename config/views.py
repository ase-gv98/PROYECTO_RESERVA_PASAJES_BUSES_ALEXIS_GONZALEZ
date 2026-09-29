from decimal import Decimal

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import logout as django_logout
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from reservas.models import Boleto, Servicio, Venta


def buscar_pasajes_view(request):
    """Recibe la peticion web y retorna la plantilla del buscador."""
    return render(request, "buscar_pasajes.html")


def carro_view(request):
    """Recibe la peticion web y retorna la plantilla del carro."""
    return render(request, "carro.html")


def mis_boletos_view(request):
    """Recibe la peticion web y retorna la plantilla de boletos."""
    return render(request, "mis_boletos.html")


def logout_view(request):
    """Cierra la sesion Django y redirige a la pagina principal."""
    django_logout(request)
    return redirect("/")


@user_passes_test(lambda user: user.is_staff or user.is_superuser)
def admin_dashboard_view(request):
    """Calcula metricas administrativas y retorna el panel protegido."""
    # Se consideran servicios futuros, boletos pagados y ventas confirmadas.
    total_recaudado = (
        Venta.objects.filter(estado=Venta.Estado.PAGADO).aggregate(total=Sum("total"))["total"]
        or Decimal("0")
    )
    return render(
        request,
        "admin_dashboard.html",
        {
            "servicios_activos": Servicio.objects.filter(
                fecha_hora_salida__gte=timezone.now()
            ).count(),
            "pasajes_vendidos": Boleto.objects.filter(
                venta__estado=Venta.Estado.PAGADO
            ).count(),
            "monto_recaudado": total_recaudado,
        },
    )


def custom_404_view(request, exception=None):
    """Recibe una ruta inexistente y retorna respuesta JSON o plantilla 404."""
    if request.path.startswith("/api/"):
        return JsonResponse({"error": "Endpoint no encontrado"}, status=404)
    return render(request, "404.html", status=404)
