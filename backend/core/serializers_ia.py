"""Serializadores de lectura para el asistente IA (fase 8)."""

from rest_framework import serializers

from .models import IAConversacion, IAMensaje


class IAMensajeLecturaSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(read_only=True)

    class Meta:
        model = IAMensaje
        fields = ["id", "rol", "contenido", "estado", "error", "created_at"]


class IAConversacionLecturaSerializer(serializers.ModelSerializer):
    ultimo_mensaje = serializers.CharField(read_only=True)
    mensajes = IAMensajeLecturaSerializer(many=True, read_only=True)

    class Meta:
        model = IAConversacion
        fields = ["id", "titulo", "estado", "ultimo_mensaje", "mensajes",
                  "created_at", "updated_at"]


class IAConversacionListaSerializer(serializers.ModelSerializer):
    ultimo_mensaje = serializers.CharField(read_only=True)

    class Meta:
        model = IAConversacion
        fields = ["id", "titulo", "estado", "ultimo_mensaje", "created_at"]


class IAChatInputSerializer(serializers.Serializer):
    conversacion_id = serializers.UUIDField(required=False, allow_null=True)
    mensaje = serializers.CharField(trim_whitespace=False)
