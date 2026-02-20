# db.py
from __future__ import annotations

import sqlite3
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional, Dict, Any, List


@dataclass
class MonthRef:
    id: int
    year: int
    month: int
    start_date: str  # YYYY-MM-01


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    role: str  # 'admin' or 'user'
    must_change_password: bool
    created_at: str


@dataclass
class IngestedTransaction:
    id: int
    user_id: int
    tx_date: str
    tx_time: str
    amount: int
    merchant: str
    currency: str
    from_wallet: bool
    from_email: bool
    wallet_payload: Optional[str]
    email_payload: Optional[str]
    dedupe_key: str
    created_at: str


def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == password_hash


def connect(db_path: str = "finanzas.db") -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def init_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            must_change_password INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS months (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(year, month, user_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salary_amount INTEGER NOT NULL DEFAULT 0,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS fixed_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount INTEGER NOT NULL, -- CRC
            category TEXT NOT NULL,
            destination TEXT NOT NULL,
            account TEXT NOT NULL,
            frequency TEXT NOT NULL,           -- MONTHLY / EVERY_N_MONTHS
            every_n_months INTEGER,            -- si EVERY_N_MONTHS
            start_year INTEGER NOT NULL,
            start_month INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(name, user_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_date TEXT NOT NULL,             -- YYYY-MM-DD
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            kind TEXT NOT NULL,                -- INCOME / EXPENSE
            amount INTEGER NOT NULL,           -- CRC
            category TEXT NOT NULL,
            destination TEXT NOT NULL,
            account TEXT NOT NULL,
            note TEXT,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_tx_ym ON transactions(year, month, user_id);
        CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(tx_date);
        CREATE INDEX IF NOT EXISTS idx_months_user ON months(user_id);

        CREATE TABLE IF NOT EXISTS ingested_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tx_date TEXT NOT NULL,              -- YYYY-MM-DD
            tx_time TEXT NOT NULL,              -- HH:MM:SS
            amount INTEGER NOT NULL,            -- CRC
            merchant TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'CRC',
            from_wallet INTEGER NOT NULL DEFAULT 0,
            from_email INTEGER NOT NULL DEFAULT 0,
            wallet_payload TEXT,
            email_payload TEXT,
            dedupe_key TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, dedupe_key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ingested_user_date ON ingested_transactions(user_id, tx_date);
        """
    )
    con.commit()
    
    # Create default admin user if not exists
    create_default_admin(con)


def create_default_admin(con: sqlite3.Connection) -> None:
    """Create default admin user if not exists"""
    admin_hash = hash_password("admin123")
    con.execute(
        """
        INSERT OR IGNORE INTO users(username, password_hash, role, must_change_password)
        VALUES (?, ?, ?, ?)
        """,
        ("admin", admin_hash, "admin", 0)
    )
    con.commit()


def authenticate_user(con: sqlite3.Connection, username: str, password: str) -> Optional[User]:
    """Authenticate user and return User object if valid"""
    row = con.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    
    if row and verify_password(password, row["password_hash"]):
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
            must_change_password=bool(row["must_change_password"]),
            created_at=row["created_at"]
        )
    return None


def create_user(con: sqlite3.Connection, username: str, password: str, role: str = 'user') -> bool:
    """Create new user"""
    try:
        password_hash = hash_password(password)
        con.execute(
            """
            INSERT INTO users(username, password_hash, role, must_change_password)
            VALUES (?, ?, ?, ?)
            """,
            (username, password_hash, role, 1)  # New users must change password
        )
        con.commit()
        
        # Initialize default settings for new user
        user_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.execute(
            "INSERT INTO settings(salary_amount, user_id) VALUES (0, ?)",
            (user_id,)
        )
        con.execute(
            "INSERT INTO accounts(name, user_id) VALUES (?, ?), (?, ?)",
            ('BCR', user_id, 'BAC', user_id)
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def change_password(con: sqlite3.Connection, user_id: int, new_password: str) -> None:
    """Change user password and reset must_change_password flag"""
    password_hash = hash_password(new_password)
    con.execute(
        "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
        (password_hash, user_id)
    )
    con.commit()


def list_users(con: sqlite3.Connection) -> List[User]:
    """List all users (admin only)"""
    rows = con.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return [
        User(
            id=r["id"],
            username=r["username"],
            password_hash=r["password_hash"],
            role=r["role"],
            must_change_password=bool(r["must_change_password"]),
            created_at=r["created_at"]
        )
        for r in rows
    ]


def delete_user(con: sqlite3.Connection, user_id: int) -> bool:
    """Delete user (admin only) - cannot delete self"""
    try:
        con.execute("DELETE FROM users WHERE id = ?", (user_id,))
        con.commit()
        return True
    except:
        return False


def list_accounts(con: sqlite3.Connection, user_id: int) -> List[str]:
    rows = con.execute("SELECT name FROM accounts WHERE user_id = ? ORDER BY name", (user_id,)).fetchall()
    return [r["name"] for r in rows]


def add_account(con: sqlite3.Connection, name: str, user_id: int) -> None:
    con.execute("INSERT INTO accounts(name, user_id) VALUES (?, ?)", (name, user_id))
    con.commit()


def delete_account(con: sqlite3.Connection, name: str, user_id: int) -> None:
    con.execute("DELETE FROM accounts WHERE name=? AND user_id=?", (name, user_id))
    con.commit()


def ensure_month(con: sqlite3.Connection, year: int, month: int, user_id: int) -> MonthRef:
    start = date(year, month, 1).isoformat()
    con.execute(
        "INSERT OR IGNORE INTO months(year, month, start_date, user_id) VALUES (?, ?, ?, ?)",
        (year, month, start, user_id),
    )
    con.commit()

    row = con.execute(
        "SELECT id, year, month, start_date FROM months WHERE year=? AND month=? AND user_id=?",
        (year, month, user_id),
    ).fetchone()
    return MonthRef(id=row["id"], year=row["year"], month=row["month"], start_date=row["start_date"])


def ensure_month_for_today(con: sqlite3.Connection, today: date, user_id: int) -> MonthRef:
    return ensure_month(con, today.year, today.month, user_id)


def list_months(con: sqlite3.Connection, user_id: int, limit: int = 48) -> List[MonthRef]:
    rows = con.execute(
        "SELECT id, year, month, start_date FROM months WHERE user_id=? ORDER BY year DESC, month DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [MonthRef(id=r["id"], year=r["year"], month=r["month"], start_date=r["start_date"]) for r in rows]


def get_salary(con: sqlite3.Connection, user_id: int) -> int:
    row = con.execute("SELECT salary_amount FROM settings WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        # Create default settings for user if not exists
        try:
            con.execute("INSERT INTO settings(salary_amount, user_id) VALUES (0, ?)", (user_id,))
        except sqlite3.IntegrityError:
            # If there's already a settings record for this user, update it
            con.execute("UPDATE settings SET salary_amount = 0 WHERE user_id = ?", (user_id,))
        con.commit()
        return 0
    return int(row["salary_amount"])


def set_salary(con: sqlite3.Connection, amount: int, user_id: int) -> None:
    # Try to update first, then insert if not exists
    cursor = con.execute("UPDATE settings SET salary_amount=? WHERE user_id=?", (amount, user_id))
    if cursor.rowcount == 0:
        con.execute("INSERT INTO settings(salary_amount, user_id) VALUES (?, ?)", (amount, user_id))
    con.commit()


def add_fixed_expense(
    con: sqlite3.Connection,
    *,
    name: str,
    amount: int,
    category: str,
    destination: str,
    account: str,
    frequency: str,
    every_n_months: Optional[int],
    start_year: int,
    start_month: int,
    user_id: int,
) -> None:
    con.execute(
        """
        INSERT INTO fixed_expenses
        (name, amount, category, destination, account, frequency, every_n_months, start_year, start_month, active, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (name, amount, category, destination, account, frequency, every_n_months, start_year, start_month, user_id),
    )
    con.commit()


def list_fixed_expenses(con: sqlite3.Connection, user_id: int, active_only: bool = False):
    if active_only:
        return con.execute("SELECT * FROM fixed_expenses WHERE active=1 AND user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    return con.execute("SELECT * FROM fixed_expenses WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()


def toggle_fixed_expense(con: sqlite3.Connection, fx_id: int, active: bool, user_id: int) -> None:
    con.execute("UPDATE fixed_expenses SET active=? WHERE id=? AND user_id=?", (1 if active else 0, fx_id, user_id))
    con.commit()


def update_transaction(
    con: sqlite3.Connection,
    tx_id: int,
    *,
    tx_date: str,
    kind: str,
    amount: int,
    category: str,
    destination: str,
    account: str,
    note: Optional[str],
    user_id: int,
) -> None:
    con.execute(
        """
        UPDATE transactions
        SET tx_date=?, kind=?, amount=?, category=?, destination=?, account=?, note=?
        WHERE id=? AND user_id=?
        """,
        (tx_date, kind, amount, category, destination, account, note, tx_id, user_id),
    )
    con.commit()


def update_fixed_expense(
    con: sqlite3.Connection,
    fx_id: int,
    *,
    name: str,
    amount: int,
    category: str,
    destination: str,
    account: str,
    frequency: str,
    every_n_months: Optional[int],
    user_id: int,
) -> None:
    con.execute(
        """
        UPDATE fixed_expenses
        SET name=?, amount=?, category=?, destination=?, account=?, frequency=?, every_n_months=?
        WHERE id=? AND user_id=?
        """,
        (name, amount, category, destination, account, frequency, every_n_months, fx_id, user_id),
    )
    con.commit()


def add_transaction(
    con: sqlite3.Connection,
    *,
    tx_date: str,
    year: int,
    month: int,
    kind: str,  # INCOME/EXPENSE
    amount: int,
    category: str,
    destination: str,
    account: str,
    note: Optional[str],
    user_id: int,
) -> None:
    con.execute(
        """
        INSERT INTO transactions(tx_date, year, month, kind, amount, category, destination, account, note, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (tx_date, year, month, kind, amount, category, destination, account, note, user_id),
    )
    con.commit()


def list_transactions_for_month(con: sqlite3.Connection, year: int, month: int, user_id: int):
    return con.execute(
        "SELECT * FROM transactions WHERE year=? AND month=? AND user_id=? ORDER BY tx_date ASC, id ASC",
        (year, month, user_id),
    ).fetchall()


def fixed_expenses_due_for_month(con: sqlite3.Connection, year: int, month: int, user_id: int):
    rows = con.execute("SELECT * FROM fixed_expenses WHERE active=1 AND user_id=?", (user_id,)).fetchall()

    def idx(y: int, m: int) -> int:
        return y * 12 + (m - 1)

    target = idx(year, month)
    out = []

    for r in rows:
        sy, sm = int(r["start_year"]), int(r["start_month"])
        start_i = idx(sy, sm)
        if target < start_i:
            continue

        freq = r["frequency"]
        if freq == "MONTHLY":
            out.append(r)
        else:
            n = int(r["every_n_months"] or 0)
            if n <= 1:
                out.append(r)
            else:
                diff = target - start_i
                if diff % n == 0:
                    out.append(r)

    out.sort(key=lambda rr: rr["id"])
    return out


def month_totals(con: sqlite3.Connection, year: int, month: int, user_id: int) -> Dict[str, Any]:
    salary = get_salary(con, user_id)
    tx = list_transactions_for_month(con, year, month, user_id)
    fixed = fixed_expenses_due_for_month(con, year, month, user_id)

    income_extra = sum(r["amount"] for r in tx if r["kind"] == "INCOME")
    expenses_var = sum(r["amount"] for r in tx if r["kind"] == "EXPENSE")
    expenses_fixed = sum(r["amount"] for r in fixed)

    total_income = salary + income_extra
    total_expenses = expenses_fixed + expenses_var
    balance = total_income - total_expenses

    return {
        "salary": salary,
        "income_extra": income_extra,
        "expenses_fixed": expenses_fixed,
        "expenses_var": expenses_var,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": balance,
        "fixed_rows": fixed,
        "tx_rows": tx,
    }


def build_dedupe_key(tx_date: str, amount: int, merchant: str) -> str:
    normalized_merchant = re.sub(r"\s+", " ", merchant.strip().lower())
    return f"{tx_date}|{amount}|{normalized_merchant}"


def upsert_ingested_transaction(
    con: sqlite3.Connection,
    *,
    user_id: int,
    tx_date: str,
    tx_time: str,
    amount: int,
    merchant: str,
    currency: str = "CRC",
    source: str,
    payload: str,
) -> IngestedTransaction:
    """
    Inserta transacciones detectadas desde wallet/email evitando duplicados
    entre fuentes para el mismo usuario.
    """
    dedupe_key = build_dedupe_key(tx_date, amount, merchant)
    existing = con.execute(
        "SELECT * FROM ingested_transactions WHERE user_id=? AND dedupe_key=?",
        (user_id, dedupe_key),
    ).fetchone()

    is_wallet = 1 if source == "wallet" else 0
    is_email = 1 if source == "email" else 0

    if existing:
        updated_wallet = max(existing["from_wallet"], is_wallet)
        updated_email = max(existing["from_email"], is_email)
        wallet_payload = payload if source == "wallet" else existing["wallet_payload"]
        email_payload = payload if source == "email" else existing["email_payload"]

        con.execute(
            """
            UPDATE ingested_transactions
            SET from_wallet=?, from_email=?, wallet_payload=?, email_payload=?
            WHERE id=?
            """,
            (updated_wallet, updated_email, wallet_payload, email_payload, existing["id"]),
        )
        con.commit()
        row = con.execute("SELECT * FROM ingested_transactions WHERE id=?", (existing["id"],)).fetchone()
    else:
        con.execute(
            """
            INSERT INTO ingested_transactions(
                user_id, tx_date, tx_time, amount, merchant, currency,
                from_wallet, from_email, wallet_payload, email_payload, dedupe_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                tx_date,
                tx_time,
                amount,
                merchant,
                currency,
                is_wallet,
                is_email,
                payload if source == "wallet" else None,
                payload if source == "email" else None,
                dedupe_key,
            ),
        )
        con.commit()
        row = con.execute(
            "SELECT * FROM ingested_transactions WHERE user_id=? AND dedupe_key=?",
            (user_id, dedupe_key),
        ).fetchone()

    return IngestedTransaction(
        id=row["id"],
        user_id=row["user_id"],
        tx_date=row["tx_date"],
        tx_time=row["tx_time"],
        amount=row["amount"],
        merchant=row["merchant"],
        currency=row["currency"],
        from_wallet=bool(row["from_wallet"]),
        from_email=bool(row["from_email"]),
        wallet_payload=row["wallet_payload"],
        email_payload=row["email_payload"],
        dedupe_key=row["dedupe_key"],
        created_at=row["created_at"],
    )


def list_ingested_transactions_by_day(con: sqlite3.Connection, user_id: int, tx_date: str):
    return con.execute(
        """
        SELECT *
        FROM ingested_transactions
        WHERE user_id=? AND tx_date=?
        ORDER BY tx_time ASC, id ASC
        """,
        (user_id, tx_date),
    ).fetchall()
