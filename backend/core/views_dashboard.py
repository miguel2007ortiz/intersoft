"""API de la fase 7: dashboard de analitica (solo ADMINISTRADOR).

Endpoints de lectura que consultan las vistas SQL (core/analytics.py) y
devolucion de series listas para graficar. Todos aceptan los filtros
`fecha_inicio`, `fecha_fin` y `categoria` para refrescar sin recargar.
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.permissions import EsAdministrador

from . import analytics


class DashboardResumenView(APIView):
    """KPIs del panel (ingresos, ventas, ticket, inventario, bajo minimo)."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        f = analytics.FiltrosDashboard(request)
        return Response(analytics.resumen(f))


class DashboardVentasView(APIView):
    """Series de ventas por dia y por mes para las graficas."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        f = analytics.FiltrosDashboard(request)
        return Response({
            'por_dia': analytics.ventas_por_dia(f),
            'por_mes': analytics.ventas_por_mes(f),
        })


class DashboardTopProductosView(APIView):
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        f = analytics.FiltrosDashboard(request)
        return Response({'resultados': analytics.top_productos(f)})


class DashboardClientesFrecuentesView(APIView):
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        f = analytics.FiltrosDashboard(request)
        return Response({'resultados': analytics.clientes_frecuentes(f)})


class DashboardInventarioView(APIView):
    """Valor del inventario por categoria, rotacion y productos bajo minimo."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        empresa_id = request.user.perfil.empresa_id
        return Response({
            'valor_por_categoria': analytics.valor_inventario_por_categoria(empresa_id),
            'rotacion': analytics.rotacion_productos(empresa_id),
            'bajo_minimo': analytics.productos_bajo_minimo(empresa_id),
        })


class DashboardCategoriasView(APIView):
    """Catalogo de categorias para el filtro del dashboard."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        empresa_id = request.user.perfil.empresa_id
        return Response({'resultados': analytics.categorias(empresa_id)})
