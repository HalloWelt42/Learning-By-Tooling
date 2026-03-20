"""Testinfrastruktur: In-Memory-DB, App-Client, Auth-Helpers."""

import sys, os
from pathlib import Path

# Backend-Verzeichnis im Pfad
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _test_db(tmp_path, monkeypatch):
    """Jeder Test bekommt eine eigene SQLite-Datenbank."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("BUNDLES_PATH", str(tmp_path / "bundles"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    (tmp_path / "bundles").mkdir()
    (tmp_path / "uploads").mkdir()

    import db as db_mod
    # DB_PATH ist die globale Variable die get_db() nutzt
    monkeypatch.setattr(db_mod, "DB_PATH", Path(str(db_path)))
    db_mod.init_db()

    yield db_path


@pytest.fixture
def client(_test_db):
    """FastAPI TestClient mit frischer DB."""
    from main import app
    return TestClient(app)


@pytest.fixture
def auth_header(client):
    """Registriert einen Testuser und gibt Auth-Header zurück."""
    resp = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "test1234",
        "display_name": "Tester"
    })
    if resp.status_code == 200:
        token = resp.json()["token"]
    else:
        resp = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "test1234"
        })
        token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_package(client, auth_header):
    """Erstellt ein Testpaket mit 5 Karten und gibt die Package-ID zurück."""
    resp = client.post("/api/packages", json={
        "name": "Testpaket",
        "description": "Für Tests"
    }, headers=auth_header)
    pkg_id = resp.json()["id"]

    for i in range(5):
        client.post("/api/cards", json={
            "package_id": pkg_id,
            "card_id": f"T-{i+1:03d}",
            "question": f"Frage {i+1}",
            "answer": f"Antwort {i+1}",
            "category_code": "GB",
            "difficulty": 1 + (i % 3),
        }, headers=auth_header)

    return pkg_id
