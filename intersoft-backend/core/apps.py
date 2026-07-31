from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Núcleo de InterSoft'

    def ready(self):
        # Importa las señales cuando la app esté lista
        import core.signals  # noqa
