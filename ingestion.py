from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import db


@dataclass
class ParsedTransaction:
    source: str
    tx_date: str
    tx_time: str
    amount: int
    merchant: str
    currency: str
    raw_text: str


_AMOUNT_PATTERNS = [
    re.compile(r"(?:CRC|₡)\s*([0-9][0-9\.,]*)", re.IGNORECASE),
    re.compile(r"([0-9][0-9\.,]*)\s*(?:CRC|colones?)", re.IGNORECASE),
]


def _parse_amount(raw_text: str) -> Optional[int]:
    for pattern in _AMOUNT_PATTERNS:
        m = pattern.search(raw_text)
        if not m:
            continue
        raw_amount = m.group(1).replace(",", "")
        try:
            if "." in raw_amount:
                return int(float(raw_amount))
            return int(raw_amount)
        except ValueError:
            continue
    return None


def _parse_merchant(raw_text: str) -> str:
    patterns = [
        re.compile(r"(?:en|at|comercio)\s+([A-Za-z0-9\-\._ ]{3,})", re.IGNORECASE),
        re.compile(r"(?:merchant|establecimiento)\s*[:\-]\s*([A-Za-z0-9\-\._ ]{3,})", re.IGNORECASE),
    ]
    for pattern in patterns:
        m = pattern.search(raw_text)
        if m:
            return m.group(1).strip().rstrip(".")
    return "Transacción"


def parse_wallet_notification(raw_text: str, now: Optional[datetime] = None) -> Optional[ParsedTransaction]:
    amount = _parse_amount(raw_text)
    if amount is None:
        return None

    now = now or datetime.now()
    return ParsedTransaction(
        source="wallet",
        tx_date=now.strftime("%Y-%m-%d"),
        tx_time=now.strftime("%H:%M:%S"),
        amount=amount,
        merchant=_parse_merchant(raw_text),
        currency="CRC",
        raw_text=raw_text,
    )


def parse_bcr_email(raw_text: str, now: Optional[datetime] = None) -> Optional[ParsedTransaction]:
    keywords = ["bcr", "transferencia", "compra", "débito", "debito"]
    lowered = raw_text.lower()
    if not all(k in lowered for k in ["bcr", "transfer"]):
        return None
    if not any(k in lowered for k in keywords):
        return None

    amount = _parse_amount(raw_text)
    if amount is None:
        return None

    now = now or datetime.now()
    return ParsedTransaction(
        source="email",
        tx_date=now.strftime("%Y-%m-%d"),
        tx_time=now.strftime("%H:%M:%S"),
        amount=amount,
        merchant=_parse_merchant(raw_text),
        currency="CRC",
        raw_text=raw_text,
    )


def ingest_text_event(con, user_id: int, source: str, raw_text: str, now: Optional[datetime] = None) -> Optional[db.IngestedTransaction]:
    parser = parse_wallet_notification if source == "wallet" else parse_bcr_email
    parsed = parser(raw_text, now=now)
    if not parsed:
        return None

    return db.upsert_ingested_transaction(
        con,
        user_id=user_id,
        tx_date=parsed.tx_date,
        tx_time=parsed.tx_time,
        amount=parsed.amount,
        merchant=parsed.merchant,
        currency=parsed.currency,
        source=parsed.source,
        payload=parsed.raw_text,
    )
