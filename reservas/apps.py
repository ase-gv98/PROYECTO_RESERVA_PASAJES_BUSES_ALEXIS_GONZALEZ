from django.apps import AppConfig


class ReservasConfig(AppConfig):
    """Configura la aplicacion reservas y registra sus señales."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "reservas"

    def ready(self):
        """Carga el modulo de señales cuando Django termina de inicializar apps."""
        from . import signals  # noqa: F401
