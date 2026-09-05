# Tests

Este directorio contiene las pruebas unitarias e integradas del backend.

## Cómo correr las pruebas
- El comando correcto es el runner estándar de Django (desde `backend/`):
  ```
  python manage.py test
  ```
- Las pruebas viven en `backend/core/tests.py` y `backend/cuentas/tests.py`.
- Requieren una base de datos MySQL local accesible (ver `settings.py`); Django crea y destruye una base de prueba automáticamente.