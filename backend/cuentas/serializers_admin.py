"""Serializers de la fase 2: administracion de usuarios y roles.
Solo los consume el rol ADMINISTRADOR (ver cuentas/permissions.py)."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Permiso, Perfil, Rol
from .serializers import validar_fuerza_password

Usuario = get_user_model()

# Roles base de la plataforma: no se renombran ni se eliminan
ROLES_DEL_SISTEMA = {"ADMINISTRADOR", "EMPLEADO", "CLIENTE"}


class UsuarioLecturaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nombre = serializers.CharField(source="usuario.get_full_name")
    email = serializers.EmailField(source="usuario.email")
    rol = serializers.CharField(source="rol.nombre")
    activo = serializers.BooleanField(source="usuario.is_active")
    es_propietario = serializers.BooleanField()
    ultimo_login = serializers.DateTimeField(source="usuario.last_login")


class UsuarioCreacionSerializer(serializers.Serializer):
    """Valida datos para crear una cuenta con su perfil (rol obligatorio)."""

    nombre = serializers.CharField(min_length=3, max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validar_fuerza_password])
    rol = serializers.CharField()

    def validate_rol(self, valor):
        nombre = (valor or "").strip().upper()
        empresa = self.context.get("empresa")
        if not empresa or not Rol.objects.filter(
                nombre=nombre).filter(empresa=empresa).exists() \
                and not Rol.objects.filter(nombre=nombre, empresa__isnull=True).exists():
            raise serializers.ValidationError("El rol indicado no existe.")
        return nombre

    def validate_email(self, valor):
        valor = valor.strip().lower()
        if Usuario.objects.filter(email__iexact=valor).exists():
            # Regla fase 2: correo duplicado se rechaza y se pide otro
            raise serializers.ValidationError("Ya existe una cuenta con este correo. Usa otro.")
        return valor


class UsuarioEdicionSerializer(serializers.Serializer):
    nombre = serializers.CharField(min_length=3, max_length=120)
    email = serializers.EmailField()
    rol = serializers.CharField()
    password = serializers.CharField(write_only=True, required=False,
                                     validators=[validar_fuerza_password])

    def validate_rol(self, valor):
        nombre = (valor or "").strip().upper()
        empresa = self.context.get("empresa")
        visible = Rol.objects.filter(nombre=nombre, empresa__isnull=True).exists() or (
            empresa is not None and Rol.objects.filter(
                nombre=nombre, empresa=empresa).exists())
        if not visible:
            raise serializers.ValidationError("El rol indicado no existe.")
        return nombre

    def validate_email(self, valor):
        valor = valor.strip().lower()
        consulta = Usuario.objects.filter(email__iexact=valor)
        if self.instance is not None:
            consulta = consulta.exclude(pk=self.instance.usuario.pk)
        if consulta.exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo. Usa otro.")
        return valor


class RolLecturaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField()
    permisos = serializers.SerializerMethodField()
    total_usuarios_activos = serializers.SerializerMethodField()
    es_sistema = serializers.SerializerMethodField()

    def get_permisos(self, rol) -> list:
        return list(rol.rol_permisos.select_related("permiso")
                    .values_list("permiso__codigo", flat=True))

    def get_total_usuarios_activos(self, rol) -> int:
        return Perfil.objects.filter(rol=rol, deleted_at__isnull=True,
                                     usuario__is_active=True).count()

    def get_es_sistema(self, rol) -> bool:
        return rol.nombre in ROLES_DEL_SISTEMA


class RolEscrituraSerializer(serializers.Serializer):
    nombre = serializers.CharField(min_length=3, max_length=30)
    descripcion = serializers.CharField(required=False, allow_blank=True,
                                        max_length=200, default="")
    permisos = serializers.ListField(child=serializers.CharField(),
                                     required=False, default=list)

    def validate_nombre(self, valor):
        valor = valor.strip().upper()
        empresa = self.context.get("empresa") if self.context else None

        # Un rol no puede usar el nombre de un rol base del sistema.
        if valor in ROLES_DEL_SISTEMA:
            raise serializers.ValidationError("Este nombre esta reservado. Elige otro.")

        consulta = Rol.objects.filter(nombre__iexact=valor)
        if empresa is not None:
            # La unicidad de los roles personalizados es por empresa; los
            # que son de otras empresas no colisionan.
            consulta = consulta.filter(empresa=empresa)
        if self.instance is not None:
            consulta = consulta.exclude(pk=self.instance.pk)
        if consulta.exists():
            raise serializers.ValidationError("Ya existe un rol con este nombre.")
        return valor

    def validate_permisos(self, codigos):
        codigos = [c.strip() for c in codigos if c.strip()]
        catalogo = set(Permiso.objects.values_list("codigo", flat=True))
        desconocidos = [c for c in codigos if c not in catalogo]
        if desconocidos:
            raise serializers.ValidationError(
                "Permisos inexistentes: " + ", ".join(desconocidos))
        return sorted(set(codigos))
