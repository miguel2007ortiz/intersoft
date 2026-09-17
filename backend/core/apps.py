from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Nucleo de InterSoft'

    def ready(self):
        import core.signals  # noqa
        # Emision automatica del recibo al completarse una venta. Modulo
        # aparte de signals.py para no cruzarse con el trabajo en curso ahi.
        import core.recibos  # noqa
