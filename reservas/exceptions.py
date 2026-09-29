from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken

def custom_exception_handler(exc, context):
    # Llama al manejador de excepciones original de Django REST Framework
    response = exception_handler(exc, context)

    # Si la excepción es por un token inválido o expirado, cambiamos el texto
    if isinstance(exc, InvalidToken) and response is not None:
        response.data['detail'] = 'Su sesión ha expirado. Por favor, inicie sesión nuevamente.'
        # Opcional: si quieres eliminar otras claves en inglés que manda la librería
        if 'messages' in response.data:
            del response.data['messages']

    return response