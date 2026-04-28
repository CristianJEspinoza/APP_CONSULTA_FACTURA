from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.schemas import ConsultaRequest, ConsultaResponse, ErrorResponse
from src.security import verify_api_key
from src.services import ReadAPI

router = APIRouter(
    prefix="/api/v1",
    tags=["Facturación"],
    dependencies=[Depends(verify_api_key)],
)

read_api = ReadAPI()


@router.post(
    "/consultar-factura",
    response_model=ConsultaResponse,
    summary="Consultar factura y datos del proveedor",
    description=(
        "Consulta la factura en la API de Lucode y los datos del proveedor "
        "en PeruDevs de forma paralela. Devuelve una respuesta unificada "
        "con los totales de la factura, los items, y el estado/condición "
        "del proveedor."
    ),
    responses={
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
)
async def consultar_factura(request: ConsultaRequest) -> ConsultaResponse:
    """Endpoint principal que unifica datos de Lucode + PeruDevs."""
    try:
        resultado = await read_api.consultar_factura(
            ruc=request.ruc_emisor,
            serie=request.serie,
            numero=request.numero,
            tipo_comprobante=request.tipo_comprobante,
        )
        return resultado

    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(exc)
            }
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Error interno del servidor",
                "detail": str(exc)
            }
        )
