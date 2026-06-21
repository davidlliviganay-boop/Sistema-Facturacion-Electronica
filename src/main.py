"""
Módulo: main.py
Descripción: API REST para el sistema de facturación electrónica.
Utiliza FastAPI para exponer los servicios de negocio.
Autor: David Llivigañay
Fecha: 2026-06-20
"""

import logging
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date

from fastapi import FastAPI, HTTPException, status, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Importar módulos del proyecto
try:
    from src.services import InvoiceService, ProductoService, ClienteService
    from src.schemas import (
        ClienteCreate, ClienteResponse, ClienteUpdate,
        ProductoCreate, ProductoResponse, ProductoUpdate,
        FacturaCreate, FacturaResponse, FacturaUpdate,
        DetalleFacturaResponse,
        EstadisticasResponse,
        ErrorResponse,
        ResponseBase,
        FacturaFilter,
        ProductoFilter,
        ClienteFilter,
        PaginatedResponse
    )
except ImportError:
    from services import InvoiceService, ProductoService, ClienteService
    from schemas import (
        ClienteCreate, ClienteResponse, ClienteUpdate,
        ProductoCreate, ProductoResponse, ProductoUpdate,
        FacturaCreate, FacturaResponse, FacturaUpdate,
        DetalleFacturaResponse,
        EstadisticasResponse,
        ErrorResponse,
        ResponseBase,
        FacturaFilter,
        ProductoFilter,
        ClienteFilter,
        PaginatedResponse
    )

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================ INICIALIZACIÓN DE FASTAPI ================

app = FastAPI(
    title="Sistema de Facturación Electrónica API",
    description="API REST para gestión de facturación electrónica",
    version="1.0.0",
    contact={
        "name": "Soporte Técnico",
        "email": "soporte@facturacion.com"
    },
    license_info={
        "name": "MIT",
    }
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================ DEPENDENCIAS ================

# Cache de servicios (singleton)
_invoice_service = None
_producto_service = None
_cliente_service = None

def get_invoice_service() -> InvoiceService:
    """Dependencia para obtener el servicio de facturación (singleton)."""
    global _invoice_service
    if _invoice_service is None:
        _invoice_service = InvoiceService()
    return _invoice_service

def get_producto_service() -> ProductoService:
    """Dependencia para obtener el servicio de productos (singleton)."""
    global _producto_service
    if _producto_service is None:
        _producto_service = ProductoService()
    return _producto_service

def get_cliente_service() -> ClienteService:
    """Dependencia para obtener el servicio de clientes (singleton)."""
    global _cliente_service
    if _cliente_service is None:
        _cliente_service = ClienteService()
    return _cliente_service

# ================ FUNCIONES AUXILIARES ================

def convert_factura_to_response(factura, cliente=None):
    """Convierte un objeto Factura a FacturaResponse."""
    if cliente is None:
        cliente_service = get_cliente_service()
        _, cliente, _ = cliente_service.get_client_by_id(factura.id_cliente)
    
    return FacturaResponse(
        id_factura=factura.id_factura,
        numero_factura=factura.numero_factura,
        fecha_emision=factura.fecha_emision,
        fecha_vencimiento=factura.fecha_vencimiento,
        id_cliente=factura.id_cliente,
        subtotal=float(factura.subtotal),
        iva=float(factura.iva),
        total=float(factura.total),
        estado=factura.estado,
        observaciones=factura.observaciones,
        fecha_creacion=factura.fecha_creacion,
        cliente=ClienteResponse(
            id_cliente=cliente.id_cliente,
            identificacion=cliente.identificacion,
            nombre=cliente.nombre,
            direccion=cliente.direccion,
            telefono=cliente.telefono,
            email=cliente.email,
            estado=cliente.estado,
            fecha_creacion=cliente.fecha_creacion
        ) if cliente else None,
        detalles=[
            DetalleFacturaResponse(
                id_detalle=d.id_detalle,
                id_factura=factura.id_factura,
                id_producto=d.id_producto,
                cantidad=d.cantidad,
                precio_unitario=float(d.precio_unitario),
                descuento=float(d.descuento),
                subtotal=float(d.subtotal)
            )
            for d in factura.detalles
        ]
    )

# ================ MANEJADORES DE ERRORES ================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Manejador personalizado para excepciones HTTP."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            status_code=exc.status_code
        ).model_dump()
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Manejador para errores de validación de Pydantic."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            detail="Error de validación",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            errors=exc.errors()
        ).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Manejador para excepciones no controladas."""
    logger.error(f"Error no controlado: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="Error interno del servidor",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ).model_dump()
    )

# ================ RUTAS DE SALUD ================

@app.get("/", tags=["Sistema"])
async def root():
    """Ruta raíz para verificar que la API está funcionando."""
    return {
        "message": "Sistema de Facturación Electrónica API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", tags=["Sistema"])
async def health_check():
    """Verifica el estado de la API y la conexión a la base de datos."""
    try:
        # Probar conexión a la base de datos
        db = get_invoice_service().db
        if db.test_connection():
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "degraded",
                "database": "disconnected",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ================ RUTAS DE CLIENTES ================

@app.get(
    "/api/v1/clientes",
    response_model=List[ClienteResponse],
    tags=["Clientes"],
    summary="Obtener todos los clientes"
)
async def get_clientes(
    incluir_inactivos: bool = Query(False, description="Incluir clientes inactivos"),
    service: ClienteService = Depends(get_cliente_service)
):
    """Obtiene todos los clientes."""
    success, clientes, error = service.get_all_clients(incluir_inactivos=incluir_inactivos)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error or "Error al obtener los clientes"
        )
    
    return [
        ClienteResponse(
            id_cliente=c.id_cliente,
            identificacion=c.identificacion,
            nombre=c.nombre,
            direccion=c.direccion,
            telefono=c.telefono,
            email=c.email,
            estado=c.estado,
            fecha_creacion=c.fecha_creacion
        )
        for c in clientes
    ]


@app.get(
    "/api/v1/clientes/{cliente_id}",
    response_model=ClienteResponse,
    tags=["Clientes"],
    summary="Obtener cliente por ID"
)
async def get_cliente(
    cliente_id: int,
    service: ClienteService = Depends(get_cliente_service)
):
    """Obtiene un cliente por su ID."""
    success, cliente, error = service.get_client_by_id(cliente_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error or "Cliente no encontrado"
        )
    
    return ClienteResponse(
        id_cliente=cliente.id_cliente,
        identificacion=cliente.identificacion,
        nombre=cliente.nombre,
        direccion=cliente.direccion,
        telefono=cliente.telefono,
        email=cliente.email,
        estado=cliente.estado,
        fecha_creacion=cliente.fecha_creacion
    )


@app.post(
    "/api/v1/clientes",
    response_model=ClienteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Clientes"],
    summary="Crear nuevo cliente"
)
async def create_cliente(
    cliente_data: ClienteCreate,
    service: ClienteService = Depends(get_cliente_service)
):
    """Crea un nuevo cliente."""
    try:
        # Implementación usando el servicio de cliente
        # Nota: Se necesita agregar el método create_cliente en ClienteService
        # Por ahora, lanzamos un error controlado
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Funcionalidad en desarrollo. Próximamente disponible."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear cliente: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.put(
    "/api/v1/clientes/{cliente_id}",
    response_model=ClienteResponse,
    tags=["Clientes"],
    summary="Actualizar cliente"
)
async def update_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    service: ClienteService = Depends(get_cliente_service)
):
    """Actualiza un cliente existente."""
    # Implementación pendiente
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Funcionalidad en desarrollo"
    )

# ================ RUTAS DE PRODUCTOS ================

@app.get(
    "/api/v1/productos",
    response_model=List[ProductoResponse],
    tags=["Productos"],
    summary="Obtener todos los productos"
)
async def get_productos(
    incluir_inactivos: bool = Query(False, description="Incluir productos inactivos"),
    service: ProductoService = Depends(get_producto_service)
):
    """Obtiene todos los productos."""
    success, productos, error = service.get_all_products(incluir_inactivos=incluir_inactivos)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error or "Error al obtener los productos"
        )
    
    return [
        ProductoResponse(
            id_producto=p.id_producto,
            codigo=p.codigo,
            nombre=p.nombre,
            descripcion=p.descripcion,
            precio_unitario=float(p.precio_unitario),
            stock=p.stock,
            id_tipo_iva=p.id_tipo_iva,
            estado=p.estado,
            fecha_creacion=p.fecha_creacion
        )
        for p in productos
    ]


@app.get(
    "/api/v1/productos/{producto_id}",
    response_model=ProductoResponse,
    tags=["Productos"],
    summary="Obtener producto por ID"
)
async def get_producto(
    producto_id: int,
    service: ProductoService = Depends(get_producto_service)
):
    """Obtiene un producto por su ID."""
    success, producto, error = service.get_product_by_id(producto_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error or "Producto no encontrado"
        )
    
    return ProductoResponse(
        id_producto=producto.id_producto,
        codigo=producto.codigo,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        precio_unitario=float(producto.precio_unitario),
        stock=producto.stock,
        id_tipo_iva=producto.id_tipo_iva,
        estado=producto.estado,
        fecha_creacion=producto.fecha_creacion
    )


@app.post(
    "/api/v1/productos",
    response_model=ProductoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Productos"],
    summary="Crear nuevo producto"
)
async def create_producto(
    producto_data: ProductoCreate,
    service: ProductoService = Depends(get_producto_service)
):
    """Crea un nuevo producto."""
    # Implementación pendiente
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Funcionalidad en desarrollo"
    )

# ================ RUTAS DE FACTURAS ================

@app.post(
    "/api/v1/facturas",
    response_model=FacturaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Facturas"],
    summary="Crear nueva factura",
    description="Crea una nueva factura con sus detalles. La operación es atómica (todo o nada)."
)
async def create_factura(
    factura_data: FacturaCreate,
    service: InvoiceService = Depends(get_invoice_service)
):
    """
    Crea una nueva factura.
    
    - **id_cliente**: ID del cliente
    - **items**: Lista de productos con cantidades y precios
    - **observaciones**: Observaciones adicionales
    """
    try:
        # Convertir items a lista de diccionarios para el servicio
        items_list = []
        for item in factura_data.items:
            item_dict = {
                'id_producto': item.id_producto,
                'cantidad': item.cantidad,
                'precio_unitario': item.precio_unitario,
                'descuento': item.descuento or 0.0
            }
            items_list.append(item_dict)
        
        # Crear la factura
        success, factura, error = service.create_invoice(
            cliente_id=factura_data.id_cliente,
            items_list=items_list,
            observaciones=factura_data.observaciones or ""
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error or "Error al crear la factura"
            )
        
        # Obtener información del cliente para la respuesta
        cliente_service = get_cliente_service()
        _, cliente, _ = cliente_service.get_client_by_id(factura.id_cliente)
        
        return convert_factura_to_response(factura, cliente)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear factura: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get(
    "/api/v1/facturas/{factura_id}",
    response_model=FacturaResponse,
    tags=["Facturas"],
    summary="Obtener factura por ID"
)
async def get_factura(
    factura_id: int,
    service: InvoiceService = Depends(get_invoice_service)
):
    """Obtiene una factura por su ID."""
    success, factura, error = service.get_invoice_by_id(factura_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error or "Factura no encontrada"
        )
    
    # Obtener información del cliente
    cliente_service = get_cliente_service()
    _, cliente, _ = cliente_service.get_client_by_id(factura.id_cliente)
    
    return convert_factura_to_response(factura, cliente)


@app.get(
    "/api/v1/clientes/{cliente_id}/facturas",
    response_model=List[FacturaResponse],
    tags=["Facturas"],
    summary="Obtener facturas de un cliente"
)
async def get_facturas_cliente(
    cliente_id: int,
    service: InvoiceService = Depends(get_invoice_service)
):
    """Obtiene todas las facturas de un cliente."""
    success, facturas, error = service.get_invoices_by_client(cliente_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error or "Error al obtener las facturas del cliente"
        )
    
    # Obtener información del cliente
    cliente_service = get_cliente_service()
    _, cliente, _ = cliente_service.get_client_by_id(cliente_id)
    
    return [convert_factura_to_response(f, cliente) for f in facturas]


@app.put(
    "/api/v1/facturas/{factura_id}/estado",
    response_model=ResponseBase,
    tags=["Facturas"],
    summary="Actualizar estado de factura"
)
async def update_factura_estado(
    factura_id: int,
    estado: str = Query(
        ..., 
        description="Nuevo estado (PENDIENTE, PAGADA, ANULADA, VENCIDA)",
        regex="^(PENDIENTE|PAGADA|ANULADA|VENCIDA)$"
    ),
    service: InvoiceService = Depends(get_invoice_service)
):
    """
    Actualiza el estado de una factura.
    
    Estados válidos:
    - **PENDIENTE**: Factura emitida, pendiente de pago
    - **PAGADA**: Factura pagada
    - **ANULADA**: Factura anulada
    - **VENCIDA**: Factura vencida
    """
    try:
        success, error = service.update_invoice_status(factura_id, estado)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error or "Error al actualizar el estado de la factura"
            )
        
        return ResponseBase(
            success=True,
            message=f"Factura {factura_id} actualizada a estado: {estado}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar estado: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post(
    "/api/v1/facturas/{factura_id}/anular",
    response_model=ResponseBase,
    tags=["Facturas"],
    summary="Anular factura",
    description="Anula una factura y restaura el stock de los productos"
)
async def anular_factura(
    factura_id: int,
    motivo: Optional[str] = Query(None, description="Motivo de la anulación"),
    service: InvoiceService = Depends(get_invoice_service)
):
    """
    Anula una factura existente.
    
    - Restaura el stock de los productos
    - Cambia el estado a ANULADA
    - Registra el motivo de anulación
    """
    try:
        success, error = service.anular_factura(factura_id, motivo or "Anulación por API")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error or "Error al anular la factura"
            )
        
        return ResponseBase(
            success=True,
            message=f"Factura {factura_id} anulada exitosamente"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al anular factura: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get(
    "/api/v1/facturas/buscar",
    response_model=List[FacturaResponse],
    tags=["Facturas"],
    summary="Buscar facturas con filtros"
)
async def buscar_facturas(
    cliente_id: Optional[int] = Query(None, description="ID del cliente"),
    estado: Optional[str] = Query(None, description="Estado de la factura"),
    fecha_desde: Optional[date] = Query(None, description="Fecha desde"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha hasta"),
    numero_factura: Optional[str] = Query(None, description="Número de factura"),
    service: InvoiceService = Depends(get_invoice_service)
):
    """
    Busca facturas aplicando filtros.
    """
    # Validar fechas
    if fecha_desde and fecha_hasta and fecha_hasta < fecha_desde:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha hasta no puede ser anterior a la fecha desde"
        )
    
    try:
        # Implementación básica - en producción se haría con consulta SQL directa
        # Por ahora, obtener todas y filtrar en memoria (solo para demostración)
        if cliente_id:
            success, facturas, error = service.get_invoices_by_client(cliente_id)
        else:
            # Obtener todas las facturas (se necesita implementar este método)
            success, facturas, error = service.get_all_invoices()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error or "Error al buscar facturas"
            )
        
        # Aplicar filtros adicionales
        if estado:
            facturas = [f for f in facturas if f.estado == estado]
        if fecha_desde:
            facturas = [f for f in facturas if f.fecha_emision >= fecha_desde]
        if fecha_hasta:
            facturas = [f for f in facturas if f.fecha_emision <= fecha_hasta]
        if numero_factura:
            facturas = [f for f in facturas if numero_factura in f.numero_factura]
        
        # Obtener información del cliente
        cliente_service = get_cliente_service()
        
        result = []
        for f in facturas:
            _, cliente, _ = cliente_service.get_client_by_id(f.id_cliente)
            result.append(convert_factura_to_response(f, cliente))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al buscar facturas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ================ RUTAS DE ESTADÍSTICAS ================

@app.get(
    "/api/v1/estadisticas",
    response_model=EstadisticasResponse,
    tags=["Estadísticas"],
    summary="Obtener estadísticas del sistema"
)
async def get_estadisticas(
    service: InvoiceService = Depends(get_invoice_service)
):
    """
    Retorna estadísticas del sistema.
    """
    try:
        # Obtener total de clientes
        cliente_service = get_cliente_service()
        success, clientes, _ = cliente_service.get_all_clients()
        total_clientes = len(clientes) if success else 0
        
        # Obtener total de productos
        producto_service = get_producto_service()
        success, productos, _ = producto_service.get_all_products()
        total_productos = len(productos) if success else 0
        
        # Obtener estadísticas de facturas usando consulta directa
        db = service.db
        
        # Total de facturas
        query = "SELECT COUNT(*) as total FROM facturas"
        success, result, _ = db.fetch_one(query)
        total_facturas = result['total'] if result else 0
        
        # Facturas por estado
        query = """
            SELECT estado, COUNT(*) as cantidad 
            FROM facturas 
            GROUP BY estado
        """
        success, resultados, _ = db.fetch_all(query)
        facturas_por_estado = {}
        if success and resultados:
            for r in resultados:
                facturas_por_estado[r['estado']] = r['cantidad']
        
        # Total de ingresos (facturas pagadas)
        query = """
            SELECT SUM(total) as total_ingresos 
            FROM facturas 
            WHERE estado = 'PAGADA'
        """
        success, result, _ = db.fetch_one(query)
        total_ingresos = float(result['total_ingresos']) if result and result['total_ingresos'] else 0.0
        
        # Promedio de factura
        query = """
            SELECT AVG(total) as promedio 
            FROM facturas 
            WHERE estado = 'PAGADA'
        """
        success, result, _ = db.fetch_one(query)
        promedio_factura = float(result['promedio']) if result and result['promedio'] else 0.0
        
        return EstadisticasResponse(
            total_clientes=total_clientes,
            total_productos=total_productos,
            total_facturas=total_facturas,
            facturas_por_estado=facturas_por_estado,
            total_ingresos=round(total_ingresos, 2),
            promedio_factura=round(promedio_factura, 2),
            periodo=datetime.now().strftime("%Y-%m")
        )
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas"
        )

# ================ RUTAS DE EXPORTACIÓN ================

@app.get(
    "/api/v1/facturas/{factura_id}/pdf",
    tags=["Facturas"],
    summary="Exportar factura a PDF"
)
async def export_factura_pdf(
    factura_id: int,
    service: InvoiceService = Depends(get_invoice_service)
):
    """
    Exporta una factura a formato PDF.
    """
    # Implementación pendiente
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Funcionalidad en desarrollo"
    )

# ================ DOCUMENTACIÓN PERSONALIZADA ================

@app.get("/api/v1", tags=["Sistema"])
async def api_info():
    """Información general de la API."""
    return {
        "name": "Sistema de Facturación Electrónica API",
        "version": "1.0.0",
        "description": "API para gestión de facturación electrónica",
        "endpoints": {
            "clientes": {
                "list": "GET /api/v1/clientes",
                "get": "GET /api/v1/clientes/{id}",
                "create": "POST /api/v1/clientes",
                "update": "PUT /api/v1/clientes/{id}"
            },
            "productos": {
                "list": "GET /api/v1/productos",
                "get": "GET /api/v1/productos/{id}",
                "create": "POST /api/v1/productos",
                "update": "PUT /api/v1/productos/{id}"
            },
            "facturas": {
                "create": "POST /api/v1/facturas",
                "get": "GET /api/v1/facturas/{id}",
                "update_status": "PUT /api/v1/facturas/{id}/estado",
                "anular": "POST /api/v1/facturas/{id}/anular",
                "buscar": "GET /api/v1/facturas/buscar",
                "pdf": "GET /api/v1/facturas/{id}/pdf"
            },
            "estadisticas": {
                "get": "GET /api/v1/estadisticas"
            }
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }

# ================ PUNTO DE ENTRADA PARA DESARROLLO ================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )