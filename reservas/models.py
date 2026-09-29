from django.core.validators import MinValueValidator
from django.conf import settings
from django.db import models


class Ciudad(models.Model):
    """Catalogo de ciudades; evita repetir el nombre en cada terminal."""

    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=120, unique=True)

    class Meta:
        """Configura orden y nombres administrativos del modelo Ciudad."""
        ordering = ["nombre"]
        verbose_name = "ciudad"
        verbose_name_plural = "ciudades"

    def __str__(self):
        """Retorna el nombre de la ciudad para representarla como texto."""
        return self.nombre


class Terminal(models.Model):
    """Terminal perteneciente a una ciudad, con su propia identidad."""

    id = models.BigAutoField(primary_key=True)
    ciudad = models.ForeignKey(
        Ciudad,
        on_delete=models.PROTECT,
        related_name="terminales",
    )
    nombre = models.CharField(max_length=150)

    class Meta:
        """Configura unicidad, orden y nombres del modelo Terminal."""
        constraints = [
            models.UniqueConstraint(
                fields=["ciudad", "nombre"],
                name="uq_terminal_nombre_ciudad",
            ),
        ]
        ordering = ["ciudad__nombre", "nombre"]
        verbose_name = "terminal"
        verbose_name_plural = "terminales"

    def __str__(self):
        """Retorna el nombre del terminal junto con su ciudad."""
        return f"{self.nombre} ({self.ciudad.nombre})"


class Ruta(models.Model):
    """Trayecto entre dos terminales; las ciudades se obtienen por sus FKs."""

    id = models.BigAutoField(primary_key=True)
    origen = models.ForeignKey(
        Terminal,
        on_delete=models.PROTECT,
        related_name="rutas_origen",
    )
    destino = models.ForeignKey(
        Terminal,
        on_delete=models.PROTECT,
        related_name="rutas_destino",
    )
    distancia_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )

    class Meta:
        """Configura la restriccion de origen y destino de una Ruta."""
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(origen=models.F("destino")),
                name="ck_ruta_origen_distinto_destino",
            ),
        ]
        verbose_name = "ruta"
        verbose_name_plural = "rutas"

    def __str__(self):
        """Retorna una descripcion textual del trayecto de la ruta."""
        return f"{self.origen} -> {self.destino}"


class Bus(models.Model):
    """Vehiculo identificado por patente y con capacidad propia."""

    id = models.BigAutoField(primary_key=True)
    patente = models.CharField(max_length=10, unique=True)
    capacidad_asientos = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )

    class Meta:
        """Configura orden y nombres administrativos del modelo Bus."""
        ordering = ["patente"]
        verbose_name = "bus"
        verbose_name_plural = "buses"

    def __str__(self):
        """Retorna la patente del bus como identificador textual."""
        return self.patente


class Servicio(models.Model):
    """Salida concreta que combina una ruta, un bus, fecha y tarifas."""

    id = models.BigAutoField(primary_key=True)
    ruta = models.ForeignKey(
        Ruta,
        on_delete=models.PROTECT,
        related_name="servicios",
    )
    bus = models.ForeignKey(
        Bus,
        on_delete=models.PROTECT,
        related_name="servicios",
    )
    fecha_hora_salida = models.DateTimeField()
    tarifa_semicama = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    tarifa_cama = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        """Configura unicidad, orden y nombres del modelo Servicio."""
        constraints = [
            models.UniqueConstraint(
                fields=["ruta", "bus", "fecha_hora_salida"],
                name="uq_servicio_ruta_bus_salida",
            ),
        ]
        ordering = ["fecha_hora_salida"]
        verbose_name = "servicio"
        verbose_name_plural = "servicios"

    def __str__(self):
        """Retorna la ruta y fecha de salida del servicio."""
        return f"{self.ruta} - {self.fecha_hora_salida:%Y-%m-%d %H:%M}"


class AsientoServicio(models.Model):
    """Estado de un asiento para un servicio especifico, no del bus global."""

    class Tipo(models.TextChoices):
        """Define las categorias de comodidad disponibles en el bus."""
        SEMICAMA = "SEMICAMA", "Semicama"
        CAMA = "CAMA", "Cama"

    class Estado(models.TextChoices):
        """Define los estados de disponibilidad de un asiento."""
        DISPONIBLE = "DISPONIBLE", "Disponible"
        OCUPADO = "OCUPADO", "Ocupado"

    id = models.BigAutoField(primary_key=True)
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        related_name="asientos",
    )
    numero_asiento = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )
    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.DISPONIBLE,
    )

    class Meta:
        """Configura unicidad, orden y nombres de los asientos."""
        constraints = [
            models.UniqueConstraint(
                fields=["servicio", "numero_asiento"],
                name="uq_asiento_numero_servicio",
            ),
        ]
        ordering = ["servicio", "numero_asiento"]
        verbose_name = "asiento de servicio"
        verbose_name_plural = "asientos de servicio"

    def __str__(self):
        """Retorna el numero de asiento y el servicio al que pertenece."""
        return f"Asiento {self.numero_asiento} - Servicio {self.servicio_id}"


class Pasajero(models.Model):
    """Datos del pasajero aislados del asiento para evitar duplicacion y usar RUT no-PK."""

    id = models.BigAutoField(primary_key=True)
    rut = models.CharField(max_length=12, unique=True)
    nombre_completo = models.CharField(max_length=200)

    class Meta:
        """Configura orden y nombres administrativos del pasajero."""
        ordering = ["nombre_completo"]
        verbose_name = "pasajero"
        verbose_name_plural = "pasajeros"

    def __str__(self):
        """Retorna el nombre completo del pasajero."""
        return self.nombre_completo


class CarroPasajes(models.Model):
    """Representa el carro de compras asociado unicamente a un usuario."""
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carro_pasajes",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Retorna una descripcion del propietario del carro."""
        return f"Carro de {self.usuario.get_username()}"


class ItemCarro(models.Model):
    """Representa un asiento y pasajero temporalmente guardados en un carro."""
    carro = models.ForeignKey(
        CarroPasajes,
        on_delete=models.CASCADE,
        related_name="items",
    )
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.PROTECT,
        related_name="items_carro",
    )
    numero_asiento = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )
    pasajero_nombre = models.CharField(max_length=200)
    pasajero_rut = models.CharField(max_length=12)

    class Meta:
        """Configura unicidad y orden de items dentro del carro."""
        constraints = [
            models.UniqueConstraint(
                fields=["carro", "servicio", "numero_asiento"],
                name="uq_item_asiento_carro",
            ),
        ]
        ordering = ["id"]

    def __str__(self):
        """Retorna el asiento y servicio contenidos en el item."""
        return f"Asiento {self.numero_asiento} del servicio {self.servicio_id}"


class Venta(models.Model):
    """Representa una compra y su estado dentro del proceso de pago."""
    class Estado(models.TextChoices):
        """Define los estados posibles de una venta."""
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        CANCELADO = "CANCELADO", "Cancelado"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ventas",
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        """Configura el orden cronologico inverso de las ventas."""
        ordering = ["-creado_en"]


class Boleto(models.Model):
    """Representa el pasaje emitido para un asiento de un servicio."""
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="boletos",
    )
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.PROTECT,
        related_name="boletos",
    )
    numero_asiento = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )
    pasajero_nombre = models.CharField(max_length=200)
    pasajero_rut = models.CharField(max_length=12)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        """Configura unicidad y orden de los boletos emitidos."""
        constraints = [
            models.UniqueConstraint(
                fields=["venta", "servicio", "numero_asiento"],
                name="uq_boleto_asiento_venta",
            ),
        ]
        ordering = ["id"]
