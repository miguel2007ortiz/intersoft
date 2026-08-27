from django.urls import path
from .views import (
    ConfirmarRecuperacionView, EmailDisponibleView, LoginView,
    RegistroCompradorView, RegistroEmpresaView, SolicitarRecuperacionView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("registro/", RegistroEmpresaView.as_view(), name="auth-registro"),
    path("registro/comprador/", RegistroCompradorView.as_view(), name="auth-registro-comprador"),
    path("email-disponible/", EmailDisponibleView.as_view(), name="auth-email-disponible"),
    path("password-reset/", SolicitarRecuperacionView.as_view(), name="auth-password-reset"),
    path("password-reset/confirmar/", ConfirmarRecuperacionView.as_view(), name="auth-password-reset-confirmar"),
]
