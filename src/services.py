import httpx
import logging

from datetime import datetime

from src.config import get_settings
from src.schemas import (
    TotalesFactura,
    DocumentoRelacionado,
    DatosProveedor,
    ItemFactura,
    ConsultaResponse,
)

logger = logging.getLogger(__name__)

# Recibo por Honorarios Electrónico: el tracker SUNAT no valida este tipo.
TIPO_RECIBO_HONORARIOS = "02"


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
            
            # En mayúsculas para igualar el formato del tracker SUNAT ("ACEPTADO").
            estado_comprobante = (detalle.get("estado_comprobante", "") or "").upper()
            fecha_emision = detalle.get("fecha_emision", "")

            # -- Extraer URL de descarga del PDF --
            url_descarga = payload_data.get("url_descarga") or {}
            pdf = url_descarga.get("pdf", "") or ""

            # -- Extraer items (codigo = identificacion_interna) --
            items_raw = payload_data.get("items") or []
            items = [
                ItemFactura(
                    codigo_producto=item.get("identificacion_interna", ""),
                    valor_venta=str(item.get("valor_venta", "0.00")),
                    impuesto_nombre_tributo=item.get("impuesto_nombre_tributo", "") or "",
                )
                for item in items_raw
            ]

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

            return {
                "totales": totales,
                "estado_comprobante": estado_comprobante,
                "fecha_emision": fecha_emision,
                "pdf": pdf,
                "items": items,
            }

        except ValueError:
            raise
        except httpx.HTTPStatusError as exc:
            logger.error("Lucode HTTP error: %s", exc.response.status_code)
            raise ValueError(f"Error de conexión con Lucode (HTTP {exc.response.status_code})")
        except Exception as exc:
            logger.error("Lucode error: %s", exc)
            raise ValueError(f"Error interno al consultar Lucode: {str(exc)}")

    # ------------------------------------------------------------------ #
    #  API Tracker SUNAT – datos del proveedor
    # ------------------------------------------------------------------ #
    @staticmethod
    def _formatear_fecha(fecha: str) -> str:
        """Convierte la fecha ISO (yyyy-mm-dd) de Lucode al formato d/m/yyyy
        que exige el tracker. Si viene en otro formato, la envía tal cual."""
        if not fecha:
            return ""
        try:
            dt = datetime.strptime(fecha, "%Y-%m-%d")
            return f"{dt.day}/{dt.month}/{dt.year}"
        except ValueError:
            return fecha

    @staticmethod
    def _parsear_monto(monto: str) -> float:
        """Convierte el monto total (string) a número para el tracker."""
        try:
            return float(monto)
        except (TypeError, ValueError):
            return 0.0

    async def consult_api_sunat_tracker(
        self,
        client: httpx.AsyncClient,
        ruc: str,
        tipo_comprobante: str,
        comprobante: str,
        fecha_emision: str,
        monto_comprobante: str,
    ) -> DatosProveedor:
        """Consulta el tracker SUNAT y devuelve condición, estado del RUC y
        estado del comprobante del proveedor."""
        api_key = (self.settings.API_KEY_SUNAT_TRACKER or "").strip()
        if not api_key:
            logger.error(
                "Tracker SUNAT: API_KEY_SUNAT_TRACKER vacía o no configurada "
                "(revisar las App Settings del entorno)."
            )
            return DatosProveedor()

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        }
        payload = {
            "numero_ruc": ruc,
            "tipo_comprobante": tipo_comprobante,
            "comprobante": comprobante,
            "fecha_emision": self._formatear_fecha(fecha_emision),
            "monto_comprobante": self._parsear_monto(monto_comprobante),
        }

        try:
            response = await client.post(
                self.settings.API_URL_SUNAT_TRACKER,
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success") and data.get("data"):
                resultado = data["data"]
                return DatosProveedor(
                    condicion=resultado.get("condDomiRuc", "") or "",
                    estado=resultado.get("estadoRuc", "") or "",
                    estado_comprobante=resultado.get("estadoCp", "") or "",
                )

            return DatosProveedor()

        except httpx.HTTPStatusError as exc:
            cuerpo = exc.response.text[:200]
            logger.error(
                "Tracker SUNAT HTTP %s (X-API-KEY len=%d): %s",
                exc.response.status_code,
                len(api_key),
                cuerpo,
            )
            return DatosProveedor()
        except Exception as exc:
            logger.error("Tracker SUNAT error: %s", exc)
            return DatosProveedor()

    # ------------------------------------------------------------------ #
    #  Consulta unificada (Lucode → Tracker SUNAT)
    # ------------------------------------------------------------------ #
    async def consultar_factura(
        self,
        ruc: str,
        serie: str,
        numero: str,
        tipo_comprobante: str = "01",
    ) -> ConsultaResponse:
        """
        Llama a Lucode y, con su fecha de emisión y monto total, consulta el
        tracker SUNAT para obtener los datos del proveedor. Unifica ambos
        resultados en una sola respuesta.
        """
        async with httpx.AsyncClient() as client:
            # Lucode primero: su fecha_emision y monto alimentan al tracker.
            lucode_result = await self.consult_api_lucode(
                client, ruc, serie, numero, tipo_comprobante
            )

            totales = lucode_result["totales"]
            fecha_emision = lucode_result.get("fecha_emision", "")
            pdf = lucode_result.get("pdf", "")

            proveedor = await self.consult_api_sunat_tracker(
                client,
                ruc=ruc,
                tipo_comprobante=tipo_comprobante,
                comprobante=f"{serie}-{numero}",
                fecha_emision=fecha_emision,
                monto_comprobante=totales.monto_total_general,
            )

            # Los recibos por honorarios (02) no los valida el tracker SUNAT
            # (responde "Error en consulta SUNAT: Sin código"), así que su
            # estado se toma del detalle que devuelve Lucode.
            if tipo_comprobante == TIPO_RECIBO_HONORARIOS:
                estado_lucode = lucode_result.get("estado_comprobante", "")
                if estado_lucode:
                    proveedor.estado_comprobante = estado_lucode

        return ConsultaResponse(
            codigo=totales.codigo,
            descripcion=totales.descripcion,
            documento_relacionado=totales.documento_relacionado,
            fecha_emision=fecha_emision,
            pdf=pdf,
            monto_total_general=totales.monto_total_general,
            total_grav_exonerado=totales.total_grav_exonerado,
            total_grav_oner=totales.total_grav_oner,
            total_igv=totales.total_igv,
            total_inaf_oner=totales.total_inaf_oner,
            total_valor_venta_exonerado=totales.total_valor_venta_exonerado,
            proveedor=proveedor,
            items=lucode_result.get("items", []),
        )
