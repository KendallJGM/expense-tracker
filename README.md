# expense-tracker

Base local para finanzas con soporte multiusuario.

## Nuevo: ingestión automática de transacciones

Se agregó un flujo base para guardar transacciones detectadas desde:

- Notificaciones de Wallet/Google Pay (`source=wallet`)
- Correos de BCR sobre transferencias/compras (`source=email`)

### Qué hace

- Parsea monto y comercio desde texto plano.
- Inserta transacciones en `ingested_transactions`.
- Evita duplicados entre wallet y correo por usuario con una llave de deduplicación (`fecha+monto+comercio`).
- Si llega por ambos canales, unifica en un solo registro y marca ambas fuentes.
- Permite consultar por día para renderizar una vista diaria en web.

### APIs internas agregadas

- `db.upsert_ingested_transaction(...)`
- `db.list_ingested_transactions_by_day(...)`
- `ingestion.ingest_text_event(...)`

### Pruebas

```bash
python -m unittest test_ingestion.py
```

## Siguiente paso recomendado para APK Android

Este repo no contiene app Android todavía. Para Galaxy S25 Ultra, el camino recomendado es:

1. Crear app nativa Android (Kotlin) con:
   - `NotificationListenerService` (leer notificaciones de Wallet)
   - integración con Gmail API o reenvío controlado de correos BCR
2. Login una sola vez en APK y guardar token seguro.
3. Enviar eventos parseados a un endpoint backend ligado al usuario autenticado.
4. En la web, mostrar pestaña **Transacciones** agrupada por día usando `list_ingested_transactions_by_day`.

