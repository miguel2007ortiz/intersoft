"""API de la fase 7: reportes (solo ADMINISTRADOR).

Seleccionar un tipo de reporte y rango de fechas/categoria, consultar la
vista SQL correspondiente y devolver las filas, o exportarlas:
- Excel (formato=excel): CSV UTF-8 con BOM (abre de forma nativa en Excel),
- PDF (formato=pdf): HTML con estilos de impresion; el navegador lo imprime
  o guarda como PDF. No hay dependencias de librerias externas.
Cada generacion/exportacion queda registrada en actividad_usuario.
"""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import ActividadUsuario
from cuentas.permissions import EsAdministrador

from . import analytics


def _filtros_dashboard(request):
    """Construye los filtros validados. Si el cliente manda una fecha o
    categoria malformada devuelve el par (None, respuesta_400)."""
    try:
        filtros = analytics.FiltrosDashboard(request)
    except ValueError as exc:
        return None, Response(
            {"codigo": "FILTROS_INVALIDOS",
             "detalle": str(exc)},
            status=status.HTTP_400_BAD_REQUEST)
    return filtros, None


class TiposReporteView(APIView):
    """Catalogo de tipos de reporte disponibles (consultan las vistas)."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        return Response({
            'resultados': [
                {'tipo': tipo, 'titulo': def_r['titulo'],
                 'columnas': [{'clave': clave, 'nombre': nombre}
                              for clave, nombre in def_r['columnas']]}
                for tipo, def_r in analytics.TIPOS_REPORTE.items()
            ]
        })


class ReporteVistaView(APIView):
    """GET datos del reporte (JSON) segun tipo + rango + categoria."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        tipo = request.query_params.get('tipo', '')
        if tipo not in analytics.TIPOS_REPORTE:
            return Response(
                {"codigo": "TIPO_INVALIDO",
                 "detalle": "Tipo de reporte no valido.",
                 "tipos": list(analytics.TIPOS_REPORTE.keys())},
                status=status.HTTP_400_BAD_REQUEST)

        f, error = _filtros_dashboard(request)
        if error:
            return error
        datos = analytics.reporte_json(tipo, f)

        ActividadUsuario.registrar(
            request.user, "REPORTE_GENERADO",
            f"{tipo} [{f.fecha_inicio or 'inicio'} a {f.fecha_fin or 'hoy'}]")
        return Response(datos)


class ReporteExportarView(APIView):
    """GET exporta un reporte en un formato descargable (excel o pdf)."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        tipo = request.query_params.get('tipo', '')
        formato = request.query_params.get('formato', 'excel')
        if tipo not in analytics.TIPOS_REPORTE:
            return Response(
                {"codigo": "TIPO_INVALIDO",
                 "detalle": "Tipo de reporte no valido."},
                status=status.HTTP_400_BAD_REQUEST)

        f, error = _filtros_dashboard(request)
        if error:
            return error
        empresa = request.user.perfil.empresa

        if formato == 'pdf':
            contenido = analytics.exportar_html(tipo, f, empresa)
            respuesta = HttpResponse(contenido, content_type='text/html; charset=utf-8')
            respuesta['Content-Disposition'] = (
                f'inline; filename="reporte-{tipo}.html"')
        elif formato == 'excel':
            contenido = analytics.exportar_csv(tipo, f)
            respuesta = HttpResponse(
                contenido.encode('utf-8'), content_type='text/csv; charset=utf-8')
            respuesta['Content-Disposition'] = (
                f'attachment; filename="reporte-{tipo}.csv"')
        else:
            return Response(
                {"codigo": "FORMATO_INVALIDO",
                 "detalle": "Formato no valido (usa excel o pdf)."},
                status=status.HTTP_400_BAD_REQUEST)

        ActividadUsuario.registrar(
            request.user, "REPORTE_EXPORTADO",
            f"{formato.upper()} - {tipo} "
            f"[{f.fecha_inicio or 'inicio'} a {f.fecha_fin or 'hoy'}]")

        return respuesta
