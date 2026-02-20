# Main_web

Código web/backend en Python para finanzas multiusuario + ingesta de transacciones.

## Contenido

- App principal: `app.py`
- Lógica DB: `db.py`
- Ingesta/parsing: `ingestion.py`
- API móvil para APK: `mobile_api.py`
- Runner API móvil: `run_mobile_api.py`
- Tests: `test_ingestion.py`, `test_mobile_api.py`, `test_multiuser.py`

## Ejecutar app principal

```bash
python app.py
```

## Ejecutar API móvil

```bash
python run_mobile_api.py
```

## Tests

```bash
python -m unittest test_ingestion.py test_mobile_api.py test_multiuser.py
```
