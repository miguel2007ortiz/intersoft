"""API de la fase 3 (personal interno: ADMINISTRADOR o EMPLEADO):
- CRUD de clientes con documento unico por empresa (el rechazo informa
  el registro en conflicto) y vinculo opcional a un usuario existente;
- CRUD de productos; si el producto tiene detalle_venta no se elimina
  fisicamente, solo se desactiva (queda oculto del catalogo);
- catalogo de categorias para el formulario de productos.
Toda accion queda auditada en actividad_usuario."""

from django.db import IntegrityError, transaction
from django.db.models import (Count, DecimalField, Exists, OuterRef, Q, Sum,
                              Value)
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import ActividadUsuario
from cuentas.permissions import EsPersonal

from .models import Categoria, Cliente, DetalleVenta, Producto
from .serializers_catalogo import (
    CategoriaSerializer, ClienteDetalleSerializer, ClienteEscrituraSerializer,
    ClienteLecturaSerializer, ProductoEscrituraSerializer, ProductoLecturaSerializer,
)

def respuesta_datos_invalidos(errores):
    return Response({"codigo": "DATOS_INVALIDOS",
                     "detalle": "Revisa los datos del formulario.",
                     "errores": errores},
                    status=status.HTTP_400_BAD_REQUEST)


def _limite_paginacion(valor, por_defecto=50, maximo=200):
    """Limite de filas a devolver, acotado a [1, maximo]."""
    try:
        return max(1, min(int(valor), maximo))
    except (TypeError, ValueError):
        return por_defecto


# ------------------------------ Clientes -----------------------------------

class ClientesView(APIView):
    """GET lista (con busqueda, filtro de estado y paginacion) / POST crea cliente."""
    permission_classes = [IsAuthenticated, EsPersonal]
    POR_PAGINA = 25

    def get(self, request):
        clientes = Cliente.objects.select_related("usuario").filter(
            empresa=request.user.perfil.empresa)

        estado = request.query_params.get("estado", "activos")
        if estado == "activos":
            clientes = clientes.filter(deleted_at__isnull=True)
        elif estado == "inactivos":
            clientes = clientes.filter(deleted_at__isnull=False)
        # estado == "todos": sin filtro adicional

        busqueda = request.query_params.get("busqueda", "").strip()
        if busqueda:
            clientes = clientes.filter(
                Q(nombre__icontains=busqueda)
                | Q(numero_documento__icontains=busqueda)
                | Q(email__icontains=busqueda))

        # Fase 6: evita N+1 (usuario_email + total_compras por cliente).
        clientes = clientes.annotate(
            _total_compras=Coalesce(
                Sum("ventas__total",
                    filter=Q(ventas__deleted_at__isnull=True,
                             ventas__estado="completada")),
                Value(0), output_field=DecimalField(max_digits=12,
                                                    decimal_places=2)))

        clientes = clientes.order_by("nombre")
        total = clientes.count()
        try:
            pagina = max(int(request.query_params.get("pagina", 1)), 1)
        except (TypeError, ValueError):
            pagina = 1
        inicio = (pagina - 1) * self.POR_PAGINA
        datos = ClienteLecturaSerializer(
            clientes[inicio:inicio + self.POR_PAGINA], many=True).data
        return Response({
            "resultados": datos,
            "total": total,
            "pagina": pagina,
            "por_pagina": self.POR_PAGINA,
            "total_paginas": max((total + self.POR_PAGINA - 1) // self.POR_PAGINA, 1),
        })

    def post(self, request):
        entrada = ClienteEscrituraSerializer(data=request.data,
                                             context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidos(entrada.errors)

        try:
            with transaction.atomic():
                cliente = entrada.save()
        except IntegrityError:
            # Defensa ante condicion de carrera: dos solicitudes casi
            # simultaneas pasaron el validate() (que ya cubre el caso
            # normal) antes de que cualquiera de las dos insertara. La
            # constraint de BD no distingue activos/inactivos (CU-CLI-01).
            return Response({
                "codigo": "DOCUMENTO_DUPLICADO",
                "detalle": "Ese documento ya fue registrado (posible doble envio). "
                           "Actualiza el listado antes de reintentar.",
            }, status=status.HTTP_400_BAD_REQUEST)
        ActividadUsuario.registrar(request.user, "CLIENTE_CREADO",
                                   f"{cliente.nombre} ({cliente.tipo_documento} "
                                   f"{cliente.numero_documento})")
        return Response(ClienteLecturaSerializer(cliente).data,
                        status=status.HTTP_201_CREATED)


class ClienteDetalleView(APIView):
    """GET (incluye ultimas 5 ventas) / PUT-PATCH / DELETE (borrado logico).

    No filtra por deleted_at: un cliente desactivado tambien debe poder
    verse y reactivarse desde su propio detalle."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def obtener_cliente(self, request, id):
        return (Cliente.objects.select_related("usuario")
                .filter(empresa=request.user.perfil.empresa,
                        id=id).first())

    def get(self, request, id):
        cliente = self.obtener_cliente(request, id)
        if cliente is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(ClienteDetalleSerializer(cliente).data)

    def put(self, request, id):
        return self.editar(request, id, parcial=False)

    def patch(self, request, id):
        return self.editar(request, id, parcial=True)

    def editar(self, request, id, parcial: bool):
        cliente = self.obtener_cliente(request, id)
        if cliente is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        entrada = ClienteEscrituraSerializer(cliente, data=request.data,
                                             partial=parcial,
                                             context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidos(entrada.errors)

        try:
            with transaction.atomic():
                cliente = entrada.save()
        except IntegrityError:
            return Response({
                "codigo": "DOCUMENTO_DUPLICADO",
                "detalle": "Ese documento ya fue registrado (posible doble envio). "
                           "Actualiza el listado antes de reintentar.",
            }, status=status.HTTP_400_BAD_REQUEST)
        ActividadUsuario.registrar(request.user, "CLIENTE_EDITADO",
                                   f"{cliente.nombre} ({cliente.tipo_documento} "
                                   f"{cliente.numero_documento})")
        return Response(ClienteLecturaSerializer(cliente).data)

    def delete(self, request, id):
        cliente = self.obtener_cliente(request, id)
        if cliente is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        nombre = cliente.nombre
        with transaction.atomic():
            cliente.soft_delete()   # conserva historial de ventas
        ActividadUsuario.registrar(request.user, "CLIENTE_ELIMINADO", nombre)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClienteEstadoView(APIView):
    """POST desactiva o reactiva un cliente. Desactivar reusa el mismo
    borrado logico que DELETE (conserva historial); reactivar limpia
    deleted_at para que vuelva a aparecer en el listado de activos."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def post(self, request, id, accion):
        cliente = ClienteDetalleView().obtener_cliente(request, id)
        if cliente is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if accion not in ("desactivar", "reactivar"):
            return Response(status=status.HTTP_404_NOT_FOUND)

        deseado_activo = accion == "reactivar"
        if cliente.esta_activo == deseado_activo:
            # CU-CLI-05 E1: repetir la misma accion es idempotente, no un
            # error. El estado no cambia pero la respuesta es 200, nunca 500
            # ni 400 (evita que un doble-click o un reintento rompan la UI).
            return Response(ClienteDetalleSerializer(cliente).data)

        if deseado_activo:
            cliente.deleted_at = None
            cliente.save(update_fields=["deleted_at"])
        else:
            cliente.soft_delete()
        evento = "CLIENTE_REACTIVADO" if deseado_activo else "CLIENTE_DESACTIVADO"
        ActividadUsuario.registrar(request.user, evento, cliente.nombre)
        return Response(ClienteDetalleSerializer(cliente).data)


# ------------------------------ Productos ----------------------------------

class ProductosView(APIView):
    """GET lista (?busqueda=&activo=true/false) / POST crea producto."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        productos = Producto.objects.select_related("categoria").filter(
            empresa=request.user.perfil.empresa, deleted_at__isnull=True)
        busqueda = request.query_params.get("busqueda", "").strip()
        if busqueda:
            productos = productos.filter(Q(nombre__icontains=busqueda)
                                         | Q(sku__icontains=busqueda))
        filtro_activo = request.query_params.get("activo")
        if filtro_activo is not None:
            productos = productos.filter(activo=filtro_activo.lower() == "true")
        # Fase 6: anota 'tiene_ventas' para evitar un EXISTS por fila.
        productos = productos.annotate(
            tiene_ventas_flag=Exists(
                DetalleVenta.objects.filter(producto=OuterRef("pk"))))
        limite = _limite_paginacion(request.query_params.get("limite", 50))
        datos = ProductoLecturaSerializer(
            productos.order_by("nombre")[:limite], many=True).data
        return Response({"resultados": datos, "total": len(datos)})

    def post(self, request):
        entrada = ProductoEscrituraSerializer(data=request.data,
                                              context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidos(entrada.errors)

        with transaction.atomic():
            producto = entrada.save()
        ActividadUsuario.registrar(request.user, "PRODUCTO_CREADO",
                                   f"{producto.nombre} (${producto.precio}, "
                                   f"stock {producto.stock})")
        return Response(ProductoLecturaSerializer(producto).data,
                        status=status.HTTP_201_CREATED)


class ProductoDetalleView(APIView):
    """GET / PUT-PATCH / DELETE.

    Regla fase 3: si el producto tiene detalle_venta asociado NO se elimina
    fisicamente; la API responde PRODUCTO_CON_VENTAS y solo permite
    desactivarlo (activo=false), lo que lo oculta del catalogo publico."""
    permission_classes = [IsAuthenticated, EsPersonal]

    @staticmethod
    def obtener_producto(request, id):
        return (Producto.objects.select_related("categoria")
                .filter(empresa=request.user.perfil.empresa,
                        deleted_at__isnull=True, id=id).first())

    def get(self, request, id):
        producto = self.obtener_producto(request, id)
        if producto is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(ProductoLecturaSerializer(producto).data)

    def put(self, request, id):
        return self.editar(request, id, parcial=False)

    def patch(self, request, id):
        return self.editar(request, id, parcial=True)

    def editar(self, request, id, parcial: bool):
        if not request.user.perfil.tiene_permiso("producto.actualizar"):
            # RN Empleados: ver el catalogo no implica poder editarlo (precio incl.).
            return Response(status=status.HTTP_403_FORBIDDEN)
        producto = self.obtener_producto(request, id)
        if producto is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        entrada = ProductoEscrituraSerializer(producto, data=request.data,
                                              partial=parcial,
                                              context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidos(entrada.errors)

        with transaction.atomic():
            producto = entrada.save()
        ActividadUsuario.registrar(request.user, "PRODUCTO_EDITADO",
                                   f"{producto.nombre} (${producto.precio}, "
                                   f"stock {producto.stock})")
        return Response(ProductoLecturaSerializer(producto).data)

    def delete(self, request, id):
        producto = self.obtener_producto(request, id)
        if producto is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        ventas = producto.detalles_venta.count()
        if ventas > 0:
            return Response({
                "codigo": "PRODUCTO_CON_VENTAS",
                "detalle": (f"'{producto.nombre}' tiene {ventas} linea(s) de venta "
                            "registrada(s). No se puede eliminar: desactivalo para "
                            "ocultarlo del catalogo."),
                "ventas": ventas},
                status=status.HTTP_400_BAD_REQUEST)

        nombre = producto.nombre
        with transaction.atomic():
            producto.soft_delete()
        ActividadUsuario.registrar(request.user, "PRODUCTO_ELIMINADO", nombre)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductoEstadoView(APIView):
    """POST desactiva o reactiva un producto (ocultar/mostrar del catalogo)."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def post(self, request, id, accion):
        producto = ProductoDetalleView.obtener_producto(request, id)
        if producto is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if accion not in ("desactivar", "reactivar"):
            return Response(status=status.HTTP_404_NOT_FOUND)

        deseado = accion == "reactivar"
        if producto.activo == deseado:
            codigo = "YA_ACTIVO" if deseado else "YA_DESACTIVADO"
            return Response({"codigo": codigo,
                             "detalle": f"El producto ya esta {'activo' if deseado else 'inactivo'}."},
                            status=status.HTTP_400_BAD_REQUEST)

        producto.activo = deseado
        producto.save(update_fields=["activo"])
        evento = "PRODUCTO_REACTIVADO" if deseado else "PRODUCTO_DESACTIVADO"
        ActividadUsuario.registrar(request.user, evento, producto.nombre)
        return Response(ProductoLecturaSerializer(producto).data)


# ------------------------------ Categorias ---------------------------------

class CategoriasView(APIView):
    """GET catalogo / POST crea categoria (para el formulario de productos)."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        categorias = Categoria.objects.filter(empresa=request.user.perfil.empresa,
                                              deleted_at__isnull=True)
        # Fase 6: anota el conteo para evitar un COUNT por fila.
        categorias = categorias.annotate(
            total_productos=Count("productos",
                                  filter=Q(productos__deleted_at__isnull=True)))
        datos = CategoriaSerializer(categorias.order_by("nombre"), many=True).data
        return Response({"resultados": datos, "total": len(datos)})

    def post(self, request):
        entrada = CategoriaSerializer(data=request.data,
                                      context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidos(entrada.errors)
        categoria = entrada.save(empresa=request.user.perfil.empresa)
        ActividadUsuario.registrar(request.user, "CATEGORIA_CREADA", categoria.nombre)
        return Response(CategoriaSerializer(categoria).data,
                        status=status.HTTP_201_CREATED)
