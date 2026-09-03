"""Vistas de la API del asistente IA (fase 8).

Accesible para personal interno (ADMINISTRADOR o EMPLEADO) via EsPersonal.

Endpoints montados en /api/ia/:
  * GET  /conversaciones/            lista sesiones del usuario
  * POST /conversaciones/            crea una sesion nueva
  * GET  /conversaciones/<uuid:id>/  detalle con sus mensajes
  * POST /chat/                      envia un mensaje y recibe la respuesta
"""

import logging

from django.db.models import OuterRef, Subquery
from django.db.models import TextField
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import ActividadUsuario
from cuentas.permissions import EsPersonal

from . import ia_engine
from .models import IAConversacion, IAMensaje
from .serializers_ia import (IAChatInputSerializer, IAConversacionLecturaSerializer,
                             IAConversacionListaSerializer)

logger = logging.getLogger(__name__)


def _obtener_empresa(request):
    return request.user.perfil.empresa


def _ultimo_mensaje_anotacion():
    """Fase 6: ultimo mensaje via Subquery para no hacer un SELECT por sesion."""
    ultimo = (IAMensaje.objects.filter(conversacion=OuterRef("pk"))
              .order_by("-created_at").values("contenido")[:1])
    return Subquery(ultimo, output_field=TextField())


def _serializar_conversacion(conversacion):
    return IAConversacionLecturaSerializer(conversacion).data


class IAConversacionesView(APIView):
    """Lista y crea sesiones de conversacion del asistente."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        # Lista acotada (nunca ilimitada): el orden ya es -created_at por
        # Meta.ordering del modelo.
        conversaciones = (IAConversacion.objects.filter(usuario=request.user)
                          .annotate(_ultimo_mensaje=_ultimo_mensaje_anotacion())[:100])
        datos = IAConversacionListaSerializer(
            conversaciones, many=True).data
        return Response({"resultados": datos})

    def post(self, request):
        titulo = (request.data.get("titulo") or "").strip()[:120]
        conversacion = IAConversacion.objects.create(
            usuario=request.user, titulo=titulo)
        return Response(_serializar_conversacion(conversacion),
                        status=status.HTTP_201_CREATED)


class IAConversacionDetalleView(APIView):
    """Detalle de una sesion con todos sus mensajes."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get_object(self, request, id):
        return (IAConversacion.objects.filter(usuario=request.user, id=id)
                .annotate(_ultimo_mensaje=_ultimo_mensaje_anotacion())
                .prefetch_related("mensajes").first())

    def get(self, request, id):
        conversacion = self.get_object(request, id)
        if not conversacion:
            return Response(
                {"codigo": "NO_ENCONTRADO",
                 "detalle": "La conversacion no existe o no te pertenece."},
                status=status.HTTP_404_NOT_FOUND)
        return Response(_serializar_conversacion(conversacion))


class IAChatView(APIView):
    """Envia un mensaje del usuario y obtiene la respuesta del asistente.

    Flujo:
      1. Crea (o reutiliza) la conversacion; registra el mensaje del usuario,
         auditando IA_CONSULTA. Si la peticion es un reintento (el ultimo
         mensaje es del usuario, igual al entrante y sin respuesta del
         asistente), no duplica el mensaje.
      2. Arma el contexto de negocio de la empresa y el historial.
      3. Llama al motor. Si responde, guarda el mensaje del asistente
         (estado ok) y audita IA_RESPUESTA.
      4. Si el motor falla (timeout/error), conserva la conversacion con el
         mensaje del usuario para que se pueda reintentar y devuelve 502.
    """
    permission_classes = [IsAuthenticated, EsPersonal]

    def post(self, request):
        # Rate-limit por usuario antes de tocar la conversacion ni el motor.
        if not ia_engine.verificar_rate_limit(request.user):
            return Response(
                {"codigo": "IA_DEMASIADAS_PETICIONES",
                 "detalle": "Has superado el numero de consultas permitido. "
                            "Espera un momento e intenta de nuevo."},
                status=status.HTTP_429_TOO_MANY_REQUESTS)

        entrada = IAChatInputSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos del mensaje.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        datos = entrada.validated_data
        mensaje = (datos.get("mensaje") or "").strip()
        if not mensaje:
            return Response(
                {"codigo": "MENSAJE_VACIO",
                 "detalle": "Escribe un mensaje para consultar al asistente."},
                status=status.HTTP_400_BAD_REQUEST)

        empresa = _obtener_empresa(request)
        usuario = request.user

        conversacion = self._obtener_conversacion(usuario, datos)
        self._guardar_mensaje_usuario(conversacion, mensaje)

        historial = [(m.rol, m.contenido)
                     for m in conversacion.mensajes.order_by('created_at')]

        contexto = ia_engine.construir_contexto(empresa, request)

        try:
            texto = ia_engine.llamar_proveedor(contexto, historial, mensaje)
        except ia_engine.IAError as exc:
            logger.warning("Fallo el motor IA (usuario %s): %s",
                           usuario.email, exc)
            return Response(
                {"codigo": "IA_NO_DISPONIBLE",
                 "detalle": "El asistente no pudo responder en este momento. "
                            "Tu mensaje quedo guardado y puedes reintentar.",
                 "conversacion": _serializar_conversacion(conversacion)},
                status=status.HTTP_502_BAD_GATEWAY)

        IAMensaje.objects.create(conversacion=conversacion,
                                 rol="asistente", contenido=texto)
        ActividadUsuario.registrar(usuario=usuario, accion="IA_RESPUESTA",
                                   detalle=f"Respuesta a conversacion {conversacion.pk}")

        return Response({
            "respuesta": texto,
            "contexto": contexto.a_texto(),
            "conversacion": _serializar_conversacion(conversacion),
        })

    @staticmethod
    def _obtener_conversacion(usuario, datos):
        conversacion_id = datos.get("conversacion_id")
        if conversacion_id:
            conversacion = IAConversacion.objects.filter(
                usuario=usuario, id=conversacion_id).first()
            if conversacion:
                return conversacion
        return IAConversacion.objects.create(usuario=usuario, titulo="")

    @staticmethod
    def _guardar_mensaje_usuario(conversacion, mensaje):
        """Guarda el mensaje del usuario sin duplicarlo en un reintento.

        Un reintento se detecta cuando el ultimo mensaje es del usuario, con
        el mismo contenido y aun sin respuesta del asistente.
        """
        ultimo = conversacion.mensajes.order_by('-created_at').first()
        if (ultimo and ultimo.rol == "usuario"
                and ultimo.contenido == mensaje
                and not conversacion.mensajes.filter(
                    rol="asistente", created_at__gt=ultimo.created_at).exists()):
            return  # reintento: no duplicar
        IAMensaje.objects.create(conversacion=conversacion,
                                 rol="usuario", contenido=mensaje)
        user = conversacion.usuario
        ActividadUsuario.registrar(usuario=user, accion="IA_CONSULTA",
                                   detalle=f"Conversacion {conversacion.pk}")
