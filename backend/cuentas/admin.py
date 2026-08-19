from django.contrib import admin
from .models import Perfil, TokenRecuperacion


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("usuario", "empresa", "rol", "intentos_fallidos", "fecha_desbloqueo")
    list_filter = ("rol", "empresa")
    actions = ["desbloquear"]

    @admin.action(description="Desbloquear cuentas seleccionadas")
    def desbloquear(self, request, queryset):
        for perfil in queryset:
            perfil.reiniciar_intentos()


admin.site.register(TokenRecuperacion)
