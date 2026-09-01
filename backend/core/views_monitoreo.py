"""API de la fase 9: monitoreo de camaras y centro de notificaciones.

Exclusivo del ADMINISTRADOR (EsAdministrador). Multi-tenancy: todo se filtra
por `request.user.perfil.empresa`.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import ActividadUsuario
from cuentas.permissions import EsAdministrador

from .models import Camara, Notificacion
from .serializers_monitoreo import (CamaraSerializer,
                                    NotificacionLecturaSerializer)
from .services import camaras as servicio_camaras


def _obtener_empresa(request):
    return request.user.perfil.empresa


# ------------------------------ Camaras -----------------------------------

class CamarasView(APIView):
    """Lista y crea camaras de la empresa (solo ADMINISTRADOR)."""
    permission_classes = [IsAuthenticated, EsAdministrador]
    # Alto a proposito: el frontend actual no tiene controles de pagina,
    # asi que una empresa real (decenas de camaras, no miles) sigue viendo
    # el listado completo en la pagina 1 sin cambios de UI.
    POR_PAGINA = 100

    def get(self, request):
        empresa = _obtener_empresa(request)
        qs = Camara.objects.filter(empresa=empresa, deleted_at__isnull=True)

        activas = request.query_params.get('activas')
        if activas is not None:
            if activas not in ('0', '1'):
                return Response(
                    {"codigo": "DATOS_INVALIDOS",
                     "detalle": "El filtro 'activas' solo acepta '0' o '1'."},
                    status=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(activa=(activas == '1'))

        qs = qs.order_by('nombre')
        total = qs.count()
        try:
            pagina = max(int(request.query_params.get('pagina', 1)), 1)
        except (TypeError, ValueError):
            pagina = 1
        inicio = (pagina - 1) * self.POR_PAGINA
        datos = CamaraSerializer(
            qs[inicio:inicio + self.POR_PAGINA], many=True).data
        return Response({
            "resultados": datos,
            "total": total,
            "pagina": pagina,
            "por_pagina": self.POR_PAGINA,
            "total_paginas": max((total + self.POR_PAGINA - 1) // self.POR_PAGINA, 1),
        })

    def post(self, request):
        empresa = _obtener_empresa(request)
        serializer = CamaraSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS", "errores": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)
        camara = serializer.save(empresa=empresa)
        ActividadUsuario.registrar(
            request.user, "CAMARA_CREADA", camara.nombre)
        return Response(CamaraSerializer(camara).data,
                        status=status.HTTP_201_CREATED)


class CamaraDetalleView(APIView):
    """Consulta, edita o desactiva una camara de la empresa."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def _get(self, request, id):
        return Camara.objects.filter(
            empresa=_obtener_empresa(request), id=id,
            deleted_at__isnull=True).first()

    def get(self, request, id):
        camara = self._get(request, id)
        if not camara:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(CamaraSerializer(camara).data)

    def patch(self, request, id):
        camara = self._get(request, id)
        if not camara:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CamaraSerializer(camara, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS", "errores": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        ActividadUsuario.registrar(
            request.user, "CAMARA_EDITADA", camara.nombre)
        return Response(CamaraSerializer(camara).data)

    def delete(self, request, id):
        camara = self._get(request, id)
        if not camara:
            return Response(status=status.HTTP_404_NOT_FOUND)
        camara.soft_delete()
        ActividadUsuario.registrar(
            request.user, "CAMARA_ELIMINADA", camara.nombre)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CamaraGrabacionView(APIView):
    """GET devuelve la grabacion historica de una camara por fecha/hora."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request, id):
        camara = Camara.objects.filter(
            empresa=_obtener_empresa(request), id=id,
            deleted_at__isnull=True).first()
        if not camara:
            return Response(status=status.HTTP_404_NOT_FOUND)

        fecha = request.query_params.get('fecha', '')
        hora = request.query_params.get('hora', '')
        grabacion = servicio_camaras.resolver_grabacion(
            camara, camara.empresa, fecha, hora)
        if not grabacion.get('disponible'):
            return Response(grabacion, status=status.HTTP_404_NOT_FOUND)
        return Response(grabacion)


# --------------------------- Notificaciones --------------------------------

class NotificacionesView(APIView):
    """GET lista las notificaciones activas (no resueltas) de la empresa."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        empresa = _obtener_empresa(request)
        qs = Notificacion.objects.filter(empresa=empresa)
        if request.query_params.get('incluir_resueltas') == '1':
            qs = qs.all()
        else:
            qs = NotificacionLecturaSerializer.activas(qs)
        datos = NotificacionLecturaSerializer(qs[:100], many=True).data
        return Response({"resultados": datos})


class NotificacionDetalleView(APIView):
    """PATCH marca una notificacion como revisada o resuelta.

    Una notificacion 'resuelta' se retira del panel activo.
    """
    permission_classes = [IsAuthenticated, EsAdministrador]

    def patch(self, request, id):
        aviso = Notificacion.objects.filter(
            empresa=_obtener_empresa(request), id=id).first()
        if not aviso:
            return Response(status=status.HTTP_404_NOT_FOUND)

        estado = (request.data.get('estado') or '').strip()
        if estado not in ('revisada', 'resuelta'):
            return Response(
                {"codigo": "ESTADO_INVALIDO",
                 "detalle": "Estado valido: revisada o resuelta."},
                status=status.HTTP_400_BAD_REQUEST)

        aviso.estado = estado
        aviso.leida = True
        aviso.save(update_fields=['estado', 'leida'])

        ActividadUsuario.registrar(
            request.user, "NOTIFICACION_MARCADA",
            f"#{str(aviso.id)[:8]} -> {estado}")
        return Response(NotificacionLecturaSerializer(aviso).data)
