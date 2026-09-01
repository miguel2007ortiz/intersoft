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
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basic')
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nombre} ({self.get_plan_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generar_slug()
        super().save(*args, **kwargs)

    def _generar_slug(self):
        from django.utils.text import slugify
        base = slugify(self.nombre) or slugify(self.nit)
        slug = base
        contador = 2
        while Empresa.objects.exclude(pk=self.pk).filter(slug=slug).exists():
            slug = f"{base}-{contador}"
            contador += 1
        return slug


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
    numero_factura = models.CharField(max_length=50, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='efectivo')
    notas = models.TextField(blank=True)
    motivo_anulacion = models.TextField(blank=True)
    anulada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha']
        indexes = [models.Index(fields=['empresa', '-fecha']), models.Index(fields=['estado'])]
        constraints = [
            models.CheckConstraint(condition=models.Q(total__gte=0),
                                   name='venta_total_no_negativo'),
            models.CheckConstraint(condition=models.Q(descuento__gte=0),
                                   name='venta_descuento_no_negativo'),
            models.UniqueConstraint(fields=['empresa', 'numero_factura'],
                                    name='venta_numero_factura_empresa_unico'),
        ]

    def __str__(self):
        return f"Factura {self.numero_factura} - {self.cliente.nombre} (${self.total})"

    def _generar_numero_factura(self, bloqueada=False):
        fecha = timezone.localtime().strftime('%Y%m%d')
        # Correlativo por empresa. Si 'bloqueada' es True es porque la fila de
        # la empresa ya esta siendo lockeada (SELECT FOR UPDATE) por el caller,
        # lo que serializa la generacion del consecutivo sin colisiones.
        consecutivo = Venta.objects.filter(empresa=self.empresa).count() + 1
        prefijo = self.empresa_id.hex[:8].upper()
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
    """Aviso para un usuario (p. ej. alertas de stock bajo, fase 9).

    Desde la fase 9 el sistema es global por empresa:
    - `tipo`: origen del evento (stock, factura, camara, sistema).
    - `empresa`: alcance multi-tenancy (null en avisos pre-fase 9).
    - `estado`: nueva -> revisada -> resuelta. Una notificacion 'resuelta'
      se retira del panel activo de notificaciones.
    - `canal`: via de entrega efectiva (whatsapp/email/ninguno).
    - `entrega_pendiente`: True si la entrega fallo y queda a la espera de
      reintento (mecanismo "no perder el aviso", fase 9).
    Se conserva `leida` (equivalente a estado != 'nueva') por compatibilidad
    con fases anteriores.
    """
    TIPO_CHOICES = [('stock', 'Stock bajo'), ('factura', 'Facturacion'),
                    ('camara', 'Camara'), ('sistema', 'Sistema')]
    ESTADO_CHOICES = [('nueva', 'Nueva'), ('revisada', 'Revisada'),
                      ('resuelta', 'Resuelta')]
    CANAL_CHOICES = [('ninguno', 'Sin entrega'), ('whatsapp', 'WhatsApp'),
                     ('email', 'Email')]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                null=True, blank=True, related_name='notificaciones')
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE,
                                null=True, blank=True, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES,
                            default='sistema')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES,
                              default='nueva')
    canal = models.CharField(max_length=20, choices=CANAL_CHOICES,
                             default='ninguno')
    leida = models.BooleanField(default=False)
    entrega_pendiente = models.BooleanField(
        default=False,
        help_text="True si se intento notificar pero fallo la entrega por "
                  "todos los canales y queda pendiente de reintento.")
    mensaje = models.TextField()

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['empresa', 'estado']),
                   models.Index(fields=['usuario', 'leida'])]

    def __str__(self):
        return f"{self.get_estado_display()} ({self.tipo}): {self.mensaje[:60]}"


class Cupon(TimeStampedModel):
    """Codigo de descuento con vigencia y porcentaje."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cupones')
    codigo = models.CharField(max_length=30)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()

    class Meta:
        unique_together = ('empresa', 'codigo')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.codigo} ({self.porcentaje}%)"

    @property
    def esta_vigente(self):
        now = timezone.now()
        return self.activo and self.fecha_inicio <= now <= self.fecha_fin


class Carrito(TimeStampedModel):
    """Carrito de compras de un usuario (1 carrito activo por usuario)."""
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='carrito')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='carritos')
    cupon = models.ForeignKey(Cupon, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='carritos')

    class Meta:
        verbose_name_plural = "Carritos"

    def __str__(self):
        return f"Carrito de {self.usuario.email}"

    @property
    def total_items(self):
        return sum(item.cantidad for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())


class CarritoItem(TimeStampedModel):
    """Item individual dentro de un carrito."""
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='carrito_items')
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('carrito', 'producto')

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    @property
    def subtotal(self):
        return self.producto.precio * self.cantidad


class FacturaElectronica(TimeStampedModel):
    """Comprobante electronico DIAN ligado a una venta.

    Estados:
    - pendiente: documento generado, esperando envio/respuesta DIAN.
    - enviada: enviada a DIAN, esperando validacion.
    - aprobada: DIAN acepto → tiene CUFE + comprobante PDF/XML.
    - rechazada: DIAN rechazo → motivo en motivo_rechazo, admin corrige.
    - fallida: servicio DIAN sin respuesta → reintento automatico.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('fallida', 'Fallida'),
    ]

    venta = models.OneToOneField(Venta, on_delete=models.CASCADE,
                                 related_name='factura_electronica')
    numero = models.CharField(max_length=50, unique=True, blank=True)
    cufe = models.CharField(max_length=100, blank=True, default='')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    motivo_rechazo = models.TextField(blank=True, default='')
    pdf = models.FileField(upload_to='facturas/%Y/%m/pdf/', blank=True, null=True)
    xml = models.FileField(upload_to='facturas/%Y/%m/xml/', blank=True, null=True)
    intentos = models.PositiveSmallIntegerField(default=0)
    ultimo_intento = models.DateTimeField(null=True, blank=True)
    enviado_correo = models.BooleanField(default=False)
    enviado_correo_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Factura {self.numero} [{self.get_estado_display()}]"


class NotaCredito(TimeStampedModel):
    """Nota credito DIAN para reversar una venta ya facturada.

    Estados: pendiente / aprobada / rechazada.
    Cuando se aprueba, la venta original se marca como anulada y se
    revierte el stock.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    venta_original = models.ForeignKey(Venta, on_delete=models.CASCADE,
                                       related_name='notas_credito')
    numero = models.CharField(max_length=50, unique=True, blank=True)
    cufe_nota = models.CharField(max_length=100, blank=True, default='')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    motivo = models.TextField()
    pdf = models.FileField(upload_to='notas_credito/%Y/%m/pdf/', blank=True, null=True)
    xml = models.FileField(upload_to='notas_credito/%Y/%m/xml/', blank=True, null=True)
    reverso_stock = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Nota Credito {self.numero} sobre {self.venta_original.numero_factura}"


# --------------------------- Fase 8: Asistente IA ---------------------------

class IAConversacion(TimeStampedModel):
    """Sesion de chat del asistente IA (una por contexto de la conversacion).

    Guarda el contexto para preguntas de seguimiento dentro de la misma
    sesion: los mensajes de la sesion se reutilizan al llamar al motor."
    """
    ESTADO_CHOICES = [('activa', 'Activa'), ('archivada', 'Archivada')]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='ia_conversaciones')
    titulo = models.CharField(max_length=120, blank=True, default='')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Conversaciones IA"

    @property
    def ultimo_mensaje(self):
        ultimo = self.mensajes.order_by('-created_at').first()
        return ultimo.contenido if ultimo else ''

    def __str__(self):
        return f"IA {self.titulo or self.id} de {self.usuario.email}"


class IAMensaje(TimeStampedModel):
    """Mensaje individual de una conversacion IA.

    `rol`: quién emite (usuario o asistente).
    `estado`/`error`: si el motor fallo (timeout), el mensaje del asistente
    queda con estado 'error' y la conversacion se conserva para reintentar.
    """
    ROL_CHOICES = [('usuario', 'Usuario'), ('asistente', 'Asistente')]
    ESTADO_CHOICES = [('ok', 'Ok'), ('error', 'Error')]

    conversacion = models.ForeignKey(IAConversacion, on_delete=models.CASCADE,
                                     related_name='mensajes')
    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    contenido = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ok')
    error = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['conversacion', 'created_at'])]

    def __str__(self):
        return f"{self.get_rol_display()}: {self.contenido[:40]}"


# --------------------------- Fase 9: Camaras ---------------------------------

class Camara(TimeStampedModel):
    """Camara de vigilancia de la empresa (solo ADMINISTRADOR).

    `url_stream`: URL del video en vivo de la camara.
    `activa`: si esta False la camara se oculta del panel.
    Las grabaciones historicas no se guardan aqui: se resuelven por fecha/hora
    contra el servidor de almacenamiento (`url_stream` base) en
    `servicios/camaras.py`.
    """
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE,
                                related_name='camaras')
    nombre = models.CharField(max_length=120)
    ubicacion = models.CharField(max_length=150, blank=True, default='')
    url_stream = models.CharField(max_length=300, blank=True, default='')
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        indexes = [models.Index(fields=['empresa', 'activa'])]

    def __str__(self):
        return f"{self.nombre} ({self.ubicacion or 'Sin ubicacion'})"
