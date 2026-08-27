"""Serializers de la fase 9: camaras y centro de notificaciones.

Todo queda restringido al ADMINISTRADOR en las vistas. Respecto a
`Notificacion`, se conserva `leida` por compatibilidad: `leida=True` equivale
a `estado != 'nueva'`.
"""

from rest_framework import serializers

from .models import Camara, Notificacion


# ------------------------------ Camaras ------------------------------------

class CamaraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camara
        fields = ["id", "nombre", "ubicacion", "url_stream", "activa",
                  "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate_nombre(self, valor):
        valor = (valor or '').strip()
        if not valor:
            raise serializers.ValidationError("El nombre de la camara es obligatorio.")
        return valor


# ---------------------------- Notificaciones -------------------------------

class NotificacionLecturaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    canal_display = serializers.CharField(source='get_canal_display', read_only=True)

    class Meta:
        model = Notificacion
        fields = ["id", "tipo", "tipo_display", "estado", "estado_display",
                  "canal", "canal_display", "mensaje", "leida", "created_at"]

    @classmethod
    def activas(cls, qs):
        """Solo notificaciones nuevas/revisadas (sin resolver), desc por fecha."""
        return qs.exclude(estado='resuelta').order_by('-created_at')
