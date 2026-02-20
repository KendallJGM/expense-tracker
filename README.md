# expense-tracker

Base local para finanzas con soporte multiusuario.

## Ingestión automática (Wallet + BCR)

Se agregó un flujo para guardar transacciones detectadas desde texto estructurado de fuentes externas.

### Qué hace

- Parsea monto y comercio desde texto.
- Inserta en `ingested_transactions`.
- Evita duplicados por usuario (`fecha+monto+comercio`).
- Si llega por múltiples fuentes, unifica en un solo registro.
- Permite consultar por día para la vista web de transacciones.

### Pruebas

```bash
python -m unittest test_ingestion.py
python -m unittest test_multiuser.py
```
