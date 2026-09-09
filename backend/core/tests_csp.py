"""Fase C3: cabecera Content-Security-Policy emitida por el backend (y
documentada en nginx para la SPA). Verifica que toda respuesta del API la
lleva y que contiene las directivas defensivas clave.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from .csp import CONTENT_SECURITY_POLICY


class CspHeaderTest(TestCase):
    def _get(self, url):
        return APIClient().get(url)

    def test_respuesta_publica_lleva_csp_con_directivas_clave(self):
        r = self._get('/api/tienda/catalogo/')
        self.assertEqual(r.status_code, 200)
        csp = r['Content-Security-Policy']
        self.assertIn("default-src 'self'", csp)
        # Sin eval ni origenes externos: el proveedor de script es solo self.
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn('unsafe-eval', csp)
        # No se puede embutir la app en iframes ajenos (refuerza X-Frame-Options).
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn('object-src', csp)
        self.assertIn("base-uri 'self'", csp)

    def test_la_politica_registrada_mathea_la_del_backend(self):
        r = self._get('/api/tienda/catalogo/')
        self.assertEqual(r['Content-Security-Policy'], CONTENT_SECURITY_POLICY)