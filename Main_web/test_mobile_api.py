import io
import json
import os
import tempfile
import unittest

import db
from mobile_api import create_app


class MobileApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        con = db.connect(self.tmp.name)
        db.init_schema(con)
        db.create_user(con, "apkuser", "apkpass", "user")
        con.close()
        self.app = create_app(self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def call_app(self, method, path, body=None, token=None):
        body_bytes = json.dumps(body or {}).encode("utf-8")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path.split("?", 1)[0],
            "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
            "CONTENT_LENGTH": str(len(body_bytes)),
            "wsgi.input": io.BytesIO(body_bytes),
            "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
        }

        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        response = b"".join(self.app(environ, start_response))
        return captured["status"], json.loads(response.decode("utf-8"))

    def test_login_ingest_and_list(self):
        status, payload = self.call_app("POST", "/api/mobile/login", {"username": "apkuser", "password": "apkpass"})
        self.assertTrue(status.startswith("200"))
        token = payload["token"]

        status, _ = self.call_app(
            "POST",
            "/api/mobile/ingest",
            {
                "source": "wallet",
                "amount": 12500,
                "merchant": "Super Mercado Santa Ana",
                "tx_date": "2026-02-01",
                "tx_time": "10:15:00",
                "raw_text": "Wallet compra 12500",
            },
            token=token,
        )
        self.assertTrue(status.startswith("200"))

        status, payload = self.call_app(
            "POST",
            "/api/mobile/ingest",
            {
                "source": "email",
                "amount": 12500,
                "merchant": "super mercado santa ana",
                "tx_date": "2026-02-01",
                "tx_time": "10:15:00",
                "raw_text": "BCR transferencia 12500",
            },
            token=token,
        )
        self.assertTrue(status.startswith("200"))
        self.assertTrue(payload["from_wallet"])
        self.assertTrue(payload["from_email"])

        status, payload = self.call_app("GET", "/api/mobile/transactions?date=2026-02-01", token=token)
        self.assertTrue(status.startswith("200"))
        self.assertEqual(len(payload["transactions"]), 1)

    def test_invalid_token(self):
        status, _ = self.call_app("GET", "/api/mobile/transactions?date=2026-02-01", token="x.y")
        self.assertTrue(status.startswith("401"))


if __name__ == "__main__":
    unittest.main()
