from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs

import db

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 días


def _secret_key() -> bytes:
    return os.getenv("MOBILE_API_SECRET", "dev-secret-change-me").encode("utf-8")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(user_id: int, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_part = _b64url(raw)
    signature = hmac.new(_secret_key(), payload_part.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_part}.{signature}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload_part, signature = token.split(".", 1)
    except ValueError:
        return None

    expected = hmac.new(_secret_key(), payload_part.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def _json_response(status: str, body: Dict[str, Any]) -> Tuple[str, list[tuple[str, str]], bytes]:
    encoded = json.dumps(body).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(encoded))),
    ]
    return status, headers, encoded


def _read_json_body(environ) -> Dict[str, Any]:
    length = int(environ.get("CONTENT_LENGTH", "0") or "0")
    raw = environ["wsgi.input"].read(length) if length > 0 else b"{}"
    try:
        return json.loads(raw.decode("utf-8")) if raw else {}
    except json.JSONDecodeError:
        return {}


def _extract_bearer(environ) -> Optional[str]:
    auth = environ.get("HTTP_AUTHORIZATION", "")
    if not auth.startswith("Bearer "):
        return None
    return auth.replace("Bearer ", "", 1).strip()


def create_app(db_path: str = "finanzas.db"):
    def app(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "")

        if method == "GET" and path == "/api/mobile/health":
            status, headers, body = _json_response("200 OK", {"ok": True})
            start_response(status, headers)
            return [body]

        if method == "POST" and path == "/api/mobile/login":
            data = _read_json_body(environ)
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", "")).strip()
            if not username or not password:
                status, headers, body = _json_response("400 Bad Request", {"error": "username y password son obligatorios"})
                start_response(status, headers)
                return [body]

            con = db.connect(db_path)
            try:
                db.init_schema(con)
                user = db.authenticate_user(con, username, password)
            finally:
                con.close()

            if not user:
                status, headers, body = _json_response("401 Unauthorized", {"error": "credenciales inválidas"})
            else:
                token = create_token(user.id, user.username)
                status, headers, body = _json_response(
                    "200 OK", {"token": token, "user_id": str(user.id), "username": user.username}
                )
            start_response(status, headers)
            return [body]

        if method == "POST" and path == "/api/mobile/ingest":
            token = _extract_bearer(environ)
            payload = verify_token(token) if token else None
            if not payload:
                status, headers, body = _json_response("401 Unauthorized", {"error": "token inválido o ausente"})
                start_response(status, headers)
                return [body]

            data = _read_json_body(environ)
            source = str(data.get("source", "")).strip().lower()
            merchant = str(data.get("merchant", "")).strip() or "Transacción"
            raw_text = str(data.get("raw_text", "")).strip()

            try:
                amount = int(data.get("amount"))
            except (TypeError, ValueError):
                status, headers, body = _json_response("400 Bad Request", {"error": "amount inválido"})
                start_response(status, headers)
                return [body]

            tx_date = str(data.get("tx_date", "")).strip()
            tx_time = str(data.get("tx_time", "")).strip()
            try:
                datetime.strptime(tx_date, "%Y-%m-%d")
                datetime.strptime(tx_time, "%H:%M:%S")
            except ValueError:
                status, headers, body = _json_response("400 Bad Request", {"error": "tx_date o tx_time inválidos"})
                start_response(status, headers)
                return [body]

            if source not in {"wallet", "email"} or amount <= 0:
                status, headers, body = _json_response("400 Bad Request", {"error": "source/amount inválidos"})
                start_response(status, headers)
                return [body]

            con = db.connect(db_path)
            try:
                db.init_schema(con)
                row = db.upsert_ingested_transaction(
                    con,
                    user_id=int(payload["user_id"]),
                    tx_date=tx_date,
                    tx_time=tx_time,
                    amount=amount,
                    merchant=merchant,
                    currency="CRC",
                    source=source,
                    payload=raw_text,
                )
            finally:
                con.close()

            status, headers, body = _json_response(
                "200 OK",
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "tx_date": row.tx_date,
                    "tx_time": row.tx_time,
                    "amount": row.amount,
                    "merchant": row.merchant,
                    "from_wallet": row.from_wallet,
                    "from_email": row.from_email,
                },
            )
            start_response(status, headers)
            return [body]

        if method == "GET" and path == "/api/mobile/transactions":
            token = _extract_bearer(environ)
            payload = verify_token(token) if token else None
            if not payload:
                status, headers, body = _json_response("401 Unauthorized", {"error": "token inválido o ausente"})
                start_response(status, headers)
                return [body]

            query = parse_qs(environ.get("QUERY_STRING", ""))
            tx_date = (query.get("date", [""])[0] or "").strip()
            try:
                datetime.strptime(tx_date, "%Y-%m-%d")
            except ValueError:
                status, headers, body = _json_response("400 Bad Request", {"error": "date debe ser YYYY-MM-DD"})
                start_response(status, headers)
                return [body]

            con = db.connect(db_path)
            try:
                rows = db.list_ingested_transactions_by_day(con, int(payload["user_id"]), tx_date)
            finally:
                con.close()

            data = [
                {
                    "id": r["id"],
                    "tx_date": r["tx_date"],
                    "tx_time": r["tx_time"],
                    "amount": r["amount"],
                    "merchant": r["merchant"],
                    "from_wallet": bool(r["from_wallet"]),
                    "from_email": bool(r["from_email"]),
                }
                for r in rows
            ]
            status, headers, body = _json_response("200 OK", {"date": tx_date, "transactions": data})
            start_response(status, headers)
            return [body]

        status, headers, body = _json_response("404 Not Found", {"error": "not found"})
        start_response(status, headers)
        return [body]

    return app
