# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FastAPI REST API that consults Peruvian electronic invoices (SUNAT comprobantes). It unifies, in a single response, invoice data from **Lucode** (apisunat.pe) with supplier RUC status + comprobante status from the **SUNAT tracker** (an Azure-hosted `ms-tracker-sunat` service). The two upstreams run **sequentially**: Lucode first, then the tracker — the tracker's request needs Lucode's `fecha_emision` and `monto_total_general`. Code identifiers and docstrings are in Spanish.

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

All config loads from `.env` via `pydantic-settings` (`src/config.py`, cached singleton `get_settings()`). Required vars: `API_URL_BASE`, `API_TOKEN_LUCODE` (Lucode), `API_URL_SUNAT_TRACKER`, `API_KEY_SUNAT_TRACKER` (SUNAT tracker), and `API_KEY` (the key this API requires from callers). `.env` is gitignored and absent — create it before running.

## Architecture

Request flow: `app.py` (FastAPI app + open CORS) → `src/routes.py` (`/api/v1` and `/api/v2` routers, auth applied at router level via `dependencies=[Depends(verify_api_key)]`) → `src/services.py` `ReadAPI.consultar_factura` → calls Lucode, then the SUNAT tracker → unified `ConsultaResponseV2`.

- **API versioning:** `src/routes.py` exposes two routers over **one** service. `_consultar` runs the query and normalizes errors; both endpoints call it. `consultar_factura` always returns the **v2** contract (the superset), and the v1 route projects it down with `ConsultaResponse.model_validate(resultado.model_dump())` — Pydantic drops the extra keys. **`ConsultaResponse` (v1) is a frozen contract: never add fields to it.** New response fields go in `ConsultaResponseV2` / `ItemFacturaV2`, which subclass the v1 models. Today v2 adds `pdf` and `items[].impuesto_nombre_tributo`; everything else is shared.
- **Recibos por honorarios (`tipo_comprobante == "02"`, constant `TIPO_RECIBO_HONORARIOS`):** the tracker does not validate them (returns `success: false`, `"Error en consulta SUNAT: Sin código"`), so `consultar_factura` fills `proveedor.estado_comprobante` from Lucode's `detalle.estado_comprobante` (uppercased to match the tracker's `ACEPTADO`). This applies to **both** versions. `condicion`/`estado` stay empty — only the tracker has them.

- **`src/services.py`** is the core. `consultar_factura` opens one shared `httpx.AsyncClient`, awaits `consult_api_lucode`, then awaits `consult_api_sunat_tracker` passing Lucode's `fecha_emision` and `monto_total_general`. Lucode supplies invoice totals, detraction, related document, and emission date; the tracker supplies the whole `proveedor` block (`condicion` ← `condDomiRuc`, `estado` ← `estadoRuc`, `estado_comprobante` ← `estadoCp`). The calls are **sequential**, not parallel, because of this data dependency.
- **Tracker request contract:** `POST` with header `X-API-KEY`; body `{numero_ruc, tipo_comprobante, comprobante (= "SERIE-NUMERO"), fecha_emision (d/m/yyyy), monto_comprobante (number)}`. Lucode returns `fecha_emision` as ISO (`yyyy-mm-dd`) and `monto_total_general` as a string, so `_formatear_fecha` (ISO → `d/m/yyyy`) and `_parsear_monto` (str → float) adapt them; both are defensive (pass-through / `0.0` on bad input).
- **Error-handling asymmetry (intentional):** Lucode failures raise `ValueError` and abort the request (Lucode data is essential). Tracker failures are swallowed and return an empty `DatosProveedor()` (supplier data is best-effort). Preserve this when editing.
- **`src/schemas.py`** — Pydantic models. `ConsultaResponse` extends `TotalesFactura` (flat invoice totals) and adds `fecha_emision`, nested `proveedor` and `items`; `ConsultaResponseV2` extends it with the v2-only fields. All numeric totals are serialized as **strings** (e.g. `"0.00"`), not numbers.
- **`src/security.py`** — `verify_api_key` compares the caller's key against `settings.API_KEY`. Missing key → 401, wrong key → 403. The health check `GET /` is outside the router and unauthenticated.

## Auth header

Callers authenticate with the **`Authorization`** header (`src/security.py`, `APIKeyHeader(name="Authorization")`) — not a Bearer scheme, just the raw key. Missing → 401, wrong → 403.

## Conventions

- Lucode upstream responses are defensively parsed: success is gated on `data.get("success")` plus presence of `payload`; multiple error shapes (`message`-only, `error` key) are normalized into `ValueError`. Follow the same defensive `.get(...) or default` pattern when reading upstream JSON.
- `total_grav_oner` in the response is computed as `total_grav_oner + total_isc` from Lucode totals.
