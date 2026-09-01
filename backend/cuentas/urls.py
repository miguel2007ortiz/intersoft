from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ConfirmarRecuperacionView, EmailDisponibleView, LoginView,
    RegistroEmpresaView, SolicitarRecuperacionView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("registro/", RegistroEmpresaView.as_view(), name="auth-registro"),
    path("email-disponible/", EmailDisponibleView.as_view(), name="auth-email-disponible"),
    path("password-reset/", SolicitarRecuperacionView.as_view(), name="auth-password-reset"),
    path("password-reset/confirmar/", ConfirmarRecuperacionView.as_view(), name="auth-password-reset-confirmar"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
]
