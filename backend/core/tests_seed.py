"""Fase A3: aislamiento de los datos de demostracion.

Todo seed de pruebas/demo vive en management commands (seed_demo,
seed_masivo) y NUNCA se corre en produccion salvo --force explicito:
con DEBUG=False los comandos abortan con CommandError.
"""
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from core.management.commands.seed_demo import Command as SeedDemo
from core.management.commands.seed_masivo import Command as SeedMasivo


class SeedDemoGuardTest(TestCase):
    def test_rechaza_en_produccion(self):
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command(SeedDemo())

    def test_flag_force_omite_la_proteccion(self):
        with override_settings(DEBUG=False):
            call_command(SeedDemo(), force=True)

    def test_debug_true_permite_sin_flag(self):
        with override_settings(DEBUG=True):
            call_command(SeedDemo())

    def test_personal_demo_queda_con_password_usable(self):
        from django.contrib.auth.models import User

        with override_settings(DEBUG=True):
            call_command(SeedDemo())
        luis = User.objects.get(username='luis@elprogreso.co')
        self.assertTrue(luis.has_usable_password())
        self.assertTrue(luis.check_password('demo12345'))
        self.assertEqual(luis.perfil.empresa.nit, '900123456')

    def test_rerun_no_pisa_una_password_ya_configurada(self):
        from django.contrib.auth.models import User

        with override_settings(DEBUG=True):
            call_command(SeedDemo())
        luis = User.objects.get(username='luis@elprogreso.co')
        luis.set_password('Cambiada123')
        luis.save(update_fields=['password'])
        with override_settings(DEBUG=True):
            call_command(SeedDemo())
        luis.refresh_from_db()
        self.assertTrue(luis.check_password('Cambiada123'))


class SeedMasivoGuardTest(TestCase):
    def test_rechaza_en_produccion(self):
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command(SeedMasivo())

    def test_flag_force_omite_la_proteccion(self):
        with override_settings(DEBUG=False):
            # cantidad=1: solo crea la empresa demo via seed_demo(force) y
            # un producto; el guard no debe bloquear.
            call_command(SeedMasivo(), force=True, cantidad=1)

    def test_debug_true_permite_sin_flag(self):
        with override_settings(DEBUG=True):
            call_command(SeedMasivo(), cantidad=0)