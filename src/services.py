"""
Módulo: services.py
Descripción: Servicios de negocio para el sistema de facturación.
Implementa la lógica transaccional para la creación de facturas.
Autor: David Llivigañay
Fecha: 2026-06-20
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date
import re
import sys
import os

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar módulos del proyecto
try:
    from src.database import get_db_connection
    from src.models import Factura, DetalleFactura, Producto, Cliente, ValidationError
except ImportError:
    from database import get_db_connection
    from models import Factura, DetalleFactura, Producto, Cliente, ValidationError

# Configurar logging
logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Servicio de facturación que implementa la lógica de negocio.
    Garantiza la atomicidad de las facturas mediante transacciones.
    """
    
    def __init__(self):
        """Inicializa el servicio de facturación."""
        self.db = get_db_connection()
        logger.info("InvoiceService inicializado")
    
    def _generar_numero_factura(self) -> str:
        """
        Genera un número único de factura.
        Formato: FAC-YYYY-XXXXX (ejemplo: FAC-2026-00001)
        
        Returns:
            str: Número de factura generado.
        """
        year = datetime.now().year
        # Obtener el último número de factura
        query = """
            SELECT numero_factura 
            FROM facturas 
            WHERE numero_factura LIKE %s 
            ORDER BY id_factura DESC 
            LIMIT 1
        """
        params = (f'FAC-{year}-%',)
        success, result, error = self.db.fetch_one(query, params)
        
        if success and result:
            # Extraer el número secuencial
            last_num = result['numero_factura']
            match = re.search(r'FAC-\d+-(\d+)', last_num)
            if match:
                seq = int(match.group(1)) + 1
            else:
                seq = 1
        else:
            seq = 1
        
        # Formatear con ceros a la izquierda (5 dígitos)
        return f"FAC-{year}-{seq:05d}"
    
    def _validar_factura(self, factura: Factura) -> Tuple[bool, Optional[str]]:
        """
        Valida los datos de la factura antes de crear.
        
        Args:
            factura (Factura): Objeto factura a validar.
            
        Returns:
            Tuple[bool, Optional[str]]: (válido, mensaje_error)
        """
        try:
            # Validar que tenga al menos un detalle
            if not factura.detalles or len(factura.detalles) == 0:
                return False, "La factura debe tener al menos un detalle"
            
            # Validar que el cliente existe
            query = "SELECT id_cliente FROM clientes WHERE id_cliente = %s AND estado = 'ACTIVO'"
            params = (factura.id_cliente,)
            success, result, error = self.db.fetch_one(query, params)
            if not success or not result:
                return False, f"El cliente con ID {factura.id_cliente} no existe o está inactivo"
            
            # Validar cada detalle
            for detalle in factura.detalles:
                if detalle.cantidad <= 0:
                    return False, f"La cantidad del producto {detalle.id_producto} debe ser mayor a 0"
                
                if detalle.precio_unitario <= 0:
                    return False, f"El precio del producto {detalle.id_producto} debe ser mayor a 0"
                
                # Validar que el producto existe y tiene stock suficiente
                query = """
                    SELECT id_producto, stock, nombre 
                    FROM productos 
                    WHERE id_producto = %s AND estado = 'ACTIVO'
                """
                params = (detalle.id_producto,)
                success, result, error = self.db.fetch_one(query, params)
                if not success or not result:
                    return False, f"El producto con ID {detalle.id_producto} no existe o está inactivo"
                
                # Validar stock
                if result['stock'] < detalle.cantidad:
                    return False, f"Stock insuficiente para el producto '{result['nombre']}'. " \
                                 f"Disponible: {result['stock']}, solicitado: {detalle.cantidad}"
            
            return True, None
            
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f"Error en validación: {e}")
            return False, f"Error en validación: {str(e)}"
    
    def create_invoice(self, cliente_id: int, items_list: List[Dict[str, Any]], 
                      observaciones: str = "") -> Tuple[bool, Optional[Factura], Optional[str]]:
        """
        Crea una nueva factura de forma atómica.
        
        Implementa la regla crítica: "Una factura es atómica".
        Si falla cualquier detalle, se hace rollback total.
        
        Args:
            cliente_id (int): ID del cliente.
            items_list (List[Dict]): Lista de items con id_producto, cantidad, precio_unitario.
            observaciones (str): Observaciones de la factura.
            
        Returns:
            Tuple[bool, Optional[Factura], Optional[str]]: 
                - Éxito de la operación
                - Objeto Factura creada
                - Mensaje de error (si existe)
        """
        connection = None
        cursor = None
        factura = None
        
        try:
            # 1. Crear el objeto Factura con sus detalles
            factura = Factura(
                numero_factura=self._generar_numero_factura(),
                fecha_emision=date.today(),
                id_cliente=cliente_id,
                observaciones=observaciones,
                estado='PENDIENTE'
            )
            
            # 2. Crear los detalles
            for item in items_list:
                detalle = DetalleFactura(
                    id_producto=item['id_producto'],
                    cantidad=item['cantidad'],
                    precio_unitario=Decimal(str(item.get('precio_unitario', 0))),
                    descuento=Decimal(str(item.get('descuento', 0)))
                )
                factura.agregar_detalle(detalle)
            
            # 3. Validar la factura
            valido, error = self._validar_factura(factura)
            if not valido:
                return False, None, error
            
            # 4. Calcular totales usando propiedades
            subtotal = factura.subtotal
            iva = factura.iva
            total = factura.total
            
            # 5. Obtener conexión y iniciar transacción
            connection = self.db.get_connection()
            connection.start_transaction()
            cursor = connection.cursor()
            
            logger.info(f"Iniciando creación de factura: {factura.numero_factura}")
            
            # 6. Insertar cabecera de factura
            query_cabecera = """
                INSERT INTO facturas (
                    numero_factura, fecha_emision, id_cliente, 
                    subtotal, iva, total, estado, observaciones
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params_cabecera = (
                factura.numero_factura,
                factura.fecha_emision,
                factura.id_cliente,
                float(subtotal),
                float(iva),
                float(total),
                factura.estado,
                factura.observaciones
            )
            
            cursor.execute(query_cabecera, params_cabecera)
            factura_id = cursor.lastrowid
            factura.id_factura = factura_id
            
            logger.info(f"Cabecera insertada. ID: {factura_id}")
            
            # 7. Insertar detalles de factura
            for detalle in factura.detalles:
                query_detalle = """
                    INSERT INTO detalle_factura (
                        id_factura, id_producto, cantidad, 
                        precio_unitario, descuento, subtotal
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                params_detalle = (
                    factura_id,
                    detalle.id_producto,
                    detalle.cantidad,
                    float(detalle.precio_unitario),
                    float(detalle.descuento),
                    float(detalle.subtotal)
                )
                
                cursor.execute(query_detalle, params_detalle)
                logger.debug(f"Detalle insertado: producto {detalle.id_producto}, " 
                           f"cantidad {detalle.cantidad}, subtotal {detalle.subtotal}")
            
            # 8. Actualizar stock de productos
            for detalle in factura.detalles:
                query_stock = """
                    UPDATE productos 
                    SET stock = stock - %s 
                    WHERE id_producto = %s
                """
                params_stock = (detalle.cantidad, detalle.id_producto)
                cursor.execute(query_stock, params_stock)
                logger.debug(f"Stock actualizado para producto {detalle.id_producto}")
            
            # 9. Confirmar transacción (COMMIT)
            connection.commit()
            
            logger.info(f"Factura {factura.numero_factura} creada exitosamente")
            
            # 10. Retornar la factura creada
            return True, factura, None
            
        except Exception as e:
            # 11. Revertir transacción (ROLLBACK)
            if connection:
                connection.rollback()
            error_msg = f"Error en la transacción: {str(e)}"
            logger.error(error_msg)
            if factura:
                logger.error(f"Factura: {factura.numero_factura}")
            import traceback
            traceback.print_exc()
            return False, None, error_msg
            
        finally:
            # 12. Cerrar recursos
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def get_invoice_by_id(self, factura_id: int) -> Tuple[bool, Optional[Factura], Optional[str]]:
        """
        Obtiene una factura por su ID incluyendo sus detalles.
        
        Args:
            factura_id (int): ID de la factura.
            
        Returns:
            Tuple[bool, Optional[Factura], Optional[str]]: 
                - Éxito de la operación
                - Objeto Factura
                - Mensaje de error (si existe)
        """
        try:
            # 1. Obtener cabecera
            query_cabecera = """
                SELECT f.*, c.nombre as cliente_nombre, c.identificacion as cliente_identificacion
                FROM facturas f
                LEFT JOIN clientes c ON f.id_cliente = c.id_cliente
                WHERE f.id_factura = %s
            """
            params = (factura_id,)
            success, result, error = self.db.fetch_one(query_cabecera, params)
            
            if not success or not result:
                return False, None, "Factura no encontrada"
            
            # 2. Crear objeto Factura
            factura = Factura(
                id_factura=result['id_factura'],
                numero_factura=result['numero_factura'],
                fecha_emision=result['fecha_emision'],
                fecha_vencimiento=result.get('fecha_vencimiento'),
                id_cliente=result['id_cliente'],
                estado=result['estado'],
                observaciones=result.get('observaciones', '')
            )
            
            # 3. Obtener detalles
            query_detalles = """
                SELECT d.*, p.nombre as producto_nombre, p.codigo as producto_codigo
                FROM detalle_factura d
                LEFT JOIN productos p ON d.id_producto = p.id_producto
                WHERE d.id_factura = %s
            """
            params_detalles = (factura_id,)
            success, detalles_result, error = self.db.fetch_all(query_detalles, params_detalles)
            
            if success and detalles_result:
                for detalle_data in detalles_result:
                    detalle = DetalleFactura(
                        id_detalle=detalle_data['id_detalle'],
                        id_producto=detalle_data['id_producto'],
                        cantidad=detalle_data['cantidad'],
                        precio_unitario=Decimal(str(detalle_data['precio_unitario'])),
                        descuento=Decimal(str(detalle_data.get('descuento', 0)))
                    )
                    factura.agregar_detalle(detalle)
            
            return True, factura, None
            
        except Exception as e:
            error_msg = f"Error al obtener factura: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def get_invoices_by_client(self, cliente_id: int) -> Tuple[bool, List[Factura], Optional[str]]:
        """
        Obtiene todas las facturas de un cliente.
        
        Args:
            cliente_id (int): ID del cliente.
            
        Returns:
            Tuple[bool, List[Factura], Optional[str]]: 
                - Éxito de la operación
                - Lista de facturas
                - Mensaje de error (si existe)
        """
        try:
            query = """
                SELECT id_factura 
                FROM facturas 
                WHERE id_cliente = %s 
                ORDER BY fecha_emision DESC
            """
            params = (cliente_id,)
            success, result, error = self.db.fetch_all(query, params)
            
            if not success:
                return False, [], error
            
            facturas = []
            for row in result:
                success, factura, error = self.get_invoice_by_id(row['id_factura'])
                if success and factura:
                    facturas.append(factura)
            
            return True, facturas, None
            
        except Exception as e:
            error_msg = f"Error al obtener facturas del cliente: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
    
    def get_all_invoices(self, limit: int = 100) -> Tuple[bool, List[Factura], Optional[str]]:
        """
        Obtiene todas las facturas.
        
        Args:
            limit (int): Límite de registros a retornar.
            
        Returns:
            Tuple[bool, List[Factura], Optional[str]]: (éxito, lista_facturas, error)
        """
        try:
            query = """
                SELECT id_factura 
                FROM facturas 
                ORDER BY fecha_emision DESC 
                LIMIT %s
            """
            params = (limit,)
            success, result, error = self.db.fetch_all(query, params)
            
            if not success:
                return False, [], error
            
            facturas = []
            for row in result:
                success, factura, error = self.get_invoice_by_id(row['id_factura'])
                if success and factura:
                    facturas.append(factura)
            
            return True, facturas, None
            
        except Exception as e:
            error_msg = f"Error al obtener facturas: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
    
    def update_invoice_status(self, factura_id: int, nuevo_estado: str) -> Tuple[bool, Optional[str]]:
        """
        Actualiza el estado de una factura.
        
        Args:
            factura_id (int): ID de la factura.
            nuevo_estado (str): Nuevo estado ('PENDIENTE', 'PAGADA', 'ANULADA', 'VENCIDA').
            
        Returns:
            Tuple[bool, Optional[str]]: (éxito, mensaje_error)
        """
        estados_validos = ['PENDIENTE', 'PAGADA', 'ANULADA', 'VENCIDA']
        if nuevo_estado not in estados_validos:
            return False, f"Estado inválido. Debe ser: {', '.join(estados_validos)}"
        
        try:
            # Verificar que la factura existe
            query_check = "SELECT id_factura, estado FROM facturas WHERE id_factura = %s"
            params_check = (factura_id,)
            success, result, error = self.db.fetch_one(query_check, params_check)
            
            if not success or not result:
                return False, "Factura no encontrada"
            
            if result['estado'] == 'ANULADA':
                return False, "No se puede actualizar una factura anulada"
            
            # Actualizar estado
            query_update = """
                UPDATE facturas 
                SET estado = %s 
                WHERE id_factura = %s
            """
            params_update = (nuevo_estado, factura_id)
            success, affected_rows, error = self.db.execute(query_update, params_update)
            
            if not success:
                return False, error
            
            logger.info(f"Factura {factura_id} actualizada a estado: {nuevo_estado}")
            return True, None
            
        except Exception as e:
            error_msg = f"Error al actualizar estado: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def anular_factura(self, factura_id: int, motivo: str = "") -> Tuple[bool, Optional[str]]:
        """
        Anula una factura y restaura el stock de los productos.
        
        Args:
            factura_id (int): ID de la factura.
            motivo (str): Motivo de la anulación.
            
        Returns:
            Tuple[bool, Optional[str]]: (éxito, mensaje_error)
        """
        connection = None
        cursor = None
        
        try:
            # Verificar que la factura existe y está pendiente
            query_check = "SELECT id_factura, estado FROM facturas WHERE id_factura = %s"
            params_check = (factura_id,)
            success, result, error = self.db.fetch_one(query_check, params_check)
            
            if not success or not result:
                return False, "Factura no encontrada"
            
            if result['estado'] != 'PENDIENTE':
                return False, f"Solo se pueden anular facturas en estado PENDIENTE. Estado actual: {result['estado']}"
            
            # Obtener conexión y transacción
            connection = self.db.get_connection()
            connection.start_transaction()
            cursor = connection.cursor()
            
            # Obtener detalles de la factura
            query_detalles = """
                SELECT id_producto, cantidad 
                FROM detalle_factura 
                WHERE id_factura = %s
            """
            cursor.execute(query_detalles, (factura_id,))
            detalles = cursor.fetchall()
            
            # Restaurar stock
            for detalle in detalles:
                query_stock = """
                    UPDATE productos 
                    SET stock = stock + %s 
                    WHERE id_producto = %s
                """
                cursor.execute(query_stock, (detalle['cantidad'], detalle['id_producto']))
                logger.debug(f"Stock restaurado para producto {detalle['id_producto']}")
            
            # Anular factura
            query_anular = """
                UPDATE facturas 
                SET estado = 'ANULADA', observaciones = CONCAT(observaciones, ' | ANULADA: ', %s)
                WHERE id_factura = %s
            """
            cursor.execute(query_anular, (motivo or 'Sin motivo especificado', factura_id))
            
            # Confirmar transacción
            connection.commit()
            
            logger.info(f"Factura {factura_id} anulada exitosamente")
            return True, None
            
        except Exception as e:
            if connection:
                connection.rollback()
            error_msg = f"Error al anular factura: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()


class ProductoService:
    """Servicio para gestión de productos."""
    
    def __init__(self):
        self.db = get_db_connection()
        logger.info("ProductoService inicializado")
    
    def get_all_products(self, incluir_inactivos: bool = False) -> Tuple[bool, List[Producto], Optional[str]]:
        """
        Obtiene todos los productos.
        
        Args:
            incluir_inactivos (bool): Si incluir productos inactivos.
            
        Returns:
            Tuple[bool, List[Producto], Optional[str]]: (éxito, lista_productos, error)
        """
        try:
            if incluir_inactivos:
                query = """
                    SELECT p.*, t.nombre as tipo_iva_nombre, t.porcentaje 
                    FROM productos p
                    INNER JOIN tipos_iva t ON p.id_tipo_iva = t.id_tipo_iva
                    ORDER BY p.nombre
                """
            else:
                query = """
                    SELECT p.*, t.nombre as tipo_iva_nombre, t.porcentaje 
                    FROM productos p
                    INNER JOIN tipos_iva t ON p.id_tipo_iva = t.id_tipo_iva
                    WHERE p.estado = 'ACTIVO'
                    ORDER BY p.nombre
                """
            
            success, result, error = self.db.fetch_all(query)
            
            if not success:
                return False, [], error
            
            productos = []
            for row in result:
                producto = Producto(
                    id_producto=row['id_producto'],
                    codigo=row['codigo'],
                    nombre=row['nombre'],
                    descripcion=row.get('descripcion', ''),
                    precio_unitario=Decimal(str(row['precio_unitario'])),
                    stock=row['stock'],
                    id_tipo_iva=row['id_tipo_iva'],
                    estado=row['estado']
                )
                productos.append(producto)
            
            return True, productos, None
            
        except Exception as e:
            error_msg = f"Error al obtener productos: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
    
    def get_product_by_id(self, producto_id: int) -> Tuple[bool, Optional[Producto], Optional[str]]:
        """
        Obtiene un producto por su ID.
        
        Args:
            producto_id (int): ID del producto.
            
        Returns:
            Tuple[bool, Optional[Producto], Optional[str]]: (éxito, producto, error)
        """
        try:
            query = """
                SELECT * FROM productos 
                WHERE id_producto = %s
            """
            params = (producto_id,)
            success, result, error = self.db.fetch_one(query, params)
            
            if not success or not result:
                return False, None, "Producto no encontrado"
            
            producto = Producto(
                id_producto=result['id_producto'],
                codigo=result['codigo'],
                nombre=result['nombre'],
                descripcion=result.get('descripcion', ''),
                precio_unitario=Decimal(str(result['precio_unitario'])),
                stock=result['stock'],
                id_tipo_iva=result['id_tipo_iva'],
                estado=result['estado']
            )
            
            return True, producto, None
            
        except Exception as e:
            error_msg = f"Error al obtener producto: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def get_product_by_codigo(self, codigo: str) -> Tuple[bool, Optional[Producto], Optional[str]]:
        """
        Obtiene un producto por su código.
        
        Args:
            codigo (str): Código del producto.
            
        Returns:
            Tuple[bool, Optional[Producto], Optional[str]]: (éxito, producto, error)
        """
        try:
            query = """
                SELECT * FROM productos 
                WHERE codigo = %s AND estado = 'ACTIVO'
            """
            params = (codigo,)
            success, result, error = self.db.fetch_one(query, params)
            
            if not success or not result:
                return False, None, "Producto no encontrado"
            
            producto = Producto(
                id_producto=result['id_producto'],
                codigo=result['codigo'],
                nombre=result['nombre'],
                descripcion=result.get('descripcion', ''),
                precio_unitario=Decimal(str(result['precio_unitario'])),
                stock=result['stock'],
                id_tipo_iva=result['id_tipo_iva'],
                estado=result['estado']
            )
            
            return True, producto, None
            
        except Exception as e:
            error_msg = f"Error al obtener producto: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg


class ClienteService:
    """Servicio para gestión de clientes."""
    
    def __init__(self):
        self.db = get_db_connection()
        logger.info("ClienteService inicializado")
    
    def get_all_clients(self, incluir_inactivos: bool = False) -> Tuple[bool, List[Cliente], Optional[str]]:
        """
        Obtiene todos los clientes.
        
        Args:
            incluir_inactivos (bool): Si incluir clientes inactivos.
            
        Returns:
            Tuple[bool, List[Cliente], Optional[str]]: (éxito, lista_clientes, error)
        """
        try:
            if incluir_inactivos:
                query = """
                    SELECT * FROM clientes 
                    ORDER BY nombre
                """
            else:
                query = """
                    SELECT * FROM clientes 
                    WHERE estado = 'ACTIVO'
                    ORDER BY nombre
                """
            
            success, result, error = self.db.fetch_all(query)
            
            if not success:
                return False, [], error
            
            clientes = []
            for row in result:
                cliente = Cliente(
                    id_cliente=row['id_cliente'],
                    identificacion=row['identificacion'],
                    nombre=row['nombre'],
                    direccion=row.get('direccion', ''),
                    telefono=row.get('telefono', ''),
                    email=row.get('email', ''),
                    estado=row['estado']
                )
                clientes.append(cliente)
            
            return True, clientes, None
            
        except Exception as e:
            error_msg = f"Error al obtener clientes: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
    
    def get_client_by_id(self, cliente_id: int) -> Tuple[bool, Optional[Cliente], Optional[str]]:
        """
        Obtiene un cliente por su ID.
        
        Args:
            cliente_id (int): ID del cliente.
            
        Returns:
            Tuple[bool, Optional[Cliente], Optional[str]]: (éxito, cliente, error)
        """
        try:
            query = """
                SELECT * FROM clientes 
                WHERE id_cliente = %s
            """
            params = (cliente_id,)
            success, result, error = self.db.fetch_one(query, params)
            
            if not success or not result:
                return False, None, "Cliente no encontrado"
            
            cliente = Cliente(
                id_cliente=result['id_cliente'],
                identificacion=result['identificacion'],
                nombre=result['nombre'],
                direccion=result.get('direccion', ''),
                telefono=result.get('telefono', ''),
                email=result.get('email', ''),
                estado=result['estado']
            )
            
            return True, cliente, None
            
        except Exception as e:
            error_msg = f"Error al obtener cliente: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def get_client_by_identificacion(self, identificacion: str) -> Tuple[bool, Optional[Cliente], Optional[str]]:
        """
        Obtiene un cliente por su identificación.
        
        Args:
            identificacion (str): Identificación del cliente.
            
        Returns:
            Tuple[bool, Optional[Cliente], Optional[str]]: (éxito, cliente, error)
        """
        try:
            query = """
                SELECT * FROM clientes 
                WHERE identificacion = %s AND estado = 'ACTIVO'
            """
            params = (identificacion,)
            success, result, error = self.db.fetch_one(query, params)
            
            if not success or not result:
                return False, None, "Cliente no encontrado"
            
            cliente = Cliente(
                id_cliente=result['id_cliente'],
                identificacion=result['identificacion'],
                nombre=result['nombre'],
                direccion=result.get('direccion', ''),
                telefono=result.get('telefono', ''),
                email=result.get('email', ''),
                estado=result['estado']
            )
            
            return True, cliente, None
            
        except Exception as e:
            error_msg = f"Error al obtener cliente: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg


# Función de utilidad para probar servicios
def test_services():
    """
    Función de prueba para verificar que los servicios funcionan.
    """
    print("\n=== Probando Servicios ===\n")
    
    # Probar ProductoService
    print("1. Probando ProductoService...")
    producto_service = ProductoService()
    success, productos, error = producto_service.get_all_products()
    if success:
        print(f"   ✅ Productos obtenidos: {len(productos)}")
        if productos:
            print(f"   Primer producto: {productos[0].nombre} - ${productos[0].precio_unitario}")
    else:
        print(f"   ❌ Error: {error}")
    
    # Probar ClienteService
    print("\n2. Probando ClienteService...")
    cliente_service = ClienteService()
    success, clientes, error = cliente_service.get_all_clients()
    if success:
        print(f"   ✅ Clientes obtenidos: {len(clientes)}")
        if clientes:
            print(f"   Primer cliente: {clientes[0].nombre}")
    else:
        print(f"   ❌ Error: {error}")
    
    print("\n=== Prueba completada ===\n")


if __name__ == "__main__":
    # Configurar logging básico
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    test_services()