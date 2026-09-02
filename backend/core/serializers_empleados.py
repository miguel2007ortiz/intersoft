"""Serializers del modulo Empleados (personal interno).

Convenciones (clonadas de serializers_catalogo.py / Clientes):
- respuestas de error con {"codigo", "detalle", "errores"};
- documento (tipo_documento, numero_documento) unico por empresa, incluidos
  los perfiles inactivos (constraint perfil_empresa_documento_unico);
- el rol solo puede ser uno visible para la empresa (globales del sistema
  o personalizados de la propia empresa) y nunca CLIENTE."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from cuentas.models import Perfil, Rol
from cuentas.serializers import validar_fuerza_password

from .serializers_catalogo import VentaResumenSerializer

Usuario = get_user_model()

ROLES_EXCLUIDOS = {"CLIENTE"}


def roles_internos_visibles(empresa):
    """Roles asignables a personal: globales del sistema (empresa=None) o
    personalizados de la empresa, nunca CLIENTE."""
    return (Rol.objects.filter(Q(empresa=empresa) | Q(empresa__isnull=True))
            .exclude(nombre__in=ROLES_EXCLUIDOS))


class EmpleadoLecturaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nombre = serializers.SerializerMethodField()
    email = serializers.EmailField(source="usuario.email")
    rol = serializers.CharField(source="rol.nombre")
    tipo_documento = serializers.CharField(allow_null=True)
    numero_documento = serializers.CharField(allow_null=True)
    telefono = serializers.CharField()
    cargo = serializers.CharField()
    fecha_ingreso = serializers.DateField(allow_null=True)
    es_propietario = serializers.BooleanField()
    activo = serializers.SerializerMethodField()
    ultimo_login = serializers.DateTimeField(source="usuario.last_login")

    def get_nombre(self, perfil) -> str:
        return (perfil.usuario.get_full_name() or perfil.usuario.username).strip()

    def get_activo(self, perfil) -> bool:
        return bool(perfil.deleted_at is None and perfil.usuario.is_active)


class EmpleadoDetalleSerializer(EmpleadoLecturaSerializer):
    """Igual que el listado, mas las ultimas 5 ventas registradas por el
    empleado (historial rapido en su ficha).

    El contexto espera `empresa` (la empresa del usuario que consulta) para
    aislar el historial de ventas a esa empresa: asi un tenant nunca ve las
    ventas que este usuario registro como vendedor en OTRA empresa."""
    ultimas_ventas = serializers.SerializerMethodField()

    def get_ultimas_ventas(self, perfil):
        empresa = (self.context.get("empresa") if self.context
                   else perfil.empresa)
        ventas = (perfil.usuario.ventas_realizadas
                  .filter(empresa=empresa, deleted_at__isnull=True)
                  .order_by("-fecha")[:5])
        return VentaResumenSerializer(ventas, many=True).data


class EmpleadoEscrituraSerializer(serializers.Serializer):
    """Crea o edita un Perfil de personal + su User asociado.

    `password` solo se usa al crear (contrasena temporal, RN-09): en edicion
    el cambio de clave propio pasa por /api/auth/cambiar-password/, no por
    aqui. `rol` recibe el NOMBRE (ADMINISTRADOR/EMPLEADO/personalizado)."""

    nombre = serializers.CharField(min_length=3, max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=False,
                                     validators=[validar_fuerza_password])
    rol = serializers.CharField()
    tipo_documento = serializers.ChoiceField(choices=Perfil.TIPO_DOC_CHOICES,
                                             required=False, allow_null=True)
    numero_documento = serializers.CharField(required=False, allow_null=True,
                                             allow_blank=True, max_length=20)
    telefono = serializers.CharField(required=False, allow_blank=True, max_length=20)
    cargo = serializers.CharField(required=False, allow_blank=True, max_length=80)
    fecha_ingreso = serializers.DateField(required=False, allow_null=True)

    def validate_rol(self, valor):
        nombre = (valor or "").strip().upper()
        empresa = self.context["empresa"]
        if not roles_internos_visibles(empresa).filter(nombre=nombre).exists():
            raise serializers.ValidationError(
                "El rol indicado no existe o no aplica a personal interno.")
        return nombre

    def validate_email(self, valor):
        valor = valor.strip().lower()
        consulta = Usuario.objects.filter(email__iexact=valor)
        if self.instance is not None:
            consulta = consulta.exclude(pk=self.instance.usuario_id)
        if consulta.exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta con este correo. Usa otro.")
        return valor

    def validate(self, datos):
        # La contrasena temporal la resuelve la vista antes de llegar aqui
        # (la genera el servidor si el ADMINISTRADOR no mando una, RN-09):
        # a este punto siempre debe venir una si es creacion.
        tipo = datos.get("tipo_documento",
                         getattr(self.instance, "tipo_documento", None))
        numero = datos.get("numero_documento",
                           getattr(self.instance, "numero_documento", None))
        if tipo and numero:
            # Igual que Cliente: la constraint de BD no distingue activos de
            # inactivos, asi que hay que detectar el conflicto aqui tambien
            # contra perfiles desactivados (si no, el create() de abajo
            # revienta con IntegrityError).
            consulta = Perfil.objects.filter(empresa=self.context["empresa"],
                                             tipo_documento=tipo,
                                             numero_documento=numero)
            if self.instance:
                consulta = consulta.exclude(pk=self.instance.pk)
            otro = consulta.select_related("usuario").first()
            if otro is not None:
                activo = otro.deleted_at is None and otro.usuario.is_active
                if activo:
                    raise serializers.ValidationError({
                        "numero_documento":
                            f"El documento {tipo} {numero} ya esta registrado para "
                            f"{otro.usuario.get_full_name() or otro.usuario.email} "
                            "(registro en conflicto).",
                    })
                raise serializers.ValidationError({
                    "numero_documento":
                        f"Ya existe un empleado inactivo con el documento {tipo} {numero}. "
                        "Reactivalo en vez de crear uno nuevo.",
                    "empleado_inactivo_id": str(otro.id),
                })
        return datos

    def create(self, datos_validados):
        empresa = self.context["empresa"]
        rol = roles_internos_visibles(empresa).get(nombre=datos_validados["rol"])
        partes = datos_validados["nombre"].split(" ", 1)
        with transaction.atomic():
            usuario = Usuario.objects.create_user(
                username=datos_validados["email"], email=datos_validados["email"],
                password=datos_validados["password"], first_name=partes[0],
                last_name=partes[1] if len(partes) > 1 else "")
            perfil = Perfil.objects.create(
                usuario=usuario, empresa=empresa, rol=rol,
                tipo_documento=datos_validados.get("tipo_documento") or None,
                numero_documento=datos_validados.get("numero_documento") or None,
                telefono=datos_validados.get("telefono", ""),
                cargo=datos_validados.get("cargo", ""),
                fecha_ingreso=datos_validados.get("fecha_ingreso"),
                debe_cambiar_password=True,
            )
        return perfil

    def update(self, instancia, datos_validados):
        with transaction.atomic():
            usuario = instancia.usuario
            if "nombre" in datos_validados:
                partes = datos_validados["nombre"].split(" ", 1)
                usuario.first_name = partes[0]
                usuario.last_name = partes[1] if len(partes) > 1 else ""
            if "email" in datos_validados:
                usuario.email = datos_validados["email"]
                usuario.username = datos_validados["email"]
            usuario.save()

            if "rol" in datos_validados:
                instancia.rol = roles_internos_visibles(
                    self.context["empresa"]).get(nombre=datos_validados["rol"])
            # tipo_documento/numero_documento son nullable (MySQL trata NULL
            # como distinto en la constraint de unicidad); telefono/cargo son
            # CharField blank=True normales, "" es su valor vacio valido.
            for campo in ("tipo_documento", "numero_documento"):
                if campo in datos_validados:
                    valor = datos_validados[campo]
                    setattr(instancia, campo, valor or None)
            for campo in ("telefono", "cargo", "fecha_ingreso"):
                if campo in datos_validados:
                    setattr(instancia, campo, datos_validados[campo])
            instancia.save()
        return instancia
