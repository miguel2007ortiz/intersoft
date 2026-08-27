from django.contrib import admin

from .models import ActividadUsuario, Perfil, Permiso, Rol, RolPermiso, TokenRecuperacion


class RolPermisoInline(admin.TabularInline):
    model = RolPermiso
    extra = 0


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "total_permisos")
    search_fields = ("nombre",)
    inlines = [RolPermisoInline]

    @admin.display(description="Permisos")
    def total_permisos(self, obj):
        return obj.rol_permisos.count()


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descripcion")
    search_fields = ("codigo",)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("usuario", "empresa", "rol", "intentos_fallidos", "fecha_desbloqueo")
    list_filter = ("rol", "empresa")
    actions = ["desbloquear"]

    @admin.action(description="Desbloquear cuentas seleccionadas")
    def desbloquear(self, request, queryset):
        for perfil in queryset:
            perfil.reiniciar_intentos()


@admin.register(ActividadUsuario)
class ActividadUsuarioAdmin(admin.ModelAdmin):
    """Auditoria: solo lectura."""
    list_display = ("usuario", "accion", "detalle", "fecha")
    list_filter = ("accion", "fecha")
    search_fields = ("usuario__email", "accion", "detalle")
    date_hierarchy = "fecha"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(TokenRecuperacion)
