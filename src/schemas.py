"""
Módulo: schemas.py
Descripción: Esquemas Pydantic para validación de datos en la API REST.
Autor: David Llivigañay
Fecha: 2026-06-20
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ================ CONSTANTES ================

ESTADOS_CLIENTE = Literal['ACTIVO', 'INACTIVO']
ESTADOS_PRODUCTO = Literal['ACTIVO', 'INACTIVO']
ESTADOS_FACTURA = Literal['PENDIENTE', 'PAGADA', 'ANULADA', 'VENCIDA']


# ================ ESQUEMAS DE CLIENTES ================

class ClienteBase(BaseModel):
    """Esquema base para Cliente."""
    model_config = ConfigDict(from_attributes=True)
    
    identificacion: str = Field(
        ..., 
        min_length=10, 
        max_length=20, 
        description="Número de identificación (RUC/Cédula)"
    )
    nombre: str = Field(
        ..., 
        min_length=3, 
        max_length=100, 
        description="Nombre o razón social"
    )
    direccion: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Dirección del cliente"
    )
    telefono: Optional[str] = Field(
        None, 
        max_length=20, 
        description="Teléfono de contacto"
    )
    email: Optional[str] = Field(
        None, 
        max_length=100, 
        description="Correo electrónico"
    )
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Valida el formato del email."""
        if v and '@' not in v:
            raise ValueError('Email inválido')
        if v and '.' not in v.split('@')[-1]:
            raise ValueError('Email inválido: dominio sin punto')
        return v
    
    @field_validator('identificacion')
    @classmethod
    def validate_identificacion(cls, v: str) -> str:
        """Valida la identificación (solo números)."""
        if not v.isdigit():
            raise ValueError('La identificación debe contener solo números')
        return v


class ClienteCreate(ClienteBase):
    """Esquema para creación de Cliente."""
    pass


class ClienteUpdate(BaseModel):
    """Esquema para actualización de Cliente."""
    model_config = ConfigDict(from_attributes=True)
    
    identificacion: Optional[str] = Field(None, min_length=10, max_length=20)
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    direccion: Optional[str] = Field(None, max_length=255)
    telefono: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    estado: Optional[ESTADOS_CLIENTE] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and '@' not in v:
            raise ValueError('Email inválido')
        return v


class ClienteResponse(ClienteBase):
    """Esquema para respuesta de Cliente."""
    id_cliente: int
    estado: ESTADOS_CLIENTE
    fecha_creacion: datetime


# ================ ESQUEMAS DE PRODUCTOS ================

class ProductoBase(BaseModel):
    """Esquema base para Producto."""
    model_config = ConfigDict(from_attributes=True)
    
    codigo: str = Field(
        ..., 
        min_length=3, 
        max_length=20, 
        description="Código del producto"
    )
    nombre: str = Field(
        ..., 
        min_length=3, 
        max_length=100, 
        description="Nombre del producto"
    )
    descripcion: Optional[str] = Field(
        None, 
        description="Descripción del producto"
    )
    precio_unitario: float = Field(
        ..., 
        gt=0, 
        description="Precio unitario"
    )
    stock: int = Field(
        0, 
        ge=0, 
        description="Cantidad en stock"
    )
    id_tipo_iva: int = Field(
        ..., 
        description="ID del tipo de IVA"
    )
    
    @field_validator('codigo')
    @classmethod
    def validate_codigo(cls, v: str) -> str:
        """Valida que el código no tenga espacios."""
        if ' ' in v:
            raise ValueError('El código no debe contener espacios')
        return v.upper()
    
    @field_validator('precio_unitario')
    @classmethod
    def validate_precio(cls, v: float) -> float:
        """Valida que el precio sea positivo."""
        if v <= 0:
            raise ValueError('El precio unitario debe ser mayor a 0')
        return round(v, 2)  # Redondear a 2 decimales


class ProductoCreate(ProductoBase):
    """Esquema para creación de Producto."""
    pass


class ProductoUpdate(BaseModel):
    """Esquema para actualización de Producto."""
    model_config = ConfigDict(from_attributes=True)
    
    codigo: Optional[str] = Field(None, min_length=3, max_length=20)
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = None
    precio_unitario: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    id_tipo_iva: Optional[int] = None
    estado: Optional[ESTADOS_PRODUCTO] = None
    
    @field_validator('precio_unitario')
    @classmethod
    def validate_precio(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError('El precio unitario debe ser mayor a 0')
        return round(v, 2) if v is not None else v


class ProductoResponse(ProductoBase):
    """Esquema para respuesta de Producto."""
    id_producto: int
    estado: ESTADOS_PRODUCTO
    fecha_creacion: datetime
    
    # Campos adicionales de la consulta
    tipo_iva_nombre: Optional[str] = None
    porcentaje_iva: Optional[float] = None


# ================ ESQUEMAS DE DETALLE DE FACTURA ================

class DetalleFacturaBase(BaseModel):
    """Esquema base para Detalle de Factura."""
    model_config = ConfigDict(from_attributes=True)
    
    id_producto: int = Field(..., description="ID del producto")
    cantidad: int = Field(..., gt=0, description="Cantidad del producto")
    precio_unitario: float = Field(..., gt=0, description="Precio unitario")
    descuento: float = Field(0.0, ge=0, description="Descuento aplicado")
    
    @field_validator('precio_unitario')
    @classmethod
    def validate_precio(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('El precio unitario debe ser mayor a 0')
        return round(v, 2)
    
    @field_validator('descuento')
    @classmethod
    def validate_descuento(cls, v: float) -> float:
        if v < 0:
            raise ValueError('El descuento no puede ser negativo')
        return round(v, 2)
    
    @model_validator(mode='after')
    def validate_descuento_vs_precio(self) -> 'DetalleFacturaBase':
        """Valida que el descuento no sea mayor al precio total."""
        if self.descuento > (self.precio_unitario * self.cantidad):
            raise ValueError('El descuento no puede ser mayor al subtotal')
        return self


class DetalleFacturaResponse(BaseModel):
    """Esquema para respuesta de Detalle de Factura."""
    model_config = ConfigDict(from_attributes=True)
    
    id_detalle: int
    id_factura: int
    id_producto: int
    cantidad: int
    precio_unitario: float
    descuento: float
    subtotal: float
    
    # Campos adicionales
    producto_nombre: Optional[str] = None
    producto_codigo: Optional[str] = None


# ================ ESQUEMAS DE FACTURAS ================

class FacturaBase(BaseModel):
    """Esquema base para Factura."""
    model_config = ConfigDict(from_attributes=True)
    
    id_cliente: int = Field(..., description="ID del cliente")
    fecha_emision: Optional[date] = Field(
        None, 
        description="Fecha de emisión (default: hoy)"
    )
    fecha_vencimiento: Optional[date] = Field(
        None, 
        description="Fecha de vencimiento"
    )
    observaciones: Optional[str] = Field(
        None, 
        max_length=500, 
        description="Observaciones"
    )
    estado: ESTADOS_FACTURA = Field(
        'PENDIENTE', 
        description="Estado de la factura"
    )
    
    @model_validator(mode='after')
    def validate_fechas(self) -> 'FacturaBase':
        """Valida que las fechas sean consistentes."""
        if self.fecha_emision and self.fecha_vencimiento:
            if self.fecha_vencimiento < self.fecha_emision:
                raise ValueError(
                    'La fecha de vencimiento no puede ser anterior a la fecha de emisión'
                )
        return self


class FacturaCreate(BaseModel):
    """Esquema para creación de Factura."""
    model_config = ConfigDict(from_attributes=True)
    
    id_cliente: int = Field(..., description="ID del cliente")
    items: List[DetalleFacturaBase] = Field(
        ..., 
        min_length=1, 
        description="Lista de productos"
    )
    observaciones: Optional[str] = Field(
        None, 
        max_length=500, 
        description="Observaciones"
    )
    fecha_emision: Optional[date] = Field(
        None, 
        description="Fecha de emisión (default: hoy)"
    )
    fecha_vencimiento: Optional[date] = Field(
        None, 
        description="Fecha de vencimiento"
    )
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v: List[DetalleFacturaBase]) -> List[DetalleFacturaBase]:
        """Valida los items de la factura."""
        if not v:
            raise ValueError('La factura debe tener al menos un item')
        
        # Validar que no haya duplicados de productos
        productos = [item.id_producto for item in v]
        if len(productos) != len(set(productos)):
            raise ValueError('No se permiten productos duplicados en la factura')
        
        # Validar cantidades y precios
        for item in v:
            if item.cantidad <= 0:
                raise ValueError(f'Cantidad inválida para producto {item.id_producto}')
            if item.precio_unitario <= 0:
                raise ValueError(f'Precio inválido para producto {item.id_producto}')
        
        return v
    
    @model_validator(mode='after')
    def validate_fechas(self) -> 'FacturaCreate':
        """Valida que las fechas sean consistentes."""
        if self.fecha_emision and self.fecha_vencimiento:
            if self.fecha_vencimiento < self.fecha_emision:
                raise ValueError(
                    'La fecha de vencimiento no puede ser anterior a la fecha de emisión'
                )
        return self


class FacturaUpdate(BaseModel):
    """Esquema para actualización de Factura."""
    model_config = ConfigDict(from_attributes=True)
    
    estado: Optional[ESTADOS_FACTURA] = None
    fecha_vencimiento: Optional[date] = None
    observaciones: Optional[str] = Field(None, max_length=500)
    
    @model_validator(mode='after')
    def validate_fechas(self) -> 'FacturaUpdate':
        """Valida que las fechas sean consistentes."""
        if self.fecha_vencimiento:
            # No podemos validar contra fecha_emision aquí porque no la tenemos
            # Esta validación se hará en el servicio
            pass
        return self


class FacturaResponse(BaseModel):
    """Esquema para respuesta de Factura."""
    model_config = ConfigDict(from_attributes=True)
    
    id_factura: int
    numero_factura: str
    fecha_emision: date
    fecha_vencimiento: Optional[date]
    id_cliente: int
    subtotal: float
    iva: float
    total: float
    estado: ESTADOS_FACTURA
    observaciones: Optional[str]
    fecha_creacion: datetime
    
    # Relaciones
    cliente: Optional[ClienteResponse] = None
    detalles: List[DetalleFacturaResponse] = []
    
    @field_validator('subtotal', 'iva', 'total')
    @classmethod
    def round_decimal_fields(cls, v: float) -> float:
        """Redondea valores decimales a 2 decimales."""
        return round(v, 2)


# ================ ESQUEMAS DE RESPUESTA GENERICA ================

class ResponseBase(BaseModel):
    """Esquema base para respuestas de la API."""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[str]] = None


class PaginatedResponse(BaseModel):
    """Esquema para respuestas paginadas."""
    model_config = ConfigDict(from_attributes=True)
    
    items: List[Any]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ErrorResponse(BaseModel):
    """Esquema para respuestas de error."""
    model_config = ConfigDict(from_attributes=True)
    
    detail: str
    status_code: int = 400
    errors: Optional[Dict[str, List[str]]] = None


# ================ ESQUEMAS DE TIPOS DE IVA ================

class TipoIVABase(BaseModel):
    """Esquema base para Tipo de IVA."""
    model_config = ConfigDict(from_attributes=True)
    
    nombre: str = Field(..., min_length=2, max_length=50)
    porcentaje: float = Field(..., ge=0, le=100)
    
    @field_validator('porcentaje')
    @classmethod
    def validate_porcentaje(cls, v: float) -> float:
        """Valida y redondea el porcentaje."""
        if v < 0 or v > 100:
            raise ValueError('El porcentaje debe estar entre 0 y 100')
        return round(v, 2)


class TipoIVACreate(TipoIVABase):
    """Esquema para creación de Tipo de IVA."""
    pass


class TipoIVAUpdate(BaseModel):
    """Esquema para actualización de Tipo de IVA."""
    model_config = ConfigDict(from_attributes=True)
    
    nombre: Optional[str] = Field(None, min_length=2, max_length=50)
    porcentaje: Optional[float] = Field(None, ge=0, le=100)
    estado: Optional[Literal['ACTIVO', 'INACTIVO']] = None


class TipoIVAResponse(TipoIVABase):
    """Esquema para respuesta de Tipo de IVA."""
    id_tipo_iva: int
    estado: Literal['ACTIVO', 'INACTIVO']
    fecha_creacion: datetime


# ================ ESQUEMAS DE ESTADISTICAS ================

class EstadisticasResponse(BaseModel):
    """Esquema para estadísticas del sistema."""
    model_config = ConfigDict(from_attributes=True)
    
    total_clientes: int = Field(..., ge=0)
    total_productos: int = Field(..., ge=0)
    total_facturas: int = Field(..., ge=0)
    facturas_por_estado: Dict[str, int] = Field(..., description="Conteo por estado")
    total_ingresos: float = Field(..., ge=0)
    promedio_factura: float = Field(..., ge=0)
    periodo: Optional[str] = Field(None, description="Período de las estadísticas")
    
    @field_validator('total_ingresos', 'promedio_factura')
    @classmethod
    def round_decimal_fields(cls, v: float) -> float:
        """Redondea valores decimales a 2 decimales."""
        return round(v, 2)


# ================ ESQUEMAS DE FILTROS ================

class FacturaFilter(BaseModel):
    """Esquema para filtros de facturas."""
    model_config = ConfigDict(from_attributes=True)
    
    cliente_id: Optional[int] = None
    estado: Optional[ESTADOS_FACTURA] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    numero_factura: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_fechas(self) -> 'FacturaFilter':
        """Valida que las fechas sean consistentes."""
        if self.fecha_desde and self.fecha_hasta:
            if self.fecha_hasta < self.fecha_desde:
                raise ValueError(
                    'La fecha hasta no puede ser anterior a la fecha desde'
                )
        return self


class ProductoFilter(BaseModel):
    """Esquema para filtros de productos."""
    model_config = ConfigDict(from_attributes=True)
    
    nombre: Optional[str] = None
    codigo: Optional[str] = None
    stock_min: Optional[int] = Field(None, ge=0)
    stock_max: Optional[int] = Field(None, ge=0)
    estado: Optional[ESTADOS_PRODUCTO] = None
    id_tipo_iva: Optional[int] = None
    
    @model_validator(mode='after')
    def validate_stock(self) -> 'ProductoFilter':
        """Valida que los rangos de stock sean consistentes."""
        if self.stock_min is not None and self.stock_max is not None:
            if self.stock_max < self.stock_min:
                raise ValueError(
                    'El stock máximo no puede ser menor al stock mínimo'
                )
        return self


class ClienteFilter(BaseModel):
    """Esquema para filtros de clientes."""
    model_config = ConfigDict(from_attributes=True)
    
    nombre: Optional[str] = None
    identificacion: Optional[str] = None
    email: Optional[str] = None
    estado: Optional[ESTADOS_CLIENTE] = None