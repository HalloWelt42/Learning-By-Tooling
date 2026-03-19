"""
Learn-e-Versum Backend
Paket-zentrierte Lernplattform mit Mehrbenutzersystem.
Port: 8030
"""

from __future__ import annotations
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db import init_db
from auth import seed_admin

from routes.auth import router as auth_router
from routes.packages import router as packages_router
from routes.cards import router as cards_router
from routes.sessions import router as sessions_router
from routes.ai import router as ai_router
from routes.admin import router as admin_router
from routes.import_export import router as import_export_router

app = FastAPI(title="Learning-By-Tooling", version="4.0.0")

# CORS -- grosszuegig fuer die Entwicklungsphase
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
    expose_headers=["*"],
)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(Path(__file__).parent.parent / "uploads")))
UPLOAD_DIR.mkdir(exist_ok=True)

BUNDLES_PATH = Path(os.environ.get("BUNDLES_PATH", str(Path(__file__).parent.parent / "lernpakete")))

# Uploads als statische Dateien bereitstellen
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

init_db()
seed_admin()

# -- Router einbinden ----------------------------------------------------------

app.include_router(auth_router)
app.include_router(packages_router)
app.include_router(cards_router)
app.include_router(sessions_router)
app.include_router(ai_router)
app.include_router(admin_router)
app.include_router(import_export_router)


# -- Health (oeffentlich) ------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "3.0.0", "app": "Learning-By-Tooling"}
