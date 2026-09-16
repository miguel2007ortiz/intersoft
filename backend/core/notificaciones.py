"""Servicio unificado de notificaciones (fase 9).

Centraliza la creacion de avisos globales por empresa: detecta el evento,
construye el mensaje, inserta la `Notificacion` (con `tipo`, `empresa`,
`estado` y `canal`) y entrega el aviso por WhatsApp con canal alterno email.

Todas las fases anteriores que creaban avisos (`_notificar_admin`,
`_registrar_alerta_stock`) se redirigen aqui para que todo el sistema fluya
por el mismo centro de notificaciones.
"""

from .models import Notificacion


def _destinos(usuario):
    """Resuelve los destinatarios de entrega para un usuario (puede ser None)."""
    if usuario is None:
        return None, None
    perfil = getattr(usuario, 'perfil', None)
    telefono = getattr(perfil, 'telefono', '') if perfil else ''
    return (telefono or '').strip() or None, (usuario.email or '').strip() or None


def crear_notificacion(empresa, usuario=None, tipo='sistema', mensaje='',
                       notificar=False, auditar_usuario=None):
    """Inserta una notificacion global y, si `notificar`, la entrega fuera.

    Devuelve la `Notificacion` creada. El `canal` queda como 'whatsapp'/
    'email'/'ninguno' segun la entrega efectiva.
    """
    wa, email = None, None
    if notificar:
        wa, email = _destinos(usuario)

    aviso = Notificacion.objects.create(
        usuario=usuario,
        empresa=empresa,
        tipo=tipo,
        estado='nueva',
        canal='ninguno',
        leida=False,
        entrega_pendiente=False,
        mensaje=mensaje,
    )

    if notificar:
        from .services.notificador import entregar
        canal = entregar(mensaje, destino_whatsapp=wa, destino_email=email)
        aviso.canal = canal
        # Si fallo la entrega por todos los canales, queda pendiente de
        # reintento para no perder el aviso.
        aviso.entrega_pendiente = canal == 'ninguno'
        aviso.save(update_fields=['canal', 'entrega_pendiente'])

    if auditar_usuario:
        from cuentas.models import ActividadUsuario
        ActividadUsuario.registrar(
            auditar_usuario, 'NOTIFICACION_ENVIADA',
            f"{tipo}: {mensaje[:80]}")

    return aviso


def reintentar_entrega(aviso):
    """Reintenta la entrega de una notificacion pendiente.

    Usa los mismos destinatarios del usuario (si existen) y devuelve el canal
    efectivo. Si vuelve a fallar, `entrega_pendiente` se mantiene en True.
    """
    if not aviso.usuario_id or not aviso.empresa_id:
        return aviso

    from .models import Notificacion
    from .services.notificador import entregar

    wa, email = _destinos(aviso.usuario)
    canal = entregar(aviso.mensaje, destino_whatsapp=wa, destino_email=email)
    aviso.canal = canal
    aviso.entrega_pendiente = canal == 'ninguno'
    Notificacion.objects.filter(id=aviso.id).update(
        canal=canal, entrega_pendiente=canal == 'ninguno')
    return aviso


def _buscar_alertas_stock(producto):
    """Alertas de stock abiertas (no leidas) de un producto, si existen."""
    return Notificacion.objects.filter(
        empresa_id=producto.empresa_id,
        tipo='stock',
        leida=False,
        mensaje__contains=f'({producto.sku})',
    ).order_by('-created_at')


def _construir_mensaje_stock(producto):
    # Formato estable (lo parsea AlertaActualizarStockView via el primer
    # grupo de parentesis: el SKU): "Stock bajo: NOMBRE (SKU) tiene X
    # unidades (minimo Y)."
    return (f"Stock bajo: {producto.nombre} ({producto.sku}) "
            f"tiene {producto.stock} unidades "
            f"(minimo {producto.stock_minimo}).")


def sincronizar_alerta_stock(producto):
    """Mantiene EXACTAMENTE una alerta de stock abierta por producto.

    Reglas (idempotente, seguro llamarlo en cada save/movimiento):
    - Stock bajo y activo: crea la alerta si no existe (una sola, no leida)
      y actualiza su mensaje con el stock vigente.
    - Stock repuesto o producto inactivo: cierra la alerta abierta si quedaba.

    Devuelve la `Notificacion` creada (o None si no aplicaba)."""
    if not producto.activo or producto.stock > producto.stock_minimo:
        # Stock repuesto o producto inactivo: cierra TODAS las abiertas.
        _buscar_alertas_stock(producto).update(leida=True, estado='resuelta')
        return None

    alerta = _buscar_alertas_stock(producto).first()
    if alerta:
        alerta.mensaje = _construir_mensaje_stock(producto)
        alerta.save(update_fields=['mensaje'])
        return alerta
    return crear_notificacion(
        empresa=producto.empresa,
        tipo='stock',
        mensaje=_construir_mensaje_stock(producto),
    )
