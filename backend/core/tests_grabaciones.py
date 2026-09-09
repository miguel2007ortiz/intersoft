"""Fase 9 (camaras): catalogo de grabaciones con metadatos en BD.

Cubre `Grabacion` + `services/camaras.sincronizar_grabaciones` (escaneo de
`streams/` bajo MEDIA_ROOT), el command `sincronizar_grabaciones` y el
endpoint `GET /api/camaras/<id>/grabaciones/` (paginado, aislado por tenant,
solo ADMINISTRADOR).
"""

import os
import tempfile
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from cuentas.models import Perfil, Rol

from .models import Camara, Empresa, Grabacion
from .services import camaras as servicio_camaras


def _crear_archivo(base, empresa, camara, fecha='2026-09-01', hora='12_00',
                   tamano=1024):
    """Deja un .mp4 falso en `streams/{empresa}/{camara}/{fecha}/`."""
    dir_fecha = os.path.join(str(base), 'streams', empresa.id.hex,
                             camara.id.hex, fecha)
    os.makedirs(dir_fecha, exist_ok=True)
    ruta = os.path.join(dir_fecha, f'{hora}.mp4')
    with open(ruta, 'wb') as fh:
        fh.write(b'x' * tamano)
    return ruta


class BaseGrabacionesTest(TestCase):
    """Empresas A/B + ADMINISTRADOR/EMPLEADO para probar aislamiento."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa_a = Empresa.objects.create(nombre='Empresa A', nit='900000001')
        cls.empresa_b = Empresa.objects.create(nombre='Empresa B', nit='900000002')
        cls.camara_a = Camara.objects.create(
            empresa=cls.empresa_a, nombre='Entrada A', ubicacion='Recepcion')
        cls.camara_b = Camara.objects.create(
            empresa=cls.empresa_b, nombre='Entrada B')

        cls.admin_a = User.objects.create_user(
            username='admin-a@test.co', email='admin-a@test.co',
            password='Clave12345')
        Perfil.objects.create(usuario=cls.admin_a, empresa=cls.empresa_a,
                              rol=Rol.de_nombre('ADMINISTRADOR'))
        cls.empleado_a = User.objects.create_user(
            username='emp-a@test.co', email='emp-a@test.co',
            password='Clave12345')
        Perfil.objects.create(usuario=cls.empleado_a, empresa=cls.empresa_a,
                              rol=Rol.de_nombre('EMPLEADO'))

    @classmethod
    def api_como(cls, usuario):
        api = APIClient()
        api.force_authenticate(usuario)
        return api

    def _media(self):
        """Activa un MEDIA_ROOT temporal y devuelve su ruta para el test."""
        tmp = tempfile.mkdtemp(prefix='media-cam-')
        override = self.settings(MEDIA_ROOT=tmp)
        override.enable()
        self.addCleanup(override.disable)
        return tmp


class SincronizarGrabacionesTest(BaseGrabacionesTest):
    def test_sincronizar_crea_metadatos_desde_disco(self):
        media = self._media()
        _crear_archivo(media, self.empresa_a, self.camara_a, hora='12_00', tamano=100)
        _crear_archivo(media, self.empresa_a, self.camara_a, hora='13_00', tamano=250)

        resumen = servicio_camaras.sincronizar_grabaciones()

        self.assertEqual(resumen['creadas'], 2)
        self.assertEqual(resumen['existentes'], 0)
        self.assertEqual(resumen['eliminadas'], 0)
        filas = Grabacion.objects.filter(camara=self.camara_a).order_by('hora')
        self.assertEqual(filas.count(), 2)
        self.assertEqual(filas[0].hora.strftime('%H_%M'), '12_00')
        self.assertEqual(filas[0].tamano_bytes, 100)
        self.assertEqual(filas[1].hora.strftime('%H_%M'), '13_00')
        self.assertEqual(filas[1].tamano_bytes, 250)
        self.assertTrue(filas[0].archivo.endswith('12_00.mp4'))

    def test_sincronizar_es_idempotente(self):
        media = self._media()
        _crear_archivo(media, self.empresa_a, self.camara_a)
        servicio_camaras.sincronizar_grabaciones()
        resumen = servicio_camaras.sincronizar_grabaciones()

        self.assertEqual(resumen['creadas'], 0)
        self.assertEqual(resumen['existentes'], 1)
        self.assertEqual(Grabacion.objects.count(), 1)

    def test_sincronizar_elimina_filas_sin_archivo(self):
        media = self._media()
        ruta = _crear_archivo(media, self.empresa_a, self.camara_a)
        servicio_camaras.sincronizar_grabaciones()
        os.remove(ruta)
        resumen = servicio_camaras.sincronizar_grabaciones()

        self.assertEqual(resumen['eliminadas'], 1)
        self.assertEqual(Grabacion.objects.count(), 0)

    def test_sincronizar_filtra_por_empresa(self):
        media = self._media()
        _crear_archivo(media, self.empresa_a, self.camara_a)
        _crear_archivo(media, self.empresa_b, self.camara_b)
        resumen = servicio_camaras.sincronizar_grabaciones(
            empresa=self.empresa_a)

        self.assertEqual(resumen['camaras'], 1)
        self.assertEqual(Grabacion.objects.count(), 1)
        self.assertEqual(Grabacion.objects.get().camara, self.camara_a)

    def test_sincronizar_filtra_por_camara(self):
        media = self._media()
        _crear_archivo(media, self.empresa_a, self.camara_a)
        _crear_archivo(media, self.empresa_b, self.camara_b)
        resumen = servicio_camaras.sincronizar_grabaciones(
            camara=self.camara_b)

        self.assertEqual(resumen['camaras'], 1)
        self.assertEqual(Grabacion.objects.count(), 1)
        self.assertEqual(Grabacion.objects.get().camara, self.camara_b)

    def test_sincronizar_ignora_no_mp4_y_fechas_malformadas(self):
        media = self._media()
        dir_fecha = os.path.join(str(media), 'streams',
                                 self.empresa_a.id.hex, self.camara_a.id.hex,
                                 'no-es-una-fecha')
        os.makedirs(dir_fecha, exist_ok=True)
        open(os.path.join(dir_fecha, 'raro.txt'), 'w').close()
        servicio_camaras.sincronizar_grabaciones()

        self.assertEqual(Grabacion.objects.count(), 0)

    def test_constraint_unico_camara_fecha_hora(self):
        Grabacion.objects.create(camara=self.camara_a, fecha='2026-09-01',
                                 hora='12:00', archivo='x/12_00.mp4')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Grabacion.objects.create(
                    camara=self.camara_a, fecha='2026-09-01', hora='12:00',
                    archivo='x/12_00.mp4')


class CamaraGrabacionesApiTest(BaseGrabacionesTest):
    def _sembrar(self, media, cantidad=2, fecha_base='2026-09-01'):
        """Crea cajas de grabaciones y las sincroniza contra la BD."""
        for i in range(cantidad):
            dia = fecha_base if i == 0 else \
                (date(2026, 9, 1) + timedelta(days=i)).isoformat()
            _crear_archivo(media, self.empresa_a, self.camara_a,
                           fecha=dia, hora=f'{12 + (i % 10):02d}_00',
                           tamano=100 + i)
        servicio_camaras.sincronizar_grabaciones()

    def test_listado_paginado_desde_la_mas_reciente(self):
        media = self._media()
        self._sembrar(media, cantidad=51)
        api = self.api_como(self.admin_a)
        r1 = api.get(f"/api/camaras/{self.camara_a.id}/grabaciones/").json()
        r2 = api.get(
            f"/api/camaras/{self.camara_a.id}/grabaciones/?pagina=2").json()

        self.assertEqual(r1['total'], 51)
        self.assertEqual(r1['por_pagina'], 50)
        self.assertEqual(r1['total_paginas'], 2)
        self.assertEqual(len(r1['resultados']), 50)
        self.assertEqual(len(r2['resultados']), 1)
        fechas = [g['fecha'] for g in r1['resultados']]
        self.assertEqual(fechas, sorted(fechas, reverse=True))

    def test_catalogo_recalcula_disponible_contra_disco(self):
        media = self._media()
        ruta = _crear_archivo(media, self.empresa_a, self.camara_a, hora='12_00')
        servicio_camaras.sincronizar_grabaciones()
        api = self.api_como(self.admin_a)
        url = f"/api/camaras/{self.camara_a.id}/grabaciones/"

        datos = api.get(url).json()
        self.assertTrue(datos['resultados'][0]['disponible'])
        self.assertTrue(datos['resultados'][0]['url'].endswith('12_00.mp4'))

        os.remove(ruta)
        datos = api.get(url).json()
        self.assertFalse(datos['resultados'][0]['disponible'])
        self.assertEqual(datos['resultados'][0]['url'], '')

    def test_catalogo_filtra_por_fecha(self):
        media = self._media()
        self._sembrar(media, cantidad=2)
        api = self.api_como(self.admin_a)
        datos = api.get(
            f"/api/camaras/{self.camara_a.id}/grabaciones/?fecha=2026-09-01"
        ).json()

        self.assertEqual(datos['total'], 1)
        self.assertEqual(datos['resultados'][0]['fecha'], '2026-09-01')

    def test_fecha_invalida_rechazada(self):
        media = self._media()
        self._sembrar(media)
        res = self.api_como(self.admin_a).get(
            f"/api/camaras/{self.camara_a.id}/grabaciones/?fecha=01-13-2026")

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['codigo'], 'DATOS_INVALIDOS')
        self.assertIn('YYYY-MM-DD', res.json()['detalle'])

    def test_aislamiento_entre_empresas(self):
        res = self.api_como(self.admin_a).get(
            f"/api/camaras/{self.camara_b.id}/grabaciones/")
        self.assertEqual(res.status_code, 404)

    def test_solo_administrador(self):
        media = self._media()
        self._sembrar(media)
        url = f"/api/camaras/{self.camara_a.id}/grabaciones/"
        self.assertEqual(APIClient().get(url).status_code, 401)
        self.assertEqual(
            self.api_como(self.empleado_a).get(url).status_code, 403)
        self.assertEqual(
            self.api_como(self.admin_a).get(url).status_code, 200)


class SincronizarGrabacionesCommandTest(BaseGrabacionesTest):
    def test_comando_sincroniza_por_empresa_y_camara(self):
        media = self._media()
        _crear_archivo(media, self.empresa_a, self.camara_a)
        call_command(
            'sincronizar_grabaciones',
            '--empresa', str(self.empresa_a.id),
            '--camara', str(self.camara_a.id))
        self.assertEqual(Grabacion.objects.count(), 1)

    def test_comando_rechaza_camara_inexistente(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command(
                'sincronizar_grabaciones',
                '--camara', '00000000-0000-0000-0000-000000000000')