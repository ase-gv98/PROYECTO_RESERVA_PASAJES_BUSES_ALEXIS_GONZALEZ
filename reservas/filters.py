from django_filters import rest_framework as filters

from .models import Servicio


class ServicioFilter(filters.FilterSet):
    """Define filtros opcionales para buscar servicios de transporte."""

    origen = filters.CharFilter(
        field_name="ruta__origen__ciudad__nombre",
        lookup_expr="iexact",
    )
    destino = filters.CharFilter(
        field_name="ruta__destino__ciudad__nombre",
        lookup_expr="iexact",
    )
    fecha_salida = filters.DateFilter(
        field_name="fecha_hora_salida",
        lookup_expr="date",
    )
    precio_min = filters.NumberFilter(method="filter_precio_min")
    precio_max = filters.NumberFilter(method="filter_precio_max")

    def filter_precio_min(self, queryset, name, value):
        """Filtra servicios cuya tarifa de cama o semicama supera el minimo."""
        return queryset.filter(tarifa_semicama__gte=value) | queryset.filter(
            tarifa_cama__gte=value
        )

    def filter_precio_max(self, queryset, name, value):
        """Filtra servicios cuya tarifa de cama o semicama no supera el maximo."""
        return queryset.filter(tarifa_semicama__lte=value) | queryset.filter(
            tarifa_cama__lte=value
        )

    class Meta:
        model = Servicio
        fields = ["origen", "destino", "fecha_salida", "precio_min", "precio_max"]