import os
import tempfile
import unittest
from datetime import datetime

import db
import ingestion


class IngestionTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.con = db.connect(self.tmp.name)
        db.init_schema(self.con)
        db.create_user(self.con, "user1", "pass123", "user")
        self.user = db.authenticate_user(self.con, "user1", "pass123")

    def tearDown(self):
        self.con.close()
        os.unlink(self.tmp.name)

    def test_deduplicates_between_wallet_and_email(self):
        now = datetime(2026, 2, 1, 10, 15, 0)
        wallet_text = "Google Wallet: Compra por CRC 12500 en SUPER MERCADO SANTA ANA"
        email_text = "BCR transferencia aprobada por CRC 12,500 en Super Mercado Santa Ana."

        first = ingestion.ingest_text_event(self.con, self.user.id, "wallet", wallet_text, now=now)
        second = ingestion.ingest_text_event(self.con, self.user.id, "email", email_text, now=now)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.id, second.id)
        self.assertTrue(second.from_wallet)
        self.assertTrue(second.from_email)

    def test_isolated_by_user(self):
        db.create_user(self.con, "user2", "pass123", "user")
        user2 = db.authenticate_user(self.con, "user2", "pass123")

        now = datetime(2026, 2, 1, 10, 15, 0)
        text = "Google Wallet: Compra por CRC 9999 en TIENDA X"

        tx1 = ingestion.ingest_text_event(self.con, self.user.id, "wallet", text, now=now)
        tx2 = ingestion.ingest_text_event(self.con, user2.id, "wallet", text, now=now)

        self.assertNotEqual(tx1.id, tx2.id)

    def test_list_by_day(self):
        now = datetime(2026, 2, 2, 9, 0, 0)
        ingestion.ingest_text_event(
            self.con,
            self.user.id,
            "wallet",
            "Google Wallet: Compra por CRC 5000 en CAFETERIA CENTRAL",
            now=now,
        )

        rows = db.list_ingested_transactions_by_day(self.con, self.user.id, "2026-02-02")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["amount"], 5000)


if __name__ == "__main__":
    unittest.main()
