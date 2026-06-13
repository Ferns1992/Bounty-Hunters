import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.requestid import RequestIDMiddleware
from fastapi.testclient import TestClient

app = FastAPI()
app.add_middleware(RequestIDMiddleware)


@app.get("/")
def read_root(request: Request):
    return {"request_id": request.state.request_id}


client = TestClient(app)


def test_request_id_generated():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    request_id = data["request_id"]
    assert uuid.UUID(request_id)
    assert response.headers["X-Request-ID"] == request_id


def test_request_id_from_client():
    client_request_id = "my-custom-id"
    response = client.get("/", headers={"X-Request-ID": client_request_id})
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == client_request_id
    assert response.headers["X-Request-ID"] == client_request_id


def test_request_id_unique():
    ids = set()
    for _ in range(10):
        response = client.get("/")
        ids.add(response.json()["request_id"])
    assert len(ids) == 10
