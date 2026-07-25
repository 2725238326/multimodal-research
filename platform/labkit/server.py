#!/usr/bin/env python3
"""FastAPI server for the labkit dashboard (optional visualization layer).

Serves the registry as JSON under /api/* and the built frontend (web/dist) at /.
This is the ONLY component that needs third-party deps; core logging works
without it. Read-only over the registry — writes happen via the CLI / analyses.

Run:
    pip install -r platform/requirements-server.txt
    python platform/labkit/server.py            # http://127.0.0.1:8000
    # or: cd platform && python -m labkit.server
"""

from __future__ import annotations

import os
import sys

_PLATFORM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLATFORM_DIR not in sys.path:
    sys.path.insert(0, _PLATFORM_DIR)

from pathlib import Path  # noqa: E402

from labkit.store import PLATFORM_DIR, Store  # noqa: E402

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
except ImportError as exc:  # pragma: no cover - helpful message only
    raise SystemExit(
        "FastAPI not installed. Run: pip install -r platform/requirements-server.txt"
    ) from exc

app = FastAPI(title="labkit", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

store = Store()
FOLDERS = ("ideas", "experiments", "runs", "datasets", "modules")
DIST_DIR = PLATFORM_DIR / "web" / "dist"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "counts": {f: len(store.list_raw(f)) for f in FOLDERS}}


@app.get("/api/registry")
def registry() -> dict:
    problems = store.validate_all()
    return {"data": store.export(), "problems": problems}


@app.get("/api/{folder}")
def list_folder(folder: str):
    if folder not in FOLDERS:
        raise HTTPException(404, f"unknown collection: {folder}")
    return store.list_raw(folder)


@app.get("/api/{folder}/{entity_id}")
def get_entity(folder: str, entity_id: str):
    if folder not in FOLDERS:
        raise HTTPException(404, f"unknown collection: {folder}")
    if not store.exists(folder, entity_id):
        raise HTTPException(404, f"{folder}/{entity_id} not found")
    return store.load_raw(folder, entity_id)


# ---- static frontend (mounted last so /api takes precedence) ------------- #
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(DIST_DIR / "index.html")

    @app.get("/{path:path}")
    def spa(path: str):
        candidate = DIST_DIR / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")  # SPA fallback
else:

    @app.get("/")
    def index_missing():
        return JSONResponse(
            {
                "message": "Frontend not built. Run: cd platform/web && npm install && npm run build",
                "api": "/api/registry",
            }
        )


def main() -> None:
    import uvicorn

    host = os.environ.get("LABKIT_HOST", "127.0.0.1")
    port = int(os.environ.get("LABKIT_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
