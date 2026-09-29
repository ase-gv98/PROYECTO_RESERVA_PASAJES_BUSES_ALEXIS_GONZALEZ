from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AsientoServicio, Servicio, Venta


@receiver(post_save, sender=Servicio)
def crear_asientos_del_servicio(sender, instance, created, **kwargs):
    """Crea los asientos disponibles al registrar un servicio nuevo."""
    # La capacidad del bus determina cuantos asientos se persisten para el servicio.
    if not created:
        return

    capacidad = instance.bus.capacidad_asientos
    mitad = capacidad // 2
    AsientoServicio.objects.bulk_create(
        AsientoServicio(
            servicio=instance,
            numero_asiento=numero,
            tipo=AsientoServicio.Tipo.SEMICAMA if numero <= mitad else AsientoServicio.Tipo.CAMA,
        )
        for numero in range(1, capacidad + 1)
    )


@receiver(post_save, sender=Venta)
def restaurar_stock_al_cancelar(sender, instance, **kwargs):
    """Libera los asientos de los boletos cuando una venta es cancelada."""
    # La cancelacion devuelve cada asiento al inventario disponible.
    if instance.estado != Venta.Estado.CANCELADO:
        return

    for boleto in instance.boletos.all():
        AsientoServicio.objects.filter(
            servicio=boleto.servicio,
            numero_asiento=boleto.numero_asiento,
        ).update(estado=AsientoServicio.Estado.DISPONIBLE)