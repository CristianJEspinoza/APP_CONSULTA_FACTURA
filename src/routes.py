from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.schemas import (
    ConsultaRequest,
    ConsultaResponse,
    ConsultaResponseV2,
    ErrorResponse,
)
from src.security import verify_api_key
from src.services import ReadAPI

router = APIRouter(
    prefix="/api/v1",
    tags=["Facturación v1"],
    dependencies=[Depends(verify_api_key)],
)

router_v2 = APIRouter(
    prefix="/api/v2",
    tags=["Facturación v2"],
    dependencies=[Depends(verify_api_key)],
)

read_api = ReadAPI()

_DESCRIPCION_BASE = (
    "Consulta la factura en la API de Lucode y, con su fecha de emisión y "
    "monto total, consulta el tracker SUNAT para los datos del proveedor. "
    "Devuelve una respuesta unificada con los totales de la factura, los "
    "items, y el estado/condición del proveedor."
)


async def _consultar(request: ConsultaRequest) -> ConsultaResponseV2 | JSONResponse:
    """Ejecuta la consulta unificada y normaliza los errores.

    Devuelve el contrato v2 (superconjunto) o un `JSONResponse` de error.
    """
    try:
        return await read_api.consultar_factura(
            ruc=request.ruc_emisor,
            serie=request.serie,
            numero=request.numero,
            tipo_comprobante=request.tipo_comprobante,
        )

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


@router.post(
    "/consultar-factura",
    response_model=ConsultaResponse,
    summary="Consultar factura y datos del proveedor (v1)",
    description=_DESCRIPCION_BASE,
    responses={
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
)
async def consultar_factura(request: ConsultaRequest):
    """Endpoint v1 — contrato estable, sin `pdf` ni `impuesto_nombre_tributo`."""
    resultado = await _consultar(request)
    if isinstance(resultado, JSONResponse):
        return resultado

    # Proyección al contrato v1: los campos exclusivos de v2 se descartan.
    return ConsultaResponse.model_validate(resultado.model_dump())


@router_v2.post(
    "/consultar-factura",
    response_model=ConsultaResponseV2,
    summary="Consultar factura y datos del proveedor (v2)",
    description=(
        _DESCRIPCION_BASE
        + " Frente a v1 añade la URL del `pdf` del comprobante y, en cada item, "
        "`impuesto_nombre_tributo` (`IGV` en facturas, `RET 4TA` en recibos "
        "por honorarios)."
    ),
    responses={
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
)
async def consultar_factura_v2(request: ConsultaRequest):
    """Endpoint v2 — respuesta completa."""
    return await _consultar(request)
