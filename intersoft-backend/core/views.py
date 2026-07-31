"""
Vistas de InterSoft.

Patrón usado: vistas basadas en funciones (FBV), más explícitas y fáciles
de leer para quien está aprendiendo que las vistas basadas en clases (CBV).

NOTA sobre multi-tenancy:
  En esta fase, para simplificar, tomamos la PRIMERA empresa como contexto
  (Empresa.objects.first()). En la fase de autenticación, la empresa saldrá
  del usuario logueado (request.user.empresa). Hay un helper _empresa_actual()
  centralizado para que ese cambio sea de una sola línea en el futuro.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, F, Count

from .models import Empresa, Usuario, Categoria, Producto, Cliente, Venta, Perfil
from .forms import ProductoForm, ClienteForm, VentaForm, RegistroEmpresarioForm


# ════════════════════════════════════════════════════════════
# HELPER — empresa de contexto (multi-tenant)
# ════════════════════════════════════════════════════════════
def _empresa_actual(request):
    """
    Devuelve la empresa del usuario autenticado a través de su Perfil.
    Cada empresario solo ve los datos de SU empresa (aislamiento tenant).
    """
    if request.user.is_authenticated and hasattr(request.user, 'perfil'):
        return request.user.perfil.empresa
    return None


# ════════════════════════════════════════════════════════════
# AUTENTICACIÓN — registro, login, logout
# ════════════════════════════════════════════════════════════
def registro_empresario(request):
    """
    Registro del empresario: crea el negocio y su cuenta de acceso.

    Todo ocurre dentro de una transacción atómica: si algo falla,
    NO queda ni la empresa a medias ni el usuario huérfano.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = RegistroEmpresarioForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            with transaction.atomic():
                # 1. Crear la empresa
                empresa = Empresa.objects.create(
                    nombre=data['empresa_nombre'],
                    nit=data['nit'],
                    email=data['empresa_email'],
                )
                # 2. Crear el User de Django (login seguro)
                user = User.objects.create_user(
                    username=data['username'],
                    password=data['password1'],
                    first_name=data['nombre'],
                    email=data['empresa_email'],
                )
                # 3. Vincular User ↔ Empresa
                Perfil.objects.create(user=user, empresa=empresa, es_propietario=True)

                # 4. Crear también su Usuario operador (rol admin) en el dominio
                Usuario.objects.create(
                    empresa=empresa, nombre=data['nombre'],
                    email=data['empresa_email'], rol='admin', password_hash='-'
                )

            # Iniciar sesión automáticamente tras registrarse
            login(request, user)
            messages.success(request, f"¡Bienvenido, {data['nombre']}! Tu negocio quedó registrado.")
            return redirect('core:dashboard')
    else:
        form = RegistroEmpresarioForm()

    return render(request, 'core/registro.html', {'form': form})


def login_view(request):
    """Inicio de sesión con el sistema de auth de Django."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('core:dashboard')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()

    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    """Cierra la sesión y vuelve al login."""
    logout(request)
    messages.info(request, "Cerraste sesión correctamente.")
    return redirect('core:login')


# ════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════
@login_required
def dashboard(request):
    empresa = _empresa_actual(request)

    if not empresa:
        return render(request, 'core/sin_datos.html')

    ventas_completadas = Venta.objects.filter(
        empresa=empresa, estado='completada', deleted_at__isnull=True
    )

    context = {
        'empresa': empresa,
        'ingresos_totales': ventas_completadas.aggregate(Sum('total'))['total__sum'] or 0,
        'num_ventas': ventas_completadas.count(),
        'num_productos': Producto.objects.filter(empresa=empresa, activo=True).count(),
        'num_clientes': Cliente.objects.filter(empresa=empresa).count(),
        'productos_stock_bajo': Producto.objects.filter(
            empresa=empresa, activo=True, stock__lte=F('stock_minimo')
        ),
        'ultimas_ventas': ventas_completadas.order_by('-fecha')[:5],
    }
    return render(request, 'core/dashboard.html', context)


# ════════════════════════════════════════════════════════════
# PRODUCTOS — listar, crear, editar
# ════════════════════════════════════════════════════════════
@login_required
def lista_productos(request):
    empresa = _empresa_actual(request)
    productos = Producto.objects.filter(empresa=empresa, deleted_at__isnull=True)

    # Filtro por categoría
    cat_id = request.GET.get('categoria')
    if cat_id:
        productos = productos.filter(categoria_id=cat_id)

    # Búsqueda por nombre o SKU
    q = request.GET.get('q')
    if q:
        productos = productos.filter(nombre__icontains=q)

    context = {
        'empresa': empresa,
        'productos': productos,
        'categorias': Categoria.objects.filter(empresa=empresa),
    }
    return render(request, 'core/lista_productos.html', context)


@login_required
def crear_producto(request):
    empresa = _empresa_actual(request)

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        # Limitar categorías a las de esta empresa
        form.fields['categoria'].queryset = Categoria.objects.filter(empresa=empresa)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.empresa = empresa
            producto.save()
            messages.success(request, f"Producto '{producto.nombre}' creado correctamente.")
            return redirect('core:lista_productos')
    else:
        form = ProductoForm()
        form.fields['categoria'].queryset = Categoria.objects.filter(empresa=empresa)

    return render(request, 'core/form_producto.html', {'form': form, 'empresa': empresa, 'accion': 'Crear'})


@login_required
def editar_producto(request, pk):
    empresa = _empresa_actual(request)
    producto = get_object_or_404(Producto, id=pk, empresa=empresa)

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        form.fields['categoria'].queryset = Categoria.objects.filter(empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado.")
            return redirect('core:lista_productos')
    else:
        form = ProductoForm(instance=producto)
        form.fields['categoria'].queryset = Categoria.objects.filter(empresa=empresa)

    return render(request, 'core/form_producto.html',
                  {'form': form, 'empresa': empresa, 'accion': 'Editar'})


# ════════════════════════════════════════════════════════════
# CLIENTES — listar, crear
# ════════════════════════════════════════════════════════════
@login_required
def lista_clientes(request):
    empresa = _empresa_actual(request)
    clientes = Cliente.objects.filter(empresa=empresa, deleted_at__isnull=True)
    return render(request, 'core/lista_clientes.html',
                  {'clientes': clientes, 'empresa': empresa})


@login_required
def crear_cliente(request):
    empresa = _empresa_actual(request)

    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.empresa = empresa
            cliente.save()
            messages.success(request, f"Cliente '{cliente.nombre}' creado.")
            return redirect('core:lista_clientes')
    else:
        form = ClienteForm()

    return render(request, 'core/form_cliente.html',
                  {'form': form, 'empresa': empresa, 'accion': 'Crear'})


# ════════════════════════════════════════════════════════════
# VENTAS — listar, crear
# ════════════════════════════════════════════════════════════
@login_required
def lista_ventas(request):
    empresa = _empresa_actual(request)
    ventas = Venta.objects.filter(empresa=empresa, deleted_at__isnull=True)

    estado = request.GET.get('estado')
    if estado:
        ventas = ventas.filter(estado=estado)

    context = {
        'empresa': empresa,
        'ventas': ventas,
        'estados': Venta.ESTADO_CHOICES,
    }
    return render(request, 'core/lista_ventas.html', context)


@login_required
def crear_venta(request):
    empresa = _empresa_actual(request)

    if request.method == 'POST':
        form = VentaForm(request.POST)
        form.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa)
        form.fields['vendedor'].queryset = Usuario.objects.filter(empresa=empresa)
        if form.is_valid():
            venta = form.save(commit=False)
            venta.empresa = empresa
            venta.save()
            messages.success(request, f"Venta {venta.numero_factura} registrada.")
            return redirect('core:lista_ventas')
    else:
        form = VentaForm()
        form.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa)
        form.fields['vendedor'].queryset = Usuario.objects.filter(empresa=empresa)

    return render(request, 'core/form_venta.html',
                  {'form': form, 'empresa': empresa, 'accion': 'Registrar'})
