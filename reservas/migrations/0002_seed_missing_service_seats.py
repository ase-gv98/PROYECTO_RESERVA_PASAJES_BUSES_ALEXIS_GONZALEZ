from django.db import migrations


def seed_missing_service_seats(apps, schema_editor):
    """Completa los asientos faltantes de cada servicio segun su bus."""
    # Se usan modelos historicos para que la migracion sea reproducible.
    Servicio = apps.get_model("reservas", "Servicio")
    AsientoServicio = apps.get_model("reservas", "AsientoServicio")
    Bus = apps.get_model("reservas", "Bus")

    for servicio in Servicio.objects.all().iterator():
        capacidad = Bus.objects.get(pk=servicio.bus_id).capacidad_asientos
        existentes = set(
            AsientoServicio.objects.filter(servicio_id=servicio.pk).values_list(
                "numero_asiento", flat=True
            )
        )
        mitad = capacidad // 2
        faltantes = [
            AsientoServicio(
                servicio_id=servicio.pk,
                numero_asiento=numero,
                tipo="SEMICAMA" if numero <= mitad else "CAMA",
            )
            for numero in range(1, capacidad + 1)
            if numero not in existentes
        ]
        AsientoServicio.objects.bulk_create(faltantes)


def remove_seeded_service_seats(apps, schema_editor):
    """Recibe el contexto de migracion y conserva los datos al revertir."""
    # Seat data must not be removed when rolling back application migrations.
    pass


class Migration(migrations.Migration):
    """Declara la migracion que completa asientos de servicios existentes."""

    dependencies = [
        ("reservas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_missing_service_seats, remove_seeded_service_seats),
    ]
