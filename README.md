# 📄 API Consulta Documentos Electrónicos

API REST construida con **FastAPI** para consultar comprobantes electrónicos SUNAT. Unifica en una sola respuesta los datos de facturación (vía **Lucode**) con la información del proveedor (vía **PeruDevs**), ejecutando ambas consultas en **paralelo** para máxima velocidad.

---

## 🚀 Características

- ⚡ **Alta velocidad** — FastAPI + Uvicorn (ASGI asíncrono)
- 🔄 **Consultas paralelas** — Lucode y PeruDevs se consultan simultáneamente con `asyncio.gather`
- 📋 **Documentación automática** — Swagger UI en `/docs` y ReDoc en `/redoc`
- ✅ **Validación de datos** — Schemas Pydantic con validación automática de request/response
- 🔐 **Autenticación por API Key** — Protección de endpoints con header `Authorization`
- 🔒 **Variables de entorno** — Configuración segura vía `.env`
- 🌐 **CORS habilitado** — Listo para consumir desde cualquier frontend

---

## 📁 Estructura del Proyecto

```
APP_CONSULTA_FACTURA/
├── app.py                  # Entry point — FastAPI app + CORS + router
├── requirements.txt        # Dependencias del proyecto
├── .env                    # Variables de entorno (tokens API)
├── .gitignore
├── README.md
└── src/
    ├── __init__.py
    ├── config.py           # Configuración centralizada (pydantic-settings)
    ├── schemas.py          # Modelos Pydantic (request/response)
    ├── security.py         # Autenticación por API Key (Authorization)
    ├── services.py         # ReadAPI — lógica de consulta a APIs externas
    └── routes.py           # Endpoints de la API
```

---

## ⚙️ Requisitos Previos

- **Python 3.11** o **3.12** o **3.13** (Python 3.14 no es compatible con pydantic-core aún)
- Tokens de acceso para:
  - **Lucode** (API SUNAT de comprobantes)
  - **PeruDevs** (API de consulta de RUC)

---

## 🛠️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/CristianJEspinoza/APP_CONSULTA_FACTURA.git
cd APP_CONSULTA_FACTURA
```

### 2. Crear entorno virtual

```bash
# Windows (usando Python 3.11)
py -3.11 -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
# API Lucode
API_URL_BASE=https://dev.apisunat.pe/api/v1/sunat/comprobante
API_TOKEN_LUCODE=tu_token_aqui

# API PeruDevs
API_URL_PERU_DEVS=https://api.perudevs.com/api/v1/ruc
API_KEY_PERU_DEVS=tu_key_aqui

# Seguridad — API Key para proteger esta API
API_KEY=tu_api_key_aqui
```

> 💡 **Tip:** Puedes generar una API Key segura con:
>
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(32))"
> ```

---

## ▶️ Ejecución

### Modo desarrollo (con hot-reload)

```bash
uvicorn app:app --reload --port 8000
```

### Modo producción

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

La API estará disponible en: `http://127.0.0.1:8000`

---

## 📖 Documentación Interactiva

Una vez ejecutada la API, accede a la documentación generada automáticamente:

| Herramienta            | URL                                                                   |
| ---------------------- | --------------------------------------------------------------------- |
| **Swagger UI**   | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)                 |
| **ReDoc**        | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)               |
| **OpenAPI JSON** | [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) |

---

## 🔐 Autenticación

Todos los endpoints bajo `/api/v1/*` requieren el header `Authorization` con una clave válida.

| Header            | Valor                              | Requerido                   |
| ----------------- | ---------------------------------- | --------------------------- |
| `Authorization` | Tu API Key configurada en `.env` | ✅ Sí (para `/api/v1/*`) |

**Ejemplo de header:**

```
Authorization: Rk497drCAbw6S5azXBK9dfbCKpF-s0iZEolWBuUzaqk
```

> ⚠️ El endpoint `GET /` (health check) **no** requiere autenticación.

---

## 📡 Endpoints

### `GET /` — Health Check

Verifica que la API está corriendo. **No requiere API Key.**

**Response:**

```json
{
  "status": "ok",
  "message": "API Consulta Factura v1.0.0"
}
```

---

### `POST /api/v1/consultar-factura` — Consultar Factura 🔐

Consulta los datos de un comprobante electrónico y la información del proveedor de forma unificada.

> 🔑 **Requiere header:** Authorization y Content-Type

#### Request Body

```json
{
  "tipo_comprobante": "01",
  "ruc_emisor": "20100190797",
  "serie": "F081",
  "numero": "1114003"
}
```

| Campo                | Tipo       | Requerido             | Descripción                             |
| -------------------- | ---------- | --------------------- | ---------------------------------------- |
| `tipo_comprobante` | `string` | No (default:`"01"`) | Tipo de comprobante (`01` = Factura)   |
| `ruc_emisor`       | `string` | ✅ Sí                | RUC del emisor (11 dígitos)             |
| `serie`            | `string` | ✅ Sí                | Serie del comprobante (ej:`F081`)      |
| `numero`           | `string` | ✅ Sí                | Número del comprobante (ej:`1114003`) |

#### Response Exitosa (200)

```json
{
  "codigo": "035",
  "descripcion": "Bienes exonerados del IGV",
  "documento_relacionado": {
    "factura_relacionada": "F081-1120054",
    "fecha_emision": "2025-02-14"
  },
  "monto_total_general": "67.38",
  "total_grav_exonerado": "0.00",
  "total_grav_oner": "57.10",
  "total_igv": "10.28",
  "total_inaf_oner": "0.00",
  "total_valor_venta_exonerado": "0.00",
  "proveedor": {
    "condicion": "HABIDO",
    "estado": "ACTIVO",
    "estado_comprobante": "Aceptado"
  },
  "items": [
    { "codigo": "4800006", "valor_venta": "61.34" },
    { "codigo": "5101017", "valor_venta": "83.75" },
    { "codigo": "3201022", "valor_venta": "2727.38" }
  ]
}
```

> 📦 El campo `items` lista los productos del comprobante. Por cada item, `codigo` corresponde a `identificacion_interna` y `valor_venta` al valor de venta del item en Lucode.

#### Response de Error (422 — Validación)

```json
{
  "detail": [
    {
      "loc": ["body", "ruc_emisor"],
      "msg": "String should have at least 11 characters",
      "type": "string_too_short"
    }
  ]
}
```

#### Response de Error (401 — Sin API Key)

```json
{
  "detail": "API Key requerida. Envía el header 'Authorization'."
}
```

#### Response de Error (403 — API Key Inválida)

```json
{
  "detail": "API Key inválida."
}
```

#### Response de Error (500 — Error Interno)

```json
{
  "success": false,
  "message": "Error en la consulta",
  "detail": "Descripción del error"
}
```

---

## 🔧 Dependencias

| Paquete               | Versión | Propósito                                        |
| --------------------- | -------- | ------------------------------------------------- |
| `fastapi`           | 0.115.12 | Framework web ASGI de alto rendimiento            |
| `uvicorn[standard]` | 0.34.2   | Servidor ASGI (con extras: watchfiles, httptools) |
| `httpx`             | 0.28.1   | Cliente HTTP async para llamadas a APIs externas  |
| `pydantic`          | 2.11.2   | Validación de datos y serialización             |
| `pydantic-settings` | 2.9.1    | Carga de configuración desde `.env`            |
| `python-dotenv`     | 1.1.0    | Lectura de archivos `.env`                      |

---

## 🏗️ Arquitectura

```
┌─────────────┐     POST /api/v1/consultar-factura     ┌──────────────┐
│   Cliente    │ ──────────────────────────────────────► │   FastAPI    │
│  (Frontend)  │  Header: Authorization: <key>          │   Router     │
└─────────────┘ ◄────────────────────────────────────── └──────┬───────┘
                        Respuesta unificada                    │
                                                    ┌──────────▼──────────┐
                                                    │   🔐 Security      │
                                                    │  (verify_api_key)  │
                                                    └──────────┬──────────┘
                                                               │ ✅ Key válida
                                                    ┌──────────▼──────────┐
                                                    │     ReadAPI         │
                                                    │   (services.py)    │
                                                    └──────────┬──────────┘
                                                               │
                                              asyncio.gather (paralelo)
                                                    ┌──────────┴──────────┐
                                                    │                     │
                                           ┌────────▼────────┐  ┌────────▼────────┐
                                           │   API Lucode    │  │  API PeruDevs   │
                                           │  (Comprobante)  │  │     (RUC)       │
                                           │                 │  │                 │
                                           │ • Items         │  │ • Condición     │
                                           │ • Totales       │  │ • Estado        │
                                           │ • Detracción    │  │                 │
                                           └─────────────────┘  └─────────────────┘
```

---

## 📝 Ejemplo con cURL

```bash
curl -X POST http://127.0.0.1:8000/api/v1/consultar-factura \
  -H "Content-Type: application/json" \
  -H "Authorization: tu_api_key_aqui" \
  -d '{
    "tipo_comprobante": "01",
    "ruc_emisor": "20100190797",
    "serie": "F081",
    "numero": "1114003"
  }'
```

**Sin API Key (error 401):**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/consultar-factura \
  -H "Content-Type: application/json" \
  -d '{"ruc_emisor": "20100190797", "serie": "F081", "numero": "1114003"}'
# {"detail": "API Key requerida. Envía el header 'Authorization'."}
```

---

## 📄 Licencia

Este proyecto es de uso privado.
