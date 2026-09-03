"""Serializers de la fase 3: clientes y productos (personal interno).

Convenciones del proyecto:
- respuestas de error con {"codigo", "detalle", "errores"};
- el rechazo por documento duplicado informa el registro en conflicto;
- precio, stock y stock_minimo nunca negativos (ademas de los CHECK de BD)."""

from rest_framework import serializers

from cuentas.models import Perfil

from .models import Categoria, Cliente, Producto, Venta


# ------------------------------ Clientes -----------------------------------

class ClienteLecturaSerializer(serializers.ModelSerializer):
    usuario_id = serializers.SerializerMethodField()
    usuario_email = serializers.SerializerMethodField()
    total_compras = serializers.SerializerMethodField()
    activo = serializers.BooleanField(source="esta_activo", read_only=True)

    class Meta:
        model = Cliente
        fields = ["id", "nombre", "tipo_documento", "numero_documento",
                  "email", "telefono", "direccion", "ciudad", "activo",
                  "usuario_id", "usuario_email", "total_compras", "created_at"]

    def get_usuario_id(self, cliente):
        return str(cliente.usuario_id) if cliente.usuario_id else None

    def get_usuario_email(self, cliente) -> str | None:
        return cliente.usuario.email if cliente.usuario else None

    def get_total_compras(self, cliente):
        # Usa la anotacion del queryset (Fase 6) si existe; si no, la
        # propiedad del modelo (un solo registro).
        total = getattr(cliente, "_total_compras", None)
        if total is None:
            total = cliente.total_compras
        return str(total or "0")


class VentaResumenSerializer(serializers.ModelSerializer):
    """Resumen de una venta para el historial del detalle de cliente
    (no expone lineas ni datos de facturacion, solo lo esencial)."""

    class Meta:
        model = Venta
        fields = ["id", "numero_factura", "fecha", "total", "estado"]


class ClienteDetalleSerializer(ClienteLecturaSerializer):
    """Igual que el listado, mas las ultimas 5 ventas del cliente."""
    ultimas_ventas = serializers.SerializerMethodField()

    class Meta(ClienteLecturaSerializer.Meta):
        fields = ClienteLecturaSerializer.Meta.fields + ["ultimas_ventas"]

    def get_ultimas_ventas(self, cliente):
        ventas = cliente.ventas.filter(deleted_at__isnull=True).order_by("-fecha")[:5]
        return VentaResumenSerializer(ventas, many=True).data


class ClienteEscrituraSerializer(serializers.ModelSerializer):
    usuario_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Cliente
        fields = ["nombre", "tipo_documento", "numero_documento", "email",
                  "telefono", "direccion", "ciudad", "usuario_id"]

    def validate_usuario_id(self, valor):
        """Recibe el id del PERFIL (como los lista la API de seguridad) y
        resuelve la cuenta real a vincular."""
        if valor is None:
            return None
        perfil = (Perfil.objects.select_related("usuario", "empresa", "rol")
                  .filter(id=valor).first())
        if perfil is None or not perfil.usuario.is_active:
            raise serializers.ValidationError(
                "El usuario a vincular no existe o esta inactivo.")
        if perfil.empresa_id != self.context["empresa"].id:
            raise serializers.ValidationError(
                "Ese usuario pertenece a otra empresa.")
        conflicto = Cliente.objects.filter(empresa=self.context["empresa"],
                                           usuario=perfil.usuario,
                                           deleted_at__isnull=True)
        if self.instance:
            conflicto = conflicto.exclude(pk=self.instance.pk)
        if conflicto.first() is not None:
            otro = conflicto.first()
            raise serializers.ValidationError(
                f"Ese usuario ya esta vinculado al cliente {otro.nombre} "
                f"({otro.tipo_documento} {otro.numero_documento}).")
        return perfil.usuario

    def validate(self, datos):
        tipo = datos.get("tipo_documento", getattr(self.instance, "tipo_documento", ""))
        numero = datos.get("numero_documento",
                           getattr(self.instance, "numero_documento", ""))
        # OJO: la constraint de BD (empresa, tipo_documento, numero_documento) no
        # distingue clientes activos de inactivos, asi que esta consulta NO debe
        # filtrar por deleted_at: si no se detecta aqui un conflicto contra un
        # cliente inactivo, el create() de mas abajo revienta con IntegrityError
        # (500). Ver fase 4, CU-CLI-01 A2/E1.
        consulta = (Cliente.objects.filter(empresa=self.context["empresa"],
                                           tipo_documento=tipo,
                                           numero_documento=numero))
        if self.instance:
            consulta = consulta.exclude(pk=self.instance.pk)
        otro = consulta.select_related("usuario").first()
        if otro is not None:
            if otro.esta_activo:
                # E1: conflicto con un cliente activo. Rechazo simple.
                raise serializers.ValidationError({
                    "numero_documento":
                        f"El documento {tipo} {numero} ya esta registrado para el "
                        f"cliente {otro.nombre} (registro en conflicto, creado el "
                        f"{otro.created_at:%d/%m/%Y}).",
                })
            # A2: el registro en conflicto esta inactivo. No se crea un
            # duplicado; se ofrece el id para que la UI proponga reactivarlo.
            raise serializers.ValidationError({
                "numero_documento":
                    f"Ya existe un cliente inactivo con el documento {tipo} {numero} "
                    f"({otro.nombre}). Reactivalo en vez de crear uno nuevo.",
                "cliente_inactivo_id": str(otro.id),
            })
        return datos

    def create(self, datos_validados):
        usuario = datos_validados.pop("usuario_id", None)
        return Cliente.objects.create(empresa=self.context["empresa"],
                                      usuario=usuario, **datos_validados)

    def update(self, instancia, datos_validados):
        if "usuario_id" in datos_validados:   # ausente = conservar vinculo actual
            instancia.usuario = datos_validados.pop("usuario_id")
        for campo, valor in datos_validados.items():
            setattr(instancia, campo, valor)
        instancia.save()
        return instancia


# ------------------------------ Productos ----------------------------------

class ProductoLecturaSerializer(serializers.ModelSerializer):
    categoria_id = serializers.SerializerMethodField()
    categoria_nombre = serializers.CharField(source="categoria.nombre", default=None)
    tiene_ventas = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = ["id", "nombre", "descripcion", "sku", "categoria_id",
                  "categoria_nombre", "precio", "stock", "stock_minimo",
                  "activo", "stock_bajo", "tiene_ventas", "imagen", "created_at"]

    def get_categoria_id(self, producto):
        return str(producto.categoria_id) if producto.categoria_id else None

    def get_tiene_ventas(self, producto) -> bool:
        # Usa la anotacion del queryset (Fase 6) si existe.
        if hasattr(producto, "tiene_ventas_flag"):
            return producto.tiene_ventas_flag
        return producto.detalles_venta.exists()


class ProductoEscrituraSerializer(serializers.ModelSerializer):
    categoria_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Producto
        # 'activo' NO es escribible aqui: todo producto nace activo y su
        # estado solo cambia con los endpoints /desactivar/ y /reactivar/
        # (evita que un formulario sin checkbox lo apague por accidente).
        fields = ["nombre", "descripcion", "sku", "categoria_id", "precio",
                  "stock", "stock_minimo", "imagen"]
        extra_kwargs = {
            "precio": {"min_value": 0},
            "stock": {"min_value": 0},          # regla fase 3: stock >= 0
            "stock_minimo": {"min_value": 0},
            "imagen": {"required": False, "allow_null": True},
        }

    def validate_categoria_id(self, valor):
        if valor is None:
            return None
        categoria = Categoria.objects.filter(id=valor,
                                             empresa=self.context["empresa"]).first()
        if categoria is None:
            raise serializers.ValidationError(
                "La categoria no existe en tu empresa.")
        return categoria

    def validate_sku(self, valor):
        consulta = Producto.objects.filter(empresa=self.context["empresa"], sku=valor,
                                           deleted_at__isnull=True)
        if self.instance:
            consulta = consulta.exclude(pk=self.instance.pk)
        if consulta.exists():
            raise serializers.ValidationError(
                f"El SKU '{valor}' ya existe en tu empresa.")
        return valor

    def create(self, datos_validados):
        categoria = datos_validados.pop("categoria_id", None)
        return Producto.objects.create(empresa=self.context["empresa"],
                                       categoria=categoria, **datos_validados)

    def update(self, instancia, datos_validados):
        if "categoria_id" in datos_validados:   # ausente = conservar categoria
            instancia.categoria = datos_validados.pop("categoria_id")
        for campo, valor in datos_validados.items():
            setattr(instancia, campo, valor)
        instancia.save()
        return instancia


# ------------------------------ Categorias ---------------------------------

class CategoriaSerializer(serializers.ModelSerializer):
    total_productos = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion", "total_productos"]

    def get_total_productos(self, categoria) -> int:
        # Usa la anotacion del queryset (Fase 6) si existe.
        if hasattr(categoria, "total_productos"):
            return categoria.total_productos
        return categoria.productos.filter(deleted_at__isnull=True).count()

    def validate_nombre(self, valor):
        consulta = Categoria.objects.filter(empresa=self.context["empresa"],
                                            nombre__iexact=valor)
        if self.instance:
            consulta = consulta.exclude(pk=self.instance.pk)
        if consulta.exists():
            raise serializers.ValidationError("Ya existe una categoria con ese nombre.")
        return valor
