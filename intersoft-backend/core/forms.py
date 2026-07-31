"""
Formularios de InterSoft.

Usar ModelForm evita repetir la definición de campos: Django los deriva
directamente del modelo y aplica validación automática.
"""

from django import forms
from django.contrib.auth.models import User
from .models import Producto, Cliente, Venta, Categoria


# ════════════════════════════════════════════════════════════
# REGISTRO DE EMPRESARIO
# ════════════════════════════════════════════════════════════
class RegistroEmpresarioForm(forms.Form):
    """
    Formulario de registro para el empresario (dueño del negocio).

    No es un ModelForm porque toca DOS modelos a la vez: crea el User de
    Django (para el login) y la Empresa (el negocio). La vista se encarga
    de guardarlos juntos en una transacción.
    """
    # Datos del negocio
    empresa_nombre = forms.CharField(
        label="Nombre del negocio", max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Tienda El Progreso'})
    )
    nit = forms.CharField(
        label="NIT", max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 900123456'})
    )
    empresa_email = forms.EmailField(
        label="Email del negocio",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contacto@negocio.co'})
    )

    # Datos de acceso del empresario
    nombre = forms.CharField(
        label="Tu nombre", max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre completo'})
    )
    username = forms.CharField(
        label="Usuario", max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario para entrar'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mínimo 8 caracteres'})
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repite la contraseña'})
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ese nombre de usuario ya está en uso.")
        return username

    def clean_nit(self):
        from .models import Empresa
        nit = self.cleaned_data['nit']
        if Empresa.objects.filter(nit=nit).exists():
            raise forms.ValidationError("Ya existe una empresa registrada con ese NIT.")
        return nit

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Las contraseñas no coinciden.")
        if p1 and len(p1) < 8:
            self.add_error('password1', "La contraseña debe tener al menos 8 caracteres.")
        return cleaned


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['categoria', 'nombre', 'descripcion', 'sku',
                  'precio', 'stock', 'stock_minimo', 'imagen', 'activo']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'tipo_documento', 'numero_documento',
                  'email', 'telefono', 'direccion', 'ciudad']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'ciudad': forms.TextInput(attrs={'class': 'form-control'}),
        }


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['cliente', 'vendedor', 'total', 'estado', 'metodo_pago', 'notas']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'vendedor': forms.Select(attrs={'class': 'form-select'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
