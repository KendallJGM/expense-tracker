# expense-tracker

Repositorio reorganizado en **una sola rama** con dos carpetas principales:

- `Main_web/`: backend/app de finanzas en Python (incluye API móvil y base de datos).
- `Main_apk/`: proyecto Android APK.

## Estructura

```text
Main_web/
Main_apk/
```

## Comandos rápidos (PowerShell)

### Ejecutar app web (con entorno virtual)

```powershell
cd Main_web
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

### Ejecutar backend móvil para el APK (con entorno virtual)

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

APK esperado:
`Main_apk\APL\app\build\outputs\apk\debug\app-debug.apk`
