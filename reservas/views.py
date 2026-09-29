from datetime import date

from django.db import transaction
from django.contrib.auth import login as django_login
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from .filters import ServicioFilter
from .models import (
    AsientoServicio,
    Boleto,
    CarroPasajes,
    ItemCarro,
    Servicio,
    Venta,
)
from .permissions import IsAdminFlota, IsPasajero
from .serializers import (
    AsientoServicioSerializer,
    BoletoSerializer,
    CambiarPasajeSerializer,
    CarroPasajesSerializer,
    CustomTokenObtainPairSerializerResponse,
    ItemCarroSerializer,
    ServicioResumenSerializer,
    ServicioSerializer,
    VentaSerializer,
)
from django.contrib.auth.models import User, Group  # Asegúrate de tener Group aquí
from rest_framework import generics, status, viewsets # Añade generics aquí

class CustomTokenObtainPairView(TokenObtainPairView):
    """Autentica usuarios, entrega JWT y crea la sesion Django."""

    serializer_class = CustomTokenObtainPairSerializerResponse

    def post(self, request, *args, **kwargs):
        """Recibe credenciales y retorna la respuesta estandar de tokens."""
        response = super().post(request, *args, **kwargs)
        # Se crea la sesion Django para que las vistas web protegidas reconozcan al administrador.
        if response.status_code == status.HTTP_200_OK:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            django_login(request, serializer.user)
        return response


class ServicioSearchViewSet(viewsets.ReadOnlyModelViewSet):
    """Expone servicios de solo lectura para el buscador publico."""

    queryset = Servicio.objects.select_related(
        "ruta__origen__ciudad", "ruta__destino__ciudad", "bus"
    ).prefetch_related("asientos")
    serializer_class = ServicioResumenSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServicioFilter


class ServicioAdminViewSet(viewsets.ModelViewSet):
    """Administra servicios y permite listar viajes para el catalogo."""

    queryset = Servicio.objects.select_related(
        "ruta__origen__ciudad",
        "ruta__destino__ciudad",
        "bus",
    )
    serializer_class = ServicioSerializer
    permission_classes = [IsAdminFlota]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServicioFilter

    def get_queryset(self):
        """Retorna servicios filtrados por origen, destino y fecha recibidos por GET."""
        queryset = super().get_queryset()
        params = self.request.query_params

        # Cada filtro se aplica solo cuando su parametro contiene un valor.
        origen = params.get("origen", "").strip()
        if origen:
            queryset = queryset.filter(
                ruta__origen__ciudad__nombre__iexact=origen,
            )

        destino = params.get("destino", "").strip()
        if destino:
            queryset = queryset.filter(
                ruta__destino__ciudad__nombre__iexact=destino,
            )

        fecha = (params.get("fecha") or params.get("fecha_salida") or "").strip()
        if fecha:
            try:
                fecha_filtro = date.fromisoformat(fecha)
            except ValueError:
                fecha_filtro = None

            if fecha_filtro:
                queryset = queryset.filter(
                    fecha_hora_salida__date=fecha_filtro,
                )

        return queryset.distinct()

    def get_permissions(self):
        """Retorna permisos publicos para lecturas y administrativos para cambios."""
        if self.request.method in {"GET", "HEAD", "OPTIONS"}:
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        """Selecciona resumen para lecturas y serializer completo para escritura."""
        if self.action in {"list", "retrieve"}:
            return ServicioResumenSerializer
        return ServicioSerializer


class AsientosServicioView(APIView):
    """Entrega la disponibilidad de asientos de un servicio especifico."""

    permission_classes = [AllowAny]

    def get(self, request, servicio_id):
        """Recibe el ID del servicio y retorna sus asientos serializados."""
        asientos = AsientoServicio.objects.filter(servicio_id=servicio_id)
        return Response(AsientoServicioSerializer(asientos, many=True).data)


class CarroPasajesView(APIView):
    """Gestiona consulta, alta y eliminacion de items del carro del pasajero."""

    permission_classes = [IsPasajero]

    def get(self, request):
        """Retorna o crea el carro perteneciente al usuario autenticado."""
        carro, _ = CarroPasajes.objects.get_or_create(usuario=request.user)
        return Response(CarroPasajesSerializer(carro).data)

    @extend_schema(
        request=inline_serializer(
            name="AgregarAlCarro",
            fields={
                "servicio": serializers.IntegerField(),
                "numero_asiento": serializers.IntegerField(),
                "pasajero_nombre": serializers.CharField(),
                "pasajero_rut": serializers.CharField()
            }
        )
    )
    def post(self, request):
        """Valida y agrega un asiento al carro del usuario autenticado."""
        # El carro se obtiene por usuario para impedir mezclar compras entre clientes.
        carro, _ = CarroPasajes.objects.get_or_create(usuario=request.user)
        serializer = ItemCarroSerializer(
            data=request.data,
            context={"request": request, "carro": carro},
        )
        serializer.is_valid(raise_exception=True)
        try:
            item = serializer.save()
        except Exception as exc:
            if "uq_item_asiento_carro" not in str(exc):
                raise
            return Response(
                {"detail": "El asiento ya esta en el carro."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ItemCarroSerializer(item).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        """Elimina un item identificado por ID del carro del usuario actual."""
        item_id = request.data.get("item_id") or request.query_params.get("item_id")
        if not item_id:
            return Response(
                {"detail": "Debe indicar item_id para eliminar un item."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = ItemCarro.objects.filter(
            id=item_id,
            carro__usuario=request.user,
        ).delete()
        if not deleted:
            return Response({"detail": "Item no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MisBoletosView(APIView):
    """Lista boletos y reservas pertenecientes exclusivamente al usuario actual."""

    permission_classes = [IsPasajero]

    def get(self, request):
        """Retorna boletos del usuario y sus items actuales del carro."""
        # El filtro por venta__usuario limita la consulta al propietario autenticado.
        boletos = Boleto.objects.filter(
            venta__usuario=request.user,
        ).select_related("servicio", "venta")
        resultado = [
            {
                **BoletoSerializer(boleto).data,
                "estado": boleto.venta.estado,
            }
            for boleto in boletos
        ]

        carro = CarroPasajes.objects.filter(usuario=request.user).first()
        if carro:
            for item in carro.items.select_related("servicio"):
                asiento = AsientoServicio.objects.filter(
                    servicio=item.servicio,
                    numero_asiento=item.numero_asiento,
                ).first()
                precio = (
                    asiento.servicio.tarifa_cama
                    if asiento and asiento.tipo == AsientoServicio.Tipo.CAMA
                    else asiento.servicio.tarifa_semicama
                    if asiento
                    else 0
                )
                resultado.append(
                    {
                        "id": f"carro-{item.id}",
                        "servicio": item.servicio_id,
                        "numero_asiento": item.numero_asiento,
                        "pasajero_nombre": item.pasajero_nombre,
                        "pasajero_rut": item.pasajero_rut,
                        "precio": precio,
                        "estado": "EN_CARRO",
                    }
                )
        return Response(resultado)


class AnularPasajeView(APIView):
    """Anula un boleto propio y libera el asiento ocupado."""

    permission_classes = [IsPasajero]

    def post(self, request, boleto_id):
        """Recibe el ID del boleto y retorna el resultado de su anulacion."""
        # La transaccion protege el boleto, el asiento y la venta como una sola operacion.
        with transaction.atomic():
            boleto = (
                Boleto.objects.select_for_update()
                .select_related("venta", "servicio")
                .filter(id=boleto_id, venta__usuario=request.user)
                .first()
            )
            if boleto is None:
                return Response(
                    {"detail": "Boleto no encontrado."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if boleto.venta.estado != Venta.Estado.PAGADO:
                return Response(
                    {"detail": "Solo se pueden anular boletos pagados."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            asiento = AsientoServicio.objects.select_for_update().get(
                servicio=boleto.servicio,
                numero_asiento=boleto.numero_asiento,
            )
            # Liberar el asiento permite que vuelva a aparecer como disponible.
            asiento.estado = AsientoServicio.Estado.DISPONIBLE
            asiento.save(update_fields=["estado"])

            boleto.venta.estado = Venta.Estado.CANCELADO
            boleto.venta.save(update_fields=["estado", "actualizado_en"])

        return Response({
            "detail": "Pasaje anulado correctamente.",
            "boleto_id": boleto.id,
            "estado_venta": Venta.Estado.CANCELADO,
            "asiento_estado": AsientoServicio.Estado.DISPONIBLE,
        })


class CambiarPasajeView(APIView):
    """Cambia un boleto propio a otro asiento disponible del mismo servicio y bus."""

    permission_classes = [IsPasajero]

    def post(self, request, boleto_id):
        """Recibe boleto y nuevo asiento, y retorna el boleto actualizado."""
        input_serializer = CambiarPasajeSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        nuevo_asiento_id = input_serializer.validated_data["nuevo_asiento_id"]

        # La transaccion y los bloqueos de filas evitan reservar simultaneamente el mismo asiento.
        with transaction.atomic():
            boleto = (
                Boleto.objects.select_for_update()
                .select_related("venta", "servicio")
                .filter(id=boleto_id, venta__usuario=request.user)
                .first()
            )
            if boleto is None:
                return Response(
                    {"detail": "Boleto no encontrado."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if boleto.venta.estado != Venta.Estado.PAGADO:
                return Response(
                    {"detail": "Solo se pueden cambiar boletos pagados."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            nuevo_asiento = (
                AsientoServicio.objects.select_for_update()
                .select_related("servicio__bus")
                .filter(id=nuevo_asiento_id)
                .first()
            )
            if nuevo_asiento is None:
                return Response(
                    {"detail": "El nuevo asiento no existe."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if nuevo_asiento.servicio.bus_id != boleto.servicio.bus_id:
                return Response(
                    {"detail": "El nuevo asiento debe pertenecer al mismo bus."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if nuevo_asiento.servicio_id != boleto.servicio_id:
                return Response(
                    {"detail": "El nuevo asiento debe pertenecer al mismo servicio."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if nuevo_asiento.numero_asiento == boleto.numero_asiento:
                return Response(
                    {"detail": "Debes seleccionar un asiento diferente."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if nuevo_asiento.estado == AsientoServicio.Estado.OCUPADO:
                return Response(
                    {"detail": "El nuevo asiento ya esta ocupado."},
                    status=status.HTTP_409_CONFLICT,
                )

            # Se libera el asiento anterior y se ocupa el nuevo dentro de la misma transaccion.
            asiento_anterior = AsientoServicio.objects.select_for_update().get(
                servicio=boleto.servicio,
                numero_asiento=boleto.numero_asiento,
            )
            asiento_anterior.estado = AsientoServicio.Estado.DISPONIBLE
            asiento_anterior.save(update_fields=["estado"])

            nuevo_asiento.estado = AsientoServicio.Estado.OCUPADO
            nuevo_asiento.save(update_fields=["estado"])

            boleto.numero_asiento = nuevo_asiento.numero_asiento
            boleto.save(update_fields=["numero_asiento"])

        return Response({
            "detail": "Pasaje cambiado correctamente.",
            "boleto": BoletoSerializer(boleto).data,
        })


class CheckoutView(APIView):
    """Confirma el carro, emite boletos y marca sus asientos como ocupados."""

    permission_classes = [IsPasajero]

    def post(self, request):
        """Procesa el pago simulado y retorna la venta creada."""
        # El bloqueo atomico evita que otro checkout tome los mismos asientos.
        with transaction.atomic():
            carro = CarroPasajes.objects.select_for_update().filter(
                usuario=request.user,
            ).first()
            if carro is None:
                return Response(
                    {"detail": "El carro no existe."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            items = list(
                ItemCarro.objects.select_for_update()
                .select_related("servicio")
                .filter(carro=carro)
            )
            if not items:
                return Response(
                    {"detail": "El carro esta vacio."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            asientos = []
            for item in items:
                asiento = AsientoServicio.objects.select_for_update().filter(
                    servicio=item.servicio,
                    numero_asiento=item.numero_asiento,
                ).first()
                if asiento is None or asiento.estado == AsientoServicio.Estado.OCUPADO:
                    return Response(
                        {"detail": "Uno de los asientos ya no esta disponible."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                asientos.append(asiento)

            venta = Venta.objects.create(usuario=request.user)
            total = 0
            for item, asiento in zip(items, asientos):
                precio = (
                    item.servicio.tarifa_cama
                    if asiento.tipo == AsientoServicio.Tipo.CAMA
                    else item.servicio.tarifa_semicama
                )
                Boleto.objects.create(
                    venta=venta,
                    servicio=item.servicio,
                    numero_asiento=item.numero_asiento,
                    pasajero_nombre=item.pasajero_nombre,
                    pasajero_rut=item.pasajero_rut,
                    precio=precio,
                )
                total += precio
                asiento.estado = AsientoServicio.Estado.OCUPADO
                asiento.save(update_fields=["estado"])
            venta.total = total
            venta.estado = Venta.Estado.PAGADO
            venta.save(update_fields=["total", "estado", "actualizado_en"])
            ItemCarro.objects.filter(carro=carro).delete()

        return Response(VentaSerializer(venta).data, status=status.HTTP_201_CREATED)


class EstadoVentaView(APIView):
    """Permite al administrador actualizar el estado de una venta."""

    permission_classes = [IsAdminFlota]
    
    @extend_schema(
        request=inline_serializer(
            name="ActualizarEstadoVenta",
            fields={
                "estado": serializers.CharField()
            }
        )
    )
    def patch(self, request, venta_id):
        """Recibe un estado valido y retorna la venta actualizada."""
        nuevo_estado = request.data.get("estado")
        estados_validos = {Venta.Estado.PAGADO, Venta.Estado.CANCELADO}
        if nuevo_estado not in estados_validos:
            return Response(
                {"detail": "El estado debe ser PAGADO o CANCELADO."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # La venta y sus asientos se actualizan juntos para mantener consistencia.
            with transaction.atomic():
                venta = Venta.objects.select_for_update().get(id=venta_id)
                if venta.estado == Venta.Estado.PAGADO and nuevo_estado == Venta.Estado.PAGADO:
                    return Response(VentaSerializer(venta).data)
                if venta.estado == Venta.Estado.CANCELADO:
                    return Response(
                        {"detail": "Una venta cancelada no puede cambiar de estado."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if nuevo_estado == Venta.Estado.PAGADO:
                    boletos = list(venta.boletos.order_by("servicio_id", "numero_asiento"))
                    asientos = []
                    for boleto in boletos:
                        asiento = AsientoServicio.objects.select_for_update().filter(
                            servicio=boleto.servicio,
                            numero_asiento=boleto.numero_asiento,
                        ).first()
                        if asiento is None or asiento.estado == AsientoServicio.Estado.OCUPADO:
                            return Response(
                                {"detail": "Uno de los asientos ya no esta disponible."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                        asientos.append(asiento)
                    for asiento in asientos:
                        asiento.estado = AsientoServicio.Estado.OCUPADO
                        asiento.save(update_fields=["estado"])

                    for boleto in boletos:
                        ItemCarro.objects.filter(
                            carro__usuario=venta.usuario,
                            servicio=boleto.servicio,
                            numero_asiento=boleto.numero_asiento,
                        ).delete()

                venta.estado = nuevo_estado
                venta.save(update_fields=["estado", "actualizado_en"])
        except Venta.DoesNotExist:
            return Response({"detail": "Venta no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        return Response(VentaSerializer(venta).data)

class RegistroPasajeroView(generics.CreateAPIView):
    """Crea usuarios nuevos y los asigna al grupo PASAJERO."""

    queryset = User.objects.all()
    permission_classes = [AllowAny]

    @extend_schema(
        request=inline_serializer(
            name="RegistroPasajero",
            fields={
                "username": serializers.CharField(),
                "password": serializers.CharField(),
                "email": serializers.EmailField(required=False)
            }
        )
    )
    def post(self, request, *args, **kwargs):
        """Recibe usuario, contrasena y correo, y retorna confirmacion de registro."""
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", "")

        if not username or not password:
            return Response(
                {"detail": "Usuario y contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": "El usuario ya existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear el usuario de forma segura mediante el manager de Django.
        user = User.objects.create_user(username=username, password=password, email=email)
        
        # Asignarle automaticamente el grupo PASAJERO para aplicar sus permisos.
        grupo_pasajero, _ = Group.objects.get_or_create(name="PASAJERO")
        user.groups.add(grupo_pasajero)

        return Response(
            {"detail": f"Pasajero '{username}' registrado exitosamente."},
            status=status.HTTP_201_CREATED
        )