from wsgiref.simple_server import make_server

from mobile_api import create_app


if __name__ == "__main__":
    app = create_app("finanzas.db")
    with make_server("0.0.0.0", 8000, app) as server:
        print("Mobile API running on http://0.0.0.0:8000")
        server.serve_forever()
