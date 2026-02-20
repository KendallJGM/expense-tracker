# expense-tracker

Base local para finanzas con soporte multiusuario.

## Estructura actual del repo

Para evitar conflictos entre web y APK, el repo se organizó así:

- `Main_web/`: código web/backend en Python (fuente principal activa)
- `Main_apk/`: proyecto Android APK

> Compatibilidad: también se mantienen archivos Python clave en la raíz (`db.py`, `app.py`, `mobile_api.py`, etc.) para facilitar merges con ramas anteriores y evitar conflictos de PR.

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

- `POST /api/mobile/login`
- `POST /api/mobile/ingest`
- `GET /api/mobile/transactions?date=YYYY-MM-DD`
- `GET /api/mobile/health`

Runner:

```bash
python run_mobile_api.py
```

## Comandos rápidos (PowerShell)

### App principal web

```powershell
cd Main_web
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

### Backend móvil para APK

```powershell
cd Main_web
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python run_mobile_api.py
```

### Compilar APK

```powershell
cd Main_apk\APL
.\gradlew.bat assembleDebug
```
