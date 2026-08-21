import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """UUID + timestamps + borrado logico para todos los modelos hijos."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    @property
    def esta_activo(self):
        return self.deleted_at is None


class Empresa(TimeStampedModel):
    PLAN_CHOICES = [('basic', 'Plan Basico'), ('pro', 'Plan Profesional'),
                    ('enterprise', 'Plan Empresarial')]
    nombre = models.CharField(max_length=150)
    nit = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basic')
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nombre} ({self.get_plan_display()})"


class Categoria(TimeStampedModel):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='categorias')
    nombre = models.CharField(max_length=80)
    descripcion = models.TextField(blank=True)

    class Meta:
        unique_together = ('empresa', 'nombre')
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(TimeStampedModel):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='productos')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True,
                                  blank=True, related_name='productos')
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    sku = models.CharField(max_length=50)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=10)
    imagen = models.ImageField(upload_to='productos/%Y/%m/', blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('empresa', 'sku')
        ordering = ['nombre']
        indexes = [models.Index(fields=['empresa', 'activo']),
                   models.Index(fields=['stock'])]
        constraints = [
            # Validaciones globales de fase 1: montos y existencias nunca negativos
            models.CheckConstraint(condition=models.Q(precio__gte=0),
                                   name='producto_precio_no_negativo'),
            models.CheckConstraint(condition=models.Q(stock__gte=0),
                                   name='producto_stock_no_negativo'),
            models.CheckConstraint(condition=models.Q(stock_minimo__gte=0),
                                   name='producto_stock_minimo_no_negativo'),
        ]

    def __str__(self):
        return f"{self.nombre} (stock: {self.stock})"

    @property
    def stock_bajo(self):
        return self.stock <= self.stock_minimo


class Cliente(TimeStampedModel):
    TIPO_DOC_CHOICES = [('CC', 'Cedula de Ciudadania'), ('NIT', 'NIT'),
                        ('CE', 'Cedula de Extranjeria'), ('PAS', 'Pasaporte')]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='clientes')
    # Cuenta opcional del portal (tabla usuario real: auth_user + Perfil)
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='perfil_cliente')
    nombre = models.CharField(max_length=120)
    tipo_documento = models.CharField(max_length=10, choices=TIPO_DOC_CHOICES, default='CC')
    numero_documento = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    ciudad = models.CharField(max_length=80, blank=True)

    class Meta:
        # Documento unico DENTRO de cada empresa (multi-tenant)
        unique_together = ('empresa', 'tipo_documento', 'numero_documento')
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.tipo_documento} {self.numero_documento})"

    @property
    def total_compras(self):
        from django.db.models import Sum
        total = self.ventas.filter(deleted_at__isnull=True, estado='completada') \
            .aggregate(Sum('total'))['total__sum']
        return total or 0


class Venta(TimeStampedModel):
    ESTADO_CHOICES = [('pendiente', 'Pendiente'), ('completada', 'Completada'),
                      ('anulada', 'Anulada')]
    METODO_PAGO_CHOICES = [('efectivo', 'Efectivo'), ('transferencia', 'Transferencia bancaria'),
                           ('nequi', 'Nequi'), ('daviplata', 'Daviplata'),
                           ('tarjeta', 'Tarjeta'), ('otro', 'Otro')]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ventas')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='ventas')
    vendedor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 blank=True, related_name='ventas_realizadas')
    numero_factura = models.CharField(max_length=50, unique=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='efectivo')
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha']
        indexes = [models.Index(fields=['empresa', '-fecha']), models.Index(fields=['estado'])]
        constraints = [
            models.CheckConstraint(condition=models.Q(total__gte=0),
                                   name='venta_total_no_negativo'),
        ]

    def __str__(self):
        return f"Factura {self.numero_factura} - {self.cliente.nombre} (${self.total})"

    def _generar_numero_factura(self):
        fecha = timezone.localtime().strftime('%Y%m%d')
        consecutivo = Venta.objects.filter(empresa=self.empresa).count() + 1
        prefijo = self.empresa.id.hex[:8].upper()
        return f"{prefijo}-{fecha}-{consecutivo:05d}"

    def save(self, *args, **kwargs):
        if not self.numero_factura:
            self.numero_factura = self._generar_numero_factura()
        super().save(*args, **kwargs)


class DetalleVenta(TimeStampedModel):
    """Linea de una venta: producto vendido con su cantidad y precio del momento."""
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles_venta')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        # El mismo producto no se repite en lineas distintas de la misma venta
        unique_together = ('venta', 'producto')
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0),
                                   name='detalle_cantidad_positiva'),
            models.CheckConstraint(condition=models.Q(precio_unitario__gte=0),
                                   name='detalle_precio_no_negativo'),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en {self.venta.numero_factura}"

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


class MovimientoInventario(TimeStampedModel):
    """Kardex: cada entrada, salida o ajuste que afecta el stock de un producto."""
    TIPO_CHOICES = [('entrada', 'Entrada'), ('salida', 'Salida'), ('ajuste', 'Ajuste')]
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                blank=True, related_name='movimientos_inventario')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.PositiveIntegerField()
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['producto', '-created_at'])]
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0),
                                   name='movimiento_cantidad_positiva'),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.cantidad} - {self.producto.nombre}"


class Notificacion(TimeStampedModel):
    """Aviso para un usuario (p. ej. alertas de stock bajo)."""
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                null=True, blank=True, related_name='notificaciones')
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['usuario', 'leida'])]

    def __str__(self):
        return f"{'Leida' if self.leida else 'Nueva'}: {self.mensaje[:60]}"
