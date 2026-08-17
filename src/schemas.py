from pydantic import BaseModel, Field


class ConsultaRequest(BaseModel):
    """Esquema de entrada para consultar una factura."""
    tipo_comprobante: str = Field(default="01", description="Tipo de comprobante (01 = Factura)")
    ruc_emisor: str = Field(..., description="RUC del emisor", min_length=11, max_length=11)
    serie: str = Field(..., description="Serie del comprobante (ej: F081)")
    numero: str = Field(..., description="Número del comprobante (ej: 1114003)")


class DocumentoRelacionado(BaseModel):
    """Documento relacionado (nota de crédito/débito)."""
    factura_relacionada: str = ""
    fecha_emision: str = ""


class DatosProveedor(BaseModel):
    """Datos del proveedor extraídos del tracker SUNAT."""
    condicion: str = ""
    estado: str = ""
    estado_comprobante: str = ""


class ItemFactura(BaseModel):
    """Item del comprobante extraído de Lucode (contrato v1)."""
    codigo_producto: str = ""
    valor_venta: str = "0.00"


class ItemFacturaV2(ItemFactura):
    """Item del comprobante (contrato v2): añade el tributo aplicado
    (`IGV` en facturas, `RET 4TA` en recibos por honorarios)."""
    impuesto_nombre_tributo: str = ""


class TotalesFactura(BaseModel):
    """Totales de la factura extraídos de Lucode."""
    codigo: str = ""
    descripcion: str = ""
    documento_relacionado: DocumentoRelacionado = DocumentoRelacionado()
    monto_total_general: str = "0.00"
    total_grav_exonerado: str = "0.00"
    total_grav_oner: str = "0.00"
    total_igv: str = "0.00"
    total_inaf_oner: str = "0.00"
    total_valor_venta_exonerado: str = "0.00"


class ConsultaResponse(TotalesFactura):
    """Respuesta unificada plana con datos de factura + proveedor (contrato v1).

    Contrato estable: no se le agregan campos nuevos. Las incorporaciones van
    en `ConsultaResponseV2`.
    """
    fecha_emision: str = ""
    proveedor: DatosProveedor = DatosProveedor()
    items: list[ItemFactura] = []


class ConsultaResponseV2(ConsultaResponse):
    """Respuesta unificada (contrato v2): añade la URL del PDF y, por item,
    el nombre del tributo aplicado."""
    pdf: str = ""
    items: list[ItemFacturaV2] = []


class ErrorResponse(BaseModel):
    """Respuesta de error."""
    success: bool = False
    message: str
    detail: str = ""
