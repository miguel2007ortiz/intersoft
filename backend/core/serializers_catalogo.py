"""Serializers de la fase 3: clientes y productos (personal interno).

Convenciones del proyecto:
- respuestas de error con {"codigo", "detalle", "errores"};
- el rechazo por documento duplicado informa el registro en conflicto;
- precio, stock y stock_minimo nunca negativos (ademas de los CHECK de BD)."""

from rest_framework import serializers

from cuentas.models import Perfil

from .models import Categoria, Cliente, Producto


# ------------------------------ Clientes -----------------------------------

class ClienteLecturaSerializer(serializers.ModelSerializer):
    usuario_id = serializers.SerializerMethodField()
    usuario_email = serializers.SerializerMethodField()
    total_compras = serializers.SerializerMethodField()

    class Meta:
        model = Cliente
        fields = ["id", "nombre", "tipo_documento", "numero_documento",
                  "email", "telefono", "direccion", "ciudad",
                  "usuario_id", "usuario_email", "total_compras", "created_at"]

    def get_usuario_id(self, cliente):
        return str(cliente.usuario_id) if cliente.usuario_id else None

    def get_usuario_email(self, cliente) -> str | None:
        return cliente.usuario.email if cliente.usuario else None

    def get_total_compras(self, cliente):
        return str(cliente.total_compras)


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
        consulta = (Cliente.objects.filter(empresa=self.context["empresa"],
                                           tipo_documento=tipo,
                                           numero_documento=numero,
                                           deleted_at__isnull=True))
        if self.instance:
            consulta = consulta.exclude(pk=self.instance.pk)
        otro = consulta.select_related("usuario").first()
        if otro is not None:
            # Regla fase 3: rechazar informando el registro en conflicto
            raise serializers.ValidationError({
                "numero_documento":
                    f"El documento {tipo} {numero} ya esta registrado para el "
                    f"cliente {otro.nombre} (registro en conflicto, creado el "
                    f"{otro.created_at:%d/%m/%Y}).",
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
                  "activo", "stock_bajo", "tiene_ventas", "created_at"]

    def get_categoria_id(self, producto):
        return str(producto.categoria_id) if producto.categoria_id else None

    def get_tiene_ventas(self, producto) -> bool:
        return producto.detalles_venta.exists()


class ProductoEscrituraSerializer(serializers.ModelSerializer):
    categoria_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Producto
        # 'activo' NO es escribible aqui: todo producto nace activo y su
        # estado solo cambia con los endpoints /desactivar/ y /reactivar/
        # (evita que un formulario sin checkbox lo apague por accidente).
        fields = ["nombre", "descripcion", "sku", "categoria_id", "precio",
                  "stock", "stock_minimo"]
        extra_kwargs = {
            "precio": {"min_value": 0},
            "stock": {"min_value": 0},          # regla fase 3: stock >= 0
            "stock_minimo": {"min_value": 0},
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
        return categoria.productos.filter(deleted_at__isnull=True).count()

    def validate_nombre(self, valor):
        consulta = Categoria.objects.filter(empresa=self.context["empresa"],
                                            nombre__iexact=valor)
        if self.instance:
            consulta = consulta.exclude(pk=self.instance.pk)
        if consulta.exists():
            raise serializers.ValidationError("Ya existe una categoria con ese nombre.")
        return valor
