from django.urls import path
from .views import (
    CambiarPasswordView, ConfirmarRecuperacionView, EmailDisponibleView, LoginView,
    MeView, RegistroCompradorView, RegistroEmpresaView, SolicitarRecuperacionView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("cambiar-password/", CambiarPasswordView.as_view(), name="auth-cambiar-password"),
    path("registro/", RegistroEmpresaView.as_view(), name="auth-registro"),
    path("registro/comprador/", RegistroCompradorView.as_view(), name="auth-registro-comprador"),
    path("email-disponible/", EmailDisponibleView.as_view(), name="auth-email-disponible"),
    path("password-reset/", SolicitarRecuperacionView.as_view(), name="auth-password-reset"),
    path("password-reset/confirmar/", ConfirmarRecuperacionView.as_view(), name="auth-password-reset-confirmar"),
]
