"""Serializadores de lectura para el asistente IA (fase 8)."""

from rest_framework import serializers

from .models import IAConversacion, IAMensaje


class IAMensajeLecturaSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(read_only=True)

    class Meta:
        model = IAMensaje
        fields = ["id", "rol", "contenido", "estado", "error", "created_at"]


class IAConversacionLecturaSerializer(serializers.ModelSerializer):
    ultimo_mensaje = serializers.SerializerMethodField()
    mensajes = IAMensajeLecturaSerializer(many=True, read_only=True)

    class Meta:
        model = IAConversacion
        fields = ["id", "titulo", "estado", "ultimo_mensaje", "mensajes",
                  "created_at", "updated_at"]

    def get_ultimo_mensaje(self, conversacion):
        # Usa la anotacion del queryset (Fase 6) si existe; si no, la
        # propiedad del modelo (un solo registro).
        return getattr(conversacion, "_ultimo_mensaje", None) or conversacion.ultimo_mensaje


class IAConversacionListaSerializer(serializers.ModelSerializer):
    ultimo_mensaje = serializers.SerializerMethodField()

    class Meta:
        model = IAConversacion
        fields = ["id", "titulo", "estado", "ultimo_mensaje", "created_at"]

    def get_ultimo_mensaje(self, conversacion):
        return getattr(conversacion, "_ultimo_mensaje", None) or conversacion.ultimo_mensaje


class IAChatInputSerializer(serializers.Serializer):
    conversacion_id = serializers.UUIDField(required=False, allow_null=True)
    mensaje = serializers.CharField(trim_whitespace=False)
