from django.urls import include, path
from rest_framework.routers import DefaultRouter
from reservas.views import RegistroPasajeroView
from .views import (
	AsientosServicioView,
	CarroPasajesView,
	CheckoutView,
	CustomTokenObtainPairView,
	EstadoVentaView,
	MisBoletosView,
	AnularPasajeView,
	CambiarPasajeView,
	ServicioAdminViewSet,
	ServicioSearchViewSet,
)


router = DefaultRouter()
router.register("servicios/buscar", ServicioSearchViewSet, basename="servicio-busqueda")
router.register("servicios", ServicioAdminViewSet, basename="servicio-admin")

urlpatterns = [
	path("auth/token/", CustomTokenObtainPairView.as_view(), name="token-obtain-pair"),
	path(
		"servicios/<int:servicio_id>/asientos/",
		AsientosServicioView.as_view(),
		name="servicio-asientos",
	),
	path("auth/registro/", RegistroPasajeroView.as_view(), name="registro_pasajero"),
	path("carro-pasajes/", CarroPasajesView.as_view(), name="carro-pasajes"),
	path("ventas/checkout/", CheckoutView.as_view(), name="checkout"),
	path("mis-boletos/", MisBoletosView.as_view(), name="mis-boletos"),
	path("boletos/<int:boleto_id>/anular/", AnularPasajeView.as_view(), name="boleto-anular"),
	path("boletos/<int:boleto_id>/cambiar/", CambiarPasajeView.as_view(), name="boleto-cambiar"),
	path("ventas/<int:venta_id>/estado/", EstadoVentaView.as_view(), name="venta-estado"),
	path("", include(router.urls)),
]
