# expense-tracker

Base local para finanzas con soporte multiusuario.

## Ingestión automática (Wallet + BCR)

Se agregó un flujo para guardar transacciones detectadas desde:

- Notificaciones de Wallet/Google Pay (`source=wallet`)
- Correos BCR (vía texto de notificación de Gmail) (`source=email`)

### Qué hace

- Parsea monto y comercio desde texto.
- Inserta en `ingested_transactions`.
- Evita duplicados por usuario (`fecha+monto+comercio`).
- Si llega por wallet y correo, unifica en un solo registro.
- Permite consultar por día para la vista web de transacciones.

## API móvil real para el APK

Ahora el repo incluye backend HTTP para el APK:

- `POST /api/mobile/login`
- `POST /api/mobile/ingest`
- `GET /api/mobile/transactions?date=YYYY-MM-DD`
- `GET /api/mobile/health`

Archivo principal:

- `mobile_api.py`
- runner: `run_mobile_api.py`

### Ejecutar API

```bash
python run_mobile_api.py
```

Servidor en `http://0.0.0.0:8000`.

> Para producción cambia `MOBILE_API_SECRET` en variables de entorno.

## APK Android

Se creó el proyecto Android en `APL/` con:

- Login una sola vez.
- `NotificationListenerService` activo para Wallet + Gmail/BCR.
- Deduplicación local previa al envío.
- Envío autenticado al backend.

Ver detalle en `APL/README.md`.
