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

## Ramas y clonado por rama

Ramas creadas en este repo local:

- `main`
- `main_apk`
- `work`

Comandos para clonar una rama específica:

```bash
git clone --branch main <URL_DEL_REPO>
git clone --branch main_apk <URL_DEL_REPO>
git clone --branch work <URL_DEL_REPO>
```

Si en tu remoto solo aparece una rama, sube las faltantes:

```bash
git push -u origin main
git push -u origin main_apk
git push -u origin work
```
