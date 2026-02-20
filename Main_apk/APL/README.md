# APL - Proyecto Android APK (FinTracker)

Este folder contiene un proyecto Android nativo (Kotlin) para generar un APK que:

1. Permite login una sola vez.
2. Escucha notificaciones del teléfono con `NotificationListenerService`.
3. Detecta eventos de gasto desde:
   - Google Wallet / Google Pay (notificación)
   - Gmail (notificación de correos BCR con transferencia/compra)
4. Deduplica localmente por `usuario+fecha+monto+comercio`.
5. Envía transacciones al backend con token del usuario autenticado.

## Main del APK

- Launcher: `LoginActivity`
- Main app class: `MainApplication`
- Pantalla principal: `MainActivity`

## Backend requerido (incluido en este repo)

Endpoints:

- `POST /api/mobile/login`
- `POST /api/mobile/ingest`
- `GET /api/mobile/transactions?date=YYYY-MM-DD`

Levantar backend (desde la raíz del repo):

```bash
cd Main_web
python run_mobile_api.py
```

## Build del APK

Desde Android Studio (recomendado):

- Abrir carpeta `Main_apk/APL`
- `Build > Build Bundle(s) / APK(s) > Build APK(s)`

Desde terminal (si tienes SDK/Gradle configurado):

```bash
cd Main_apk/APL
./gradlew assembleDebug
```

APK esperado:

- `Main_apk/APL/app/build/outputs/apk/debug/app-debug.apk`

## Notas importantes

- Leer notificaciones de Gmail no equivale a leer todo el correo: solo procesa texto de la notificación.
- Para lectura completa de inbox hace falta Gmail API (OAuth scopes + revisión adicional).
- El permiso de `NotificationListenerService` se habilita manualmente en Ajustes del sistema.
