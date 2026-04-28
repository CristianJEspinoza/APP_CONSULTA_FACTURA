from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes import router

app = FastAPI(
    title="API Consulta Documentos Electronicos",
    description=(
        "API para consultar documentos electronicos SUNAT. "
        "Unifica datos de los documentos electronicos (Lucode) con información "
        "del proveedor (PeruDevs) en una sola respuesta."
    ),
    version="1.0.0",
)

# CORS – permitir peticiones desde cualquier origen (ajustar en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rutas
app.include_router(router)


@app.get("/", tags=["Health"])
async def health_check():
    """Verificar que la API está corriendo."""
    return {"status": "ok", "message": "API Consulta Factura v1.0.0"}
