from rest_framework.permissions import BasePermission


def get_user_role(request):
    """Recibe una peticion y retorna el rol obtenido del token o usuario."""
    # Primero se consulta el claim JWT y luego los datos persistidos del usuario.
    token_role = request.auth.get("role") if request.auth else None
    if token_role in {"PASAJERO", "ADMIN_FLOTA"}:
        return token_role

    user_role = getattr(request.user, "role", None)
    if user_role in {"PASAJERO", "ADMIN_FLOTA"}:
        return user_role
    return "ADMIN_FLOTA" if request.user.is_staff else "PASAJERO"


class IsPasajero(BasePermission):
    """Permite operaciones exclusivamente a usuarios con rol PASAJERO."""

    message = "Esta operacion requiere el rol PASAJERO."

    def has_permission(self, request, view):
        """Recibe request y vista, y retorna si el pasajero puede continuar."""
        return bool(
            request.user
            and request.user.is_authenticated
            and get_user_role(request) == "PASAJERO"
        )


class IsAdminFlota(BasePermission):
    """Permite operaciones a personal de flota o usuarios administrativos."""

    message = "Esta operacion requiere el rol ADMIN_FLOTA."

    def has_permission(self, request, view):
        """Recibe request y vista, y retorna si el usuario es administrador."""
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_staff
                or get_user_role(request) == "ADMIN_FLOTA"
            )
        )