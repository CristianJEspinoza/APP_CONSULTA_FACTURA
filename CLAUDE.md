# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FastAPI REST API that consults Peruvian electronic invoices (SUNAT comprobantes). It unifies, in a single response, invoice data from **Lucode** (apisunat.pe) with supplier RUC status from **PeruDevs**, querying both upstreams in parallel via `asyncio.gather`. Code identifiers and docstrings are in Spanish.

## Commands

```powershell
# Setup (Python 3.11–3.13; 3.14 not yet supported by pydantic-core)
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Run (dev, hot-reload)
uvicorn app:app --reload --port 8000

# Run (prod)
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

# Docker
docker build -t consulta-factura .
docker run -p 8000:8000 --env-file .env consulta-factura

# Generate an API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Interactive docs at `/docs` (Swagger) and `/redoc`. There is **no test suite** in this repo.

## Configuration

All config loads from `.env` via `pydantic-settings` (`src/config.py`, cached singleton `get_settings()`). Required vars: `API_URL_BASE`, `API_TOKEN_LUCODE` (Lucode), `API_URL_PERU_DEVS`, `API_KEY_PERU_DEVS` (PeruDevs), and `API_KEY` (the key this API requires from callers). `.env` is gitignored and absent — create it before running.

## Architecture

Request flow: `app.py` (FastAPI app + open CORS) → `src/routes.py` (`/api/v1` router, auth applied at router level via `dependencies=[Depends(verify_api_key)]`) → `src/services.py` `ReadAPI.consultar_factura` → fans out to Lucode + PeruDevs in parallel → unified `ConsultaResponse`.

- **`src/services.py`** is the core. `consultar_factura` opens one shared `httpx.AsyncClient` and `asyncio.gather`s `consult_api_lucode` + `consult_api_peru_devs`. Lucode supplies invoice totals, detraction, related document, comprobante status, and emission date; PeruDevs supplies supplier `condicion`/`estado`. The two are merged: `proveedor.estado_comprobante` is set from the Lucode result after gather.
- **Error-handling asymmetry (intentional):** Lucode failures raise `ValueError` and abort the request (Lucode data is essential). PeruDevs failures are swallowed and return an empty `DatosProveedor()` (supplier data is best-effort). Preserve this when editing.
- **`src/schemas.py`** — Pydantic models. `ConsultaResponse` extends `TotalesFactura` (flat invoice totals) and adds `fecha_emision` + nested `proveedor`. All numeric totals are serialized as **strings** (e.g. `"0.00"`), not numbers.
- **`src/security.py`** — `verify_api_key` compares the caller's key against `settings.API_KEY`. Missing key → 401, wrong key → 403. The health check `GET /` is outside the router and unauthenticated.

## Auth header

Callers authenticate with the **`Authorization`** header (`src/security.py`, `APIKeyHeader(name="Authorization")`) — not a Bearer scheme, just the raw key. Missing → 401, wrong → 403.

## Conventions

- Lucode upstream responses are defensively parsed: success is gated on `data.get("success")` plus presence of `payload`; multiple error shapes (`message`-only, `error` key) are normalized into `ValueError`. Follow the same defensive `.get(...) or default` pattern when reading upstream JSON.
- `total_grav_oner` in the response is computed as `total_grav_oner + total_isc` from Lucode totals.
