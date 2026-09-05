import re
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from core.models import Cliente, Empresa
from .models import Perfil, Rol

Usuario = get_user_model()


def validar_fuerza_password(valor: str) -> str:
    faltantes = []
    if len(valor) < 8:
        faltantes.append("8 caracteres")
    if not re.search(r"[A-Z]", valor):
        faltantes.append("una mayuscula")
    if not re.search(r"[a-z]", valor):
        faltantes.append("una minuscula")
    if not re.search(r"[0-9]", valor):
        faltantes.append("un numero")
    if faltantes:
        raise serializers.ValidationError("La contraseña necesita: " + ", ".join(faltantes) + ".")
    return valor


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, valor):
        return valor.strip().lower()


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nueva = serializers.CharField(write_only=True, validators=[validar_fuerza_password])


class DatosEmpresaSerializer(serializers.Serializer):
    nombre = serializers.CharField(min_length=3, max_length=150)
    nit = serializers.RegexField(r"^\d{9}$", error_messages={"invalid": "El NIT son 9 digitos."})

    def validate_nit(self, valor):
        if Empresa.objects.filter(nit=valor).exists():
            raise serializers.ValidationError("Ya existe un negocio registrado con este NIT.")
        return valor


class DatosAdministradorSerializer(serializers.Serializer):
    nombre = serializers.CharField(min_length=3, max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validar_fuerza_password])

    def validate_email(self, valor):
        valor = valor.strip().lower()
        if Usuario.objects.filter(email__iexact=valor).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return valor


class RegistroSerializer(serializers.Serializer):
    empresa = DatosEmpresaSerializer()
    administrador = DatosAdministradorSerializer()

    @transaction.atomic
    def create(self, validated_data):
        datos_empresa = validated_data["empresa"]
        datos_admin = validated_data["administrador"]

        empresa = Empresa.objects.create(nombre=datos_empresa["nombre"], nit=datos_empresa["nit"])

        partes = datos_admin["nombre"].split(" ", 1)
        usuario = Usuario.objects.create_user(
            username=datos_admin["email"], email=datos_admin["email"],
            password=datos_admin["password"], first_name=partes[0],
            last_name=partes[1] if len(partes) > 1 else "",
        )
        Perfil.objects.create(usuario=usuario, empresa=empresa,
                              rol=Rol.de_nombre("ADMINISTRADOR"), es_propietario=True)
        return usuario


class RegistroCompradorSerializer(serializers.Serializer):
    """Alta de un comprador del marketplace (rol CLIENTE sin empresa).

    Crea la cuenta de usuario mas su Cliente global (empresa=None). El
    comprador no pertenece a ninguna empresa vendedora y puede comprar
    productos de todas las empresas del marketplace.
    """
    nombre = serializers.CharField(min_length=3, max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validar_fuerza_password])
    tipo_documento = serializers.ChoiceField(choices=Cliente.TIPO_DOC_CHOICES, default='CC')
    numero_documento = serializers.CharField(min_length=3, max_length=20)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    direccion = serializers.CharField(required=False, allow_blank=True, default='')
    ciudad = serializers.CharField(max_length=80, required=False, allow_blank=True, default='')

    def validate_email(self, valor):
        valor = valor.strip().lower()
        if Usuario.objects.filter(email__iexact=valor).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return valor

    def validate(self, datos):
        tipo = datos.get("tipo_documento", "CC")
        numero = datos.get("numero_documento")
        # En el marketplace (empresa=None) el documento no debe estar ya en uso
        if Cliente.objects.filter(empresa__isnull=True, deleted_at__isnull=True,
                                  tipo_documento=tipo, numero_documento=numero).exists():
            raise serializers.ValidationError({
                "numero_documento": "El documento ya esta registrado para un comprador.",
            })
        return datos

    @transaction.atomic
    def create(self, validated_data):
        partes = validated_data["nombre"].split(" ", 1)
        usuario = Usuario.objects.create_user(
            username=validated_data["email"], email=validated_data["email"],
            password=validated_data["password"], first_name=partes[0],
            last_name=partes[1] if len(partes) > 1 else "",
        )
        Perfil.objects.create(usuario=usuario, empresa=None, rol=Rol.de_nombre("CLIENTE"))
        Cliente.objects.create(
            usuario=usuario, empresa=None, nombre=validated_data["nombre"],
            tipo_documento=validated_data["tipo_documento"],
            numero_documento=validated_data["numero_documento"],
            email=validated_data["email"],
            telefono=validated_data["telefono"],
            direccion=validated_data["direccion"],
            ciudad=validated_data["ciudad"],
        )
        return usuario


class SolicitarRecuperacionSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, valor):
        return valor.strip().lower()


class ConfirmarRecuperacionSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, validators=[validar_fuerza_password])
