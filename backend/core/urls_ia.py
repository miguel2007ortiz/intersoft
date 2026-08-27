"""Rutas del asistente IA (fase 8): personal interno (ADMIN y EMPLEADO).
Se monta en intersoft/urls.py bajo 'api/' -> /api/ia/conversaciones/,
/api/ia/chat/."""

from django.urls import path

from . import views_ia

urlpatterns = [
    path("ia/conversaciones/", views_ia.IAConversacionesView.as_view()),
    path("ia/conversaciones/<uuid:id>/", views_ia.IAConversacionDetalleView.as_view()),
    path("ia/chat/", views_ia.IAChatView.as_view()),
]
