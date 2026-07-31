"""
Modelos de InterSoft.

Fase 1 (MVP): 5 entidades núcleo del MER.
  1. Empresa   — multi-tenancy (raíz de aislamiento de datos)
  2. Usuario   — operadores del sistema con rol
  3. Producto  — inventario (con Categoria como apoyo)
  4. Cliente   — compradores / CRM
  5. Venta     — transacciones

Decisiones de diseño:
  - UUID como PK: oculta el tamaño del negocio y evita enumeración (seguridad).
  - Borrado lógico (soft delete): nunca se pierde trazabilidad.
  - fk_empresa en todas las tablas: aislamiento multi-tenant estricto.
"""

import uuid

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


# ════════════════════════════════════════════════════════════
# CLASE BASE ABSTRACTA
# ════════════════════════════════════════════════════════════
class TimeStampedModel(models.Model):
    """
    Modelo base reutilizable.
    Aporta UUID, marcas de tiempo y borrado lógico a todos los hijos.
    Al ser abstract=True, NO crea tabla propia: solo hereda columnas.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Actualizado")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Eliminado")

    class Meta:
        abstract = True

    def soft_delete(self):
        """Marca el registro como eliminado sin borrarlo físicamente."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    @property
    def esta_activo(self):
        """True si el registro NO ha sido borrado lógicamente."""
        return self.deleted_at is None


# ════════════════════════════════════════════════════════════
# 1. MÓDULO TENANT — EMPRESA (raíz multi-tenant)
# ════════════════════════════════════════════════════════════
class Empresa(TimeStampedModel):
    """Cada empresa es un 'inquilino' (tenant) aislado del SaaS."""

    PLAN_CHOICES = [
        ('basic', 'Plan Básico'),
        ('pro', 'Plan Profesional'),
        ('enterprise', 'Plan Empresarial'),
    ]

    nombre = models.CharField(max_length=150, verbose_name="Nombre del negocio")
    nit = models.CharField(max_length=20, unique=True, verbose_name="NIT")
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basic')
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nombre} ({self.get_plan_display()})"


# ════════════════════════════════════════════════════════════
# 2. MÓDULO AUTH — USUARIO
# ════════════════════════════════════════════════════════════
class Usuario(TimeStampedModel):
    """
    Operador del sistema (no es el cliente comprador).
    Pertenece a una empresa y tiene un rol que define sus permisos.
    """

    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('vendedor', 'Vendedor'),
        ('bodeguero', 'Bodeguero'),
    ]

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='usuarios',
        verbose_name="Empresa"
    )
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    password_hash = models.CharField(
        max_length=255,
        help_text="En producción se delega al sistema de auth de Django."
    )
    rol = models.CharField(max_length=20, choices=ROLE_CHOICES, default='vendedor')
    activo = models.BooleanField(default=True)
    ultimo_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ['nombre']
        # El email es único DENTRO de cada empresa, no globalmente
        unique_together = ('empresa', 'email')

    def __str__(self):
        return f"{self.nombre} · {self.get_rol_display()} ({self.empresa.nombre})"


# ════════════════════════════════════════════════════════════
# 3. MÓDULO INVENTARIO — CATEGORIA + PRODUCTO
# ════════════════════════════════════════════════════════════
class Categoria(TimeStampedModel):
    """Clasificación de productos dentro de una empresa."""

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='categorias'
    )
    nombre = models.CharField(max_length=80)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        unique_together = ('empresa', 'nombre')
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(TimeStampedModel):
    """Producto del inventario. Núcleo del módulo de ventas."""

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='productos'
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,  # si se borra la categoría, el producto sobrevive
        null=True,
        blank=True,
        related_name='productos'
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    sku = models.CharField(
        max_length=50,
        verbose_name="SKU",
        help_text="Código único del producto"
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Precio (COP)"
    )
    stock = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=10, verbose_name="Stock mínimo")
    imagen = models.ImageField(
        upload_to='productos/%Y/%m/',
        blank=True,
        null=True
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        unique_together = ('empresa', 'sku')
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['empresa', 'activo']),
            models.Index(fields=['stock']),
        ]

    def __str__(self):
        return f"{self.nombre} (stock: {self.stock})"

    @property
    def stock_bajo(self):
        """True si el stock está en el mínimo o por debajo."""
        return self.stock <= self.stock_minimo


# ════════════════════════════════════════════════════════════
# 4. MÓDULO VENTAS — CLIENTE
# ════════════════════════════════════════════════════════════
class Cliente(TimeStampedModel):
    """
    Comprador del negocio (entidad de dominio, distinta de Usuario).
    Puede vincularse opcionalmente a un Usuario si el cliente se registra.
    """

    TIPO_DOC_CHOICES = [
        ('CC', 'Cédula de Ciudadanía'),
        ('NIT', 'NIT'),
        ('CE', 'Cédula de Extranjería'),
        ('PAS', 'Pasaporte'),
    ]

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='clientes'
    )
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='perfil_cliente',
        help_text="Vínculo opcional si el cliente también es usuario del sistema."
    )
    nombre = models.CharField(max_length=120)
    tipo_documento = models.CharField(
        max_length=10,
        choices=TIPO_DOC_CHOICES,
        default='CC'
    )
    numero_documento = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    ciudad = models.CharField(max_length=80, blank=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        unique_together = ('empresa', 'tipo_documento', 'numero_documento')
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.tipo_documento} {self.numero_documento})"

    @property
    def total_compras(self):
        """Suma el total de todas las ventas completadas de este cliente."""
        from django.db.models import Sum
        total = self.ventas.filter(
            deleted_at__isnull=True,
            estado='completada'
        ).aggregate(Sum('total'))['total__sum']
        return total or 0


# ════════════════════════════════════════════════════════════
# 5. MÓDULO VENTAS — VENTA
# ════════════════════════════════════════════════════════════
class Venta(TimeStampedModel):
    """Transacción de venta. Genera número de factura automático."""

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completada', 'Completada'),
        ('anulada', 'Anulada'),
    ]

    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia bancaria'),
        ('nequi', 'Nequi'),
        ('daviplata', 'Daviplata'),
        ('tarjeta', 'Tarjeta'),
        ('otro', 'Otro'),
    ]

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='ventas'
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,  # no se puede borrar un cliente con ventas
        related_name='ventas'
    )
    vendedor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas_realizadas'
    )
    numero_factura = models.CharField(max_length=50, unique=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Total (COP)"
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default='efectivo'
    )
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['empresa', '-fecha']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        return f"Factura {self.numero_factura} · {self.cliente.nombre} (${self.total})"

    def _generar_numero_factura(self):
        """
        Genera un número de factura legible y único:
        Formato:  <8 chars del id de empresa>-<AAAAMMDD>-<consecutivo>
        Ej:       1A2B3C4D-20260630-00007
        """
        # timezone.localtime() respeta TIME_ZONE ('America/Bogota').
        # Usar datetime.now() daria una fecha sin zona horaria (naive),
        # que con USE_TZ=True puede dar el dia equivocado de madrugada.
        fecha = timezone.localtime().strftime('%Y%m%d')
        consecutivo = Venta.objects.filter(empresa=self.empresa).count() + 1
        prefijo = self.empresa.id.hex[:8].upper()
        return f"{prefijo}-{fecha}-{consecutivo:05d}"

    def save(self, *args, **kwargs):
        # Asignar número de factura solo la primera vez
        if not self.numero_factura:
            self.numero_factura = self._generar_numero_factura()
        super().save(*args, **kwargs)


# ════════════════════════════════════════════════════════════
# PERFIL — puente entre la autenticación de Django y la Empresa
# ════════════════════════════════════════════════════════════
class Perfil(models.Model):
    """
    Vincula un User de Django (que maneja login y contraseñas de forma
    segura) con una Empresa del sistema.

    ¿Por qué no usar el modelo Usuario para login?
    Porque reinventar el hashing de contraseñas y las sesiones sería un
    error grave de seguridad. Django ya lo hace bien: aquí solo conectamos
    ese User con la empresa a la que pertenece.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil'
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='perfiles'
    )
    es_propietario = models.BooleanField(
        default=False,
        help_text="True si este usuario registró la empresa (empresario)."
    )

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"

    def __str__(self):
        return f"{self.user.username} → {self.empresa.nombre}"
