from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("reservas.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui-schema"),
    path("", views.buscar_pasajes_view, name="buscar-pasajes"),
    path("carro/", views.carro_view, name="carro"),
    path("mis-boletos/", views.mis_boletos_view, name="mis-boletos"),
    path("logout/", views.logout_view, name="logout"),
    path("admin-dashboard/", views.admin_dashboard_view, name="admin-dashboard"),
    re_path(r"^.*$", views.custom_404_view),
]
