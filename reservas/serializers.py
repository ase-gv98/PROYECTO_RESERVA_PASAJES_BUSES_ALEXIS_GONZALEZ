from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import AsientoServicio, Boleto, CarroPasajes, ItemCarro, Servicio, Venta


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Construye tokens JWT con rol e identidad basicos del usuario."""

    @classmethod
    def get_token(cls, user):
        """Recibe un usuario y retorna su token JWT con claims personalizados."""
        token = super().get_token(user)
        role = getattr(user, "role", None)
        if role not in {"PASAJERO", "ADMIN_FLOTA"}:
            role = "ADMIN_FLOTA" if user.is_staff else "PASAJERO"
        token["role"] = role
        token["username"] = user.get_username()
        token["email"] = user.email
        token["is_superuser"] = user.is_superuser
        token["is_pasajero"] = user.groups.filter(name="PASAJERO").exists()
        return token


class CustomTokenObtainPairSerializerResponse(CustomTokenObtainPairSerializer):
    """Agrega informacion del usuario a la respuesta de autenticacion."""

    def validate(self, attrs):
        """Valida credenciales y retorna tokens junto con datos de rol."""
        data = super().validate(attrs)
        token = self.get_token(self.user)
        data["role"] = token["role"]
        data["username"] = self.user.get_username()
        data["email"] = self.user.email
        data["is_superuser"] = self.user.is_superuser
        data["is_pasajero"] = self.user.groups.filter(name="PASAJERO").exists()
        return data


class AsientoServicioSerializer(serializers.ModelSerializer):
    """Serializa identificador, tipo y estado de un asiento."""

    class Meta:
        """Declara los campos expuestos para un asiento."""
        model = AsientoServicio
        fields = ["id", "numero_asiento", "tipo", "estado"]


class ServicioSerializer(serializers.ModelSerializer):
    """Serializa un servicio completo, incluidos sus asientos."""

    asientos = AsientoServicioSerializer(many=True, read_only=True)

    class Meta:
        """Declara los campos completos de un servicio."""
        model = Servicio
        fields = [
            "id",
            "ruta",
            "bus",
            "fecha_hora_salida",
            "tarifa_semicama",
            "tarifa_cama",
            "asientos",
        ]


class ServicioResumenSerializer(serializers.ModelSerializer):
    """Serializa los datos resumidos usados por el catalogo de viajes."""

    origen = serializers.CharField(source="ruta.origen.ciudad.nombre", read_only=True)
    destino = serializers.CharField(source="ruta.destino.ciudad.nombre", read_only=True)

    class Meta:
        """Declara los campos resumidos del catalogo de servicios."""
        model = Servicio
        fields = [
            "id",
            "origen",
            "destino",
            "fecha_hora_salida",
            "tarifa_semicama",
            "tarifa_cama",
        ]


class ItemCarroSerializer(serializers.ModelSerializer):
    """Valida y serializa items de pasajeros dentro del carro."""

    class Meta:
        """Declara los campos aceptados para un item del carro."""
        model = ItemCarro
        fields = [
            "id",
            "servicio",
            "numero_asiento",
            "pasajero_nombre",
            "pasajero_rut",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        """Valida que el asiento exista y no este ocupado."""
        asiento = AsientoServicio.objects.filter(
            servicio=attrs["servicio"],
            numero_asiento=attrs["numero_asiento"],
        ).first()
        if asiento is None:
            raise serializers.ValidationError("El asiento no existe para este servicio.")
        if asiento.estado == AsientoServicio.Estado.OCUPADO:
            raise serializers.ValidationError("El asiento ya esta ocupado.")
        return attrs

    def create(self, validated_data):
        """Crea el item asociado al carro entregado en el contexto."""
        return ItemCarro.objects.create(
            carro=self.context["carro"],
            **validated_data,
        )


class CarroPasajesSerializer(serializers.ModelSerializer):
    """Serializa un carro junto con sus items de pasajes."""

    items = ItemCarroSerializer(many=True, read_only=True)

    class Meta:
        """Declara los campos de salida de un carro."""
        model = CarroPasajes
        fields = ["id", "items", "creado_en", "actualizado_en"]


class BoletoSerializer(serializers.ModelSerializer):
    """Serializa los datos publicos de un boleto emitido."""

    class Meta:
        """Declara los campos publicos de un boleto."""
        model = Boleto
        fields = [
            "id",
            "servicio",
            "numero_asiento",
            "pasajero_nombre",
            "pasajero_rut",
            "precio",
        ]


class CambiarPasajeSerializer(serializers.Serializer):
    """Valida el identificador del nuevo asiento solicitado."""

    nuevo_asiento_id = serializers.IntegerField(min_value=1)


class VentaSerializer(serializers.ModelSerializer):
    """Serializa una venta y la lista de boletos asociados."""

    boletos = BoletoSerializer(many=True, read_only=True)

    class Meta:
        """Declara los campos de salida de una venta."""
        model = Venta
        fields = ["id", "estado", "total", "creado_en", "actualizado_en", "boletos"]