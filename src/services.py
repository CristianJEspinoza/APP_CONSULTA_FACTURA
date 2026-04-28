import httpx
import asyncio
import logging

from src.config import get_settings
from src.schemas import (
    TotalesFactura,
    DocumentoRelacionado,
    DatosProveedor,
    ConsultaResponse,
)

logger = logging.getLogger(__name__)


class ReadAPI:
    """Servicio para consultar APIs externas de facturación."""

    def __init__(self):
        self.settings = get_settings()

    # ------------------------------------------------------------------ #
    #  API Lucode – datos de la factura
    # ------------------------------------------------------------------ #
    async def consult_api_lucode(
        self,
        client: httpx.AsyncClient,
        ruc: str,
        serie: str,
        numero: str,
        tipo_comprobante: str = "01",
    ) -> dict:
        """Consulta la API de Lucode y devuelve totales y estado del comprobante."""
        headers = {"Content-Type": "application/json"}
        if self.settings.API_TOKEN_LUCODE:
            headers["Authorization"] = self.settings.API_TOKEN_LUCODE

        payload = {
            "tipo_comprobante": tipo_comprobante,
            "ruc_emisor": ruc,
            "serie": serie,
            "numero": numero,
        }

        try:
            response = await client.post(
                self.settings.API_URL_BASE,
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            
            try:
                data = response.json()
            except Exception:
                response.raise_for_status()
                raise ValueError("Respuesta no válida de la API de Lucode")

            # Verificar errores en la respuesta basándonos en la API de Lucode
            if "message" in data and "success" not in data:
                raise ValueError(data.get("message", "Comprobante no disponible"))

            if "error" in data:
                raise ValueError(data.get("message", "Comprobante no disponible"))

            if not data.get("success") or "payload" not in data:
                raise ValueError(data.get("message", "No se pudo obtener los datos del comprobante"))

            payload_data = data["payload"]
            detalle = payload_data.get("detalle", {})

            # -- Extraer totales --
            detraccion = detalle.get("detraccion") or {}
            totales_raw = payload_data.get("totales", {})
            
            estado_comprobante = detalle.get("estado_comprobante", "")

            # -- Extraer documento relacionado (array → primer elemento) --
            docs_relacionados = detalle.get("documentos_relacionados") or []
            doc_rel = DocumentoRelacionado()
            if docs_relacionados:
                primer_doc = docs_relacionados[0]
                serie_rel = primer_doc.get("serie_comprobante", "")
                numero_rel = primer_doc.get("numero_comprobante", "")
                doc_rel = DocumentoRelacionado(
                    factura_relacionada=f"{serie_rel}-{numero_rel}" if serie_rel else "",
                    fecha_emision=primer_doc.get("fecha_emision", ""),
                )
            
            total_grav_oner = "{:.2f}".format(
                float(totales_raw.get("total_grav_oner") or 0) + 
                float(totales_raw.get("total_isc") or 0)
            )

            totales = TotalesFactura(
                codigo=detraccion.get("codigo", ""),
                descripcion=detraccion.get("descripcion", ""),
                documento_relacionado=doc_rel,
                monto_total_general=str(totales_raw.get("monto_total_general", "0.00")),
                total_grav_exonerado=str(totales_raw.get("total_grav_exonerado", "0.00")),
                total_grav_oner=total_grav_oner,
                total_igv=str(totales_raw.get("total_igv", "0.00")),
                total_inaf_oner=str(totales_raw.get("total_inaf_oner", "0.00")),
                total_valor_venta_exonerado=str(
                    totales_raw.get("total_valor_venta_exonerado", "0.00")
                ),
            )

            return {"totales": totales, "estado_comprobante": estado_comprobante}

        except ValueError:
            raise
        except httpx.HTTPStatusError as exc:
            logger.error("Lucode HTTP error: %s", exc.response.status_code)
            raise ValueError(f"Error de conexión con Lucode (HTTP {exc.response.status_code})")
        except Exception as exc:
            logger.error("Lucode error: %s", exc)
            raise ValueError(f"Error interno al consultar Lucode: {str(exc)}")

    # ------------------------------------------------------------------ #
    #  API PeruDevs – datos del proveedor
    # ------------------------------------------------------------------ #
    async def consult_api_peru_devs(
        self, client: httpx.AsyncClient, ruc: str
    ) -> DatosProveedor:
        """Consulta PeruDevs y devuelve condición + estado del proveedor."""
        params = {
            "document": ruc,
            "key": self.settings.API_KEY_PERU_DEVS,
        }

        try:
            response = await client.get(
                self.settings.API_URL_PERU_DEVS,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("estado") and "resultado" in data:
                resultado = data["resultado"]
                return DatosProveedor(
                    condicion=resultado.get("condicion", ""),
                    estado=resultado.get("estado", ""),
                )

            return DatosProveedor()

        except httpx.HTTPStatusError as exc:
            logger.error("PeruDevs HTTP error: %s", exc.response.status_code)
            return DatosProveedor()
        except Exception as exc:
            logger.error("PeruDevs error: %s", exc)
            return DatosProveedor()

    # ------------------------------------------------------------------ #
    #  Consulta unificada (ambas APIs en paralelo)
    # ------------------------------------------------------------------ #
    async def consultar_factura(
        self,
        ruc: str,
        serie: str,
        numero: str,
        tipo_comprobante: str = "01",
    ) -> ConsultaResponse:
        """
        Llama a Lucode y PeruDevs en **paralelo** y unifica los resultados.
        """
        async with httpx.AsyncClient() as client:
            lucode_task = self.consult_api_lucode(
                client, ruc, serie, numero, tipo_comprobante
            )
            peru_devs_task = self.consult_api_peru_devs(client, ruc)

            lucode_result, proveedor = await asyncio.gather(
                lucode_task, peru_devs_task
            )

        proveedor.estado_comprobante = lucode_result.get("estado_comprobante", "")

        totales = lucode_result["totales"]
        return ConsultaResponse(
            codigo=totales.codigo,
            descripcion=totales.descripcion,
            documento_relacionado=totales.documento_relacionado,
            monto_total_general=totales.monto_total_general,
            total_grav_exonerado=totales.total_grav_exonerado,
            total_grav_oner=totales.total_grav_oner,
            total_igv=totales.total_igv,
            total_inaf_oner=totales.total_inaf_oner,
            total_valor_venta_exonerado=totales.total_valor_venta_exonerado,
            proveedor=proveedor,
        )
