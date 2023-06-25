from flask.testing import FlaskClient
from flask import Response

from micro_file_server.__main__ import app


def test_main():
    app.testing = True
    with app.test_client() as client:
        client: FlaskClient
        r: Response = client.get('/')
        assert r.status_code == 200
