# Proyecto 4: Reservas de Pasajes de Buses Interurbanos

API REST desarrollada con Django y Django REST Framework para gestionar ciudades, terminales, rutas, buses, servicios y asientos de servicios interurbanos. El modelo separa cada hecho en su propia entidad y utiliza claves primarias autoincrementales para mantener la Tercera Forma Normal (3FN).

## Requisitos

- Python 3.11 o superior
- PostgreSQL 14 o superior
- Git

## Clonar e instalar

1. Clona el repositorio desde GitHub y entra en la carpeta del proyecto:

   ```bash
   git clone https://github.com/USUARIO/NOMBRE-DEL-REPOSITORIO.git
   cd NOMBRE-DEL-REPOSITORIO
   ```

2. Crea el entorno virtual:

   ```bash
   python -m venv venv
   ```

3. Activa el entorno virtual.

   En Windows PowerShell:

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

   En Windows CMD:

   ```bat
   venv\Scripts\activate
   ```

   En macOS o Linux:

   ```bash
   source venv/bin/activate
   ```

4. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

5. Configura las variables de entorno de PostgreSQL. Puedes definirlas en el sistema o en la sesión actual de la terminal (el proyecto las lee con `os.getenv`):

   ```env
   POSTGRES_DB=reservas_buses
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=tu_clave
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   DJANGO_SECRET_KEY=clave-local-de-desarrollo
   DJANGO_DEBUG=True
   ```

6. Crea las migraciones y aplícalas:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. Ejecuta las verificaciones y levanta el servidor:

   ```bash
   python manage.py check
   python manage.py runserver
   ```

## Documentación de la API

Con el servidor ejecutándose, visita:

- Swagger UI: http://127.0.0.1:8000/api/docs/
- Esquema OpenAPI: http://127.0.0.1:8000/api/schema/

## Estructura principal

- `config/settings.py`: configuración Django y conexión parametrizada a PostgreSQL.
- `config/urls.py`: rutas principales y documentación OpenAPI.
- `reservas/models.py`: modelo de negocio normalizado en 3FN.
- `requirements.txt`: dependencias del proyecto.
