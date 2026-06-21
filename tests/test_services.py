"""
Módulo: test_services.py
Descripción: Pruebas unitarias para los servicios de negocio.
"""

import pytest
from decimal import Decimal
from datetime import date
import os
import sys

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.services import InvoiceService, ProductoService, ClienteService
    from src.models import Factura, DetalleFactura, Cliente, Producto
    from src.database import get_db_connection
except ImportError:
    from services import InvoiceService, ProductoService, ClienteService
    from models import Factura, DetalleFactura, Cliente, Producto
    from database import get_db_connection


class TestInvoiceService:
    """Pruebas para el servicio de facturación."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuración antes de cada prueba."""
        self.db = get_db_connection()
        self.invoice_service = InvoiceService()
        self.producto_service = ProductoService()
        self.cliente_service = ClienteService()
        
        # Crear datos de prueba únicos
        self.test_cliente_id = self._create_test_cliente()
        self.test_producto_ids = self._create_test_productos()
        yield
        self._cleanup_test_data()
    
    def _create_test_cliente(self) -> int:
        """Crea un cliente de prueba y retorna su ID."""
        query = """
            INSERT INTO clientes (identificacion, nombre, direccion, telefono, email) 
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            f"TEST-{os.urandom(4).hex().upper()}", 
            'Cliente Test Services', 
            'Dirección Test', 
            '0999999999',
            'test@services.com'
        )
        success, last_id, error = self.db.execute_insert(query, params)
        if not success:
            pytest.skip(f"No se pudo crear cliente de prueba: {error}")
        return last_id
    
    def _create_test_productos(self) -> list:
        """Crea productos de prueba y retorna sus IDs."""
        productos = []
        productos_data = [
            {'codigo': f'TEST-PROD-{os.urandom(4).hex().upper()}', 'nombre': 'Producto Test 1', 
             'precio': 100.00, 'stock': 50},
            {'codigo': f'TEST-PROD-{os.urandom(4).hex().upper()}', 'nombre': 'Producto Test 2', 
             'precio': 50.00, 'stock': 30},
            {'codigo': f'TEST-PROD-{os.urandom(4).hex().upper()}', 'nombre': 'Producto Test 3', 
             'precio': 25.00, 'stock': 10}
        ]
        
        for prod_data in productos_data:
            query = """
                INSERT INTO productos (codigo, nombre, precio_unitario, id_tipo_iva, stock) 
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (prod_data['codigo'], prod_data['nombre'], prod_data['precio'], 1, prod_data['stock'])
            success, last_id, error = self.db.execute_insert(query, params)
            if success:
                productos.append(last_id)
        
        if len(productos) < 2:
            pytest.skip("No se pudieron crear suficientes productos de prueba")
        
        return productos
    
    def _cleanup_test_data(self):
        """Limpia los datos de prueba después de cada test."""
        try:
            # Limpiar facturas de prueba
            query = "DELETE FROM facturas WHERE id_cliente = %s"
            self.db.execute(query, (self.test_cliente_id,))
            
            # Limpiar productos de prueba
            for prod_id in self.test_producto_ids:
                query = "DELETE FROM productos WHERE id_producto = %s"
                self.db.execute(query, (prod_id,))
            
            # Limpiar cliente de prueba
            query = "DELETE FROM clientes WHERE id_cliente = %s"
            self.db.execute(query, (self.test_cliente_id,))
            
        except Exception as e:
            print(f"Warning: No se pudo limpiar datos de prueba: {e}")
    
    def test_generar_numero_factura(self):
        """Prueba la generación de números de factura."""
        numero = self.invoice_service._generar_numero_factura()
        
        # Verificar formato
        assert numero.startswith("FAC-")
        assert len(numero) >= 14  # FAC-YYYY-XXXXX
        
        # Verificar que el año es el actual
        year = date.today().year
        assert f"FAC-{year}" in numero
        
        # Verificar que el número es secuencial
        numero2 = self.invoice_service._generar_numero_factura()
        assert int(numero.split('-')[-1]) < int(numero2.split('-')[-1])
    
    def test_validar_factura_exitosa(self):
        """Prueba la validación de una factura correcta."""
        # Crear factura de prueba
        factura = Factura(
            id_cliente=self.test_cliente_id,
            numero_factura="FAC-2026-00001"
        )
        factura.agregar_detalle(DetalleFactura(
            id_producto=self.test_producto_ids[0],
            cantidad=2,
            precio_unitario=Decimal('100.00')
        ))
        
        valido, error = self.invoice_service._validar_factura(factura)
        assert valido == True
        assert error is None
    
    def test_validar_factura_sin_detalles(self):
        """Prueba la validación de una factura sin detalles."""
        factura = Factura(
            id_cliente=self.test_cliente_id,
            numero_factura="FAC-2026-00001"
        )
        
        valido, error = self.invoice_service._validar_factura(factura)
        assert valido == False
        assert "al menos un detalle" in error
    
    def test_validar_factura_cantidad_cero(self):
        """Prueba la validación de una factura con cantidad cero."""
        factura = Factura(
            id_cliente=self.test_cliente_id,
            numero_factura="FAC-2026-00001"
        )
        factura.agregar_detalle(DetalleFactura(
            id_producto=self.test_producto_ids[0],
            cantidad=0,
            precio_unitario=Decimal('100.00')
        ))
        
        valido, error = self.invoice_service._validar_factura(factura)
        assert valido == False
        assert "cantidad" in error.lower()
    
    def test_validar_factura_precio_cero(self):
        """Prueba la validación de una factura con precio cero."""
        factura = Factura(
            id_cliente=self.test_cliente_id,
            numero_factura="FAC-2026-00001"
        )
        factura.agregar_detalle(DetalleFactura(
            id_producto=self.test_producto_ids[0],
            cantidad=2,
            precio_unitario=Decimal('0.00')
        ))
        
        valido, error = self.invoice_service._validar_factura(factura)
        assert valido == False
        assert "precio" in error.lower()
    
    def test_validar_factura_cliente_inactivo(self):
        """Prueba la validación de una factura con cliente inactivo."""
        # Crear cliente inactivo
        query = """
            INSERT INTO clientes (identificacion, nombre, estado) 
            VALUES (%s, %s, 'INACTIVO')
        """
        params = (f"TEST-INACTIVO-{os.urandom(4).hex().upper()}", 'Cliente Inactivo')
        success, cliente_id, error = self.db.execute_insert(query, params)
        
        if not success:
            pytest.skip("No se pudo crear cliente inactivo")
        
        factura = Factura(
            id_cliente=cliente_id,
            numero_factura="FAC-2026-00001"
        )
        factura.agregar_detalle(DetalleFactura(
            id_producto=self.test_producto_ids[0],
            cantidad=2,
            precio_unitario=Decimal('100.00')
        ))
        
        valido, error = self.invoice_service._validar_factura(factura)
        assert valido == False
        assert "inactivo" in error.lower() or "no existe" in error.lower()
        
        # Limpiar
        self.db.execute("DELETE FROM clientes WHERE id_cliente = %s", (cliente_id,))
    
    def test_validar_factura_producto_inexistente(self):
        """Prueba la validación de una factura con producto inexistente."""
        factura = Factura(
            id_cliente=self.test_cliente_id,
            numero_factura="FAC-2026-00001"
        )
        factura.agregar_detalle(DetalleFactura(
            id_producto=99999,  # Producto inexistente
            cantidad=2,
            precio_unitario=Decimal('100.00')
        ))
        
        valido, error = self.invoice_service._validar_factura(factura)
        assert valido == False
        assert "producto" in error.lower()
    
    def test_create_invoice_exitosa(self):
        """Prueba la creación exitosa de una factura."""
        items_list = [
            {'id_producto': self.test_producto_ids[0], 'cantidad': 2, 'precio_unitario': 100.00},
            {'id_producto': self.test_producto_ids[1], 'cantidad': 1, 'precio_unitario': 50.00}
        ]
        
        success, factura, error = self.invoice_service.create_invoice(
            cliente_id=self.test_cliente_id,
            items_list=items_list,
            observaciones="Factura de prueba"
        )
        
        assert success == True
        assert error is None
        assert factura is not None
        assert factura.id_factura is not None
        assert factura.numero_factura.startswith("FAC-")
        assert factura.estado == "PENDIENTE"
        assert len(factura.detalles) == 2
        
        # Verificar totales
        assert factura.subtotal == Decimal('250.00')
        assert factura.total == Decimal('280.00')  # 250 + 12% IVA
    
    def test_create_invoice_con_descuentos(self):
        """Prueba la creación de una factura con descuentos."""
        items_list = [
            {'id_producto': self.test_producto_ids[0], 'cantidad': 2, 
             'precio_unitario': 100.00, 'descuento': 20.00},
            {'id_producto': self.test_producto_ids[1], 'cantidad': 1, 
             'precio_unitario': 50.00, 'descuento': 5.00}
        ]
        
        success, factura, error = self.invoice_service.create_invoice(
            cliente_id=self.test_cliente_id,
            items_list=items_list,
            observaciones="Factura con descuentos"
        )
        
        assert success == True
        assert error is None
        assert factura is not None
        
        # Verificar que los descuentos se aplicaron
        assert factura.detalles[0].descuento == Decimal('20.00')
        assert factura.detalles[1].descuento == Decimal('5.00')
    
    def test_create_invoice_cliente_inexistente(self):
        """Prueba la creación de factura con cliente inexistente."""
        items_list = [
            {'id_producto': self.test_producto_ids[0], 'cantidad': 2, 'precio_unitario': 100.00}
        ]
        
        success, factura, error = self.invoice_service.create_invoice(
            cliente_id=99999,  # Cliente inexistente
            items_list=items_list
        )
        
        assert success == False
        assert factura is None
        assert error is not None
        assert "cliente" in error.lower()
    
    def test_create_invoice_producto_inexistente(self):
        """Prueba la creación de factura con producto inexistente."""
        items_list = [
            {'id_producto': 99999, 'cantidad': 2, 'precio_unitario': 100.00}
        ]
        
        success, factura, error = self.invoice_service.create_invoice(
            cliente_id=self.test_cliente_id,
            items_list=items_list
        )
        
        assert success == False
        assert factura is None
        assert error is not None
        assert "producto" in error.lower()
    
    def test_create_invoice_stock_insuficiente(self):
        """Prueba la creación de factura con stock insuficiente."""
        # Usar un producto con stock limitado
        items_list = [
            {'id_producto': self.test_producto_ids[2], 'cantidad': 100, 'precio_unitario': 100.00}
        ]
        
        success, factura, error = self.invoice_service.create_invoice(
            cliente_id=self.test_cliente_id,
            items_list=items_list
        )
        
        assert success == False
        assert factura is None
        assert error is not None
        assert "stock" in error.lower()
    
    def test_create_invoice_atomicidad(self):
        """Prueba que la creación de factura es atómica."""
        # Lista con un producto válido y otro inválido
        items_list = [
            {'id_producto': self.test_producto_ids[0], 'cantidad': 2, 'precio_unitario': 100.00},
            {'id_producto': 99999, 'cantidad': 1, 'precio_unitario': 50.00}  # Producto inválido
        ]
        
        # Verificar stock antes
        query = "SELECT stock FROM productos WHERE id_producto = %s"
        success, result, error = self.db.fetch_one(query, (self.test_producto_ids[0],))
        stock_before = result['stock'] if result else 0
        
        # Intentar crear factura (debe fallar)
        success, factura, error = self.invoice_service.create_invoice(
            cliente_id=self.test_cliente_id,
            items_list=items_list
        )
        
        assert success == False
        assert factura is None
        
        # Verificar que el stock no cambió (rollback)
        success, result, error = self.db.fetch_one(query, (self.test_producto_ids[0],))
        stock_after = result['stock'] if result else 0
        assert stock_before == stock_after
    
    def test_get_invoice_by_id(self):
        """Prueba la obtención de una factura por ID."""
        # Primero crear una factura
        items_list = [
            {'id_producto': self.test_producto_ids[0], 'cantidad': 1, 'precio_unitario': 100.00}
        ]
        success, factura_creada, error = self.invoice_service.create_invoice(
            cliente_id=self.test_cliente_id,
            items_list=items_list
        )
        assert success == True
        
        # Obtener la factura
        success, factura_obtenida, error = self.invoice_service.get_invoice_by_id(
            factura_creada.id_factura
        )
        
        assert success == True
        assert factura_obtenida is not None
        assert factura_obtenida.id_factura == factura_creada.id_factura
        assert factura_obtenida.numero_factura == factura_creada.numero_factura
        assert len(factura_obtenida.detalles) > 0
    
    def test_get_invoice_by_id_no_existe(self):
        """Prueba la obtención de una factura que no existe."""
        success, factura, error = self.invoice_service.get_invoice_by_id(99999)
        assert success == False
        assert factura is None
        assert error is not None
        assert "no encontrada" in error.lower()
    
    def test_update_invoice_status(self):
        """Prueba la actualización del estado de una factura."""
        # Primero crear una factura
        items_list = [
            {'id_producto': self.test_producto_ids[0], 'cantidad': 1, 'precio_unitario': 100.00}
        ]
        success, factura, error = self.invoice_service.create_invoice(
            cliente_id=self.test_cliente_id,
            items_list=items_list
        )
        assert success == True
        
        # Actualizar estado
        success, error = self.invoice_service.update_invoice_status(
            factura.id_factura,
            'PAGADA'
        )
        
        assert success == True
        assert error is None
        
        # Verificar el nuevo estado
        success, factura_actualizada, error = self.invoice_service.get_invoice_by_id(
            factura.id_factura
        )
        assert success == True
        assert factura_actualizada.estado == 'PAGADA'
    
    def test_update_invoice_status_invalido(self):
        """Prueba la actualización de estado con estado inválido."""
        success, error = self.invoice_service.update_invoice_status(
            1,
            'ESTADO_INVALIDO'
        )
        
        assert success == False
        assert error is not None
        assert "inválido" in error.lower()
    
    def test_anular_factura(self):
        """Prueba la anulación de una factura."""
        # Crear una factura
        items_list = [
            {'id_producto': self.test_producto_ids[0], 'cantidad': 2, 'precio_unitario': 100.00}
        ]
        success, factura, error = self.invoice_service.create_invoice(
            cliente_id=self.test_cliente_id,
            items_list=items_list
        )
        assert success == True
        
        # Obtener stock antes de la anulación
        query = "SELECT stock FROM productos WHERE id_producto = %s"
        success, result, error = self.db.fetch_one(query, (self.test_producto_ids[0],))
        stock_antes = result['stock'] if result else 0
        
        # Anular factura
        success, error = self.invoice_service.anular_factura(
            factura.id_factura,
            "Prueba de anulación"
        )
        
        assert success == True
        assert error is None
        
        # Verificar que el stock se restauró
        success, result, error = self.db.fetch_one(query, (self.test_producto_ids[0],))
        stock_despues = result['stock'] if result else 0
        assert stock_despues == stock_antes + 2  # Se agregó el stock
    
    def test_anular_factura_no_pendiente(self):
        """Prueba la anulación de una factura que no está pendiente."""
        # Crear una factura
        items_list = [
            {'id_producto': self.test_producto_ids[0], 'cantidad': 1, 'precio_unitario': 100.00}
        ]
        success, factura, error = self.invoice_service.create_invoice(
            cliente_id=self.test_cliente_id,
            items_list=items_list
        )
        assert success == True
        
        # Cambiar estado a PAGADA
        self.invoice_service.update_invoice_status(factura.id_factura, 'PAGADA')
        
        # Intentar anular (debe fallar)
        success, error = self.invoice_service.anular_factura(
            factura.id_factura,
            "Intento de anulación"
        )
        
        assert success == False
        assert error is not None
        assert "pendiente" in error.lower()
    
    def test_get_invoices_by_client(self):
        """Prueba la obtención de facturas por cliente."""
        # Crear algunas facturas
        for i in range(3):
            items_list = [
                {'id_producto': self.test_producto_ids[0], 'cantidad': 1, 'precio_unitario': 100.00}
            ]
            self.invoice_service.create_invoice(
                cliente_id=self.test_cliente_id,
                items_list=items_list
            )
        
        success, facturas, error = self.invoice_service.get_invoices_by_client(
            self.test_cliente_id
        )
        
        assert success == True
        assert error is None
        assert len(facturas) >= 3


class TestProductoService:
    """Pruebas para el servicio de productos."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuración antes de cada prueba."""
        self.db = get_db_connection()
        self.producto_service = ProductoService()
        
        # Crear productos de prueba
        self.test_productos_ids = []
        for i in range(3):
            query = """
                INSERT INTO productos (codigo, nombre, precio_unitario, id_tipo_iva, stock) 
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (
                f"TEST-SERV-{os.urandom(4).hex().upper()}", 
                f'Producto Servicio {i}', 
                100.00 + i * 10, 
                1, 
                10 + i * 5
            )
            success, last_id, error = self.db.execute_insert(query, params)
            if success:
                self.test_productos_ids.append(last_id)
        
        yield
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Limpia los datos de prueba."""
        try:
            for prod_id in self.test_productos_ids:
                self.db.execute("DELETE FROM productos WHERE id_producto = %s", (prod_id,))
        except Exception as e:
            print(f"Warning: No se pudo limpiar datos: {e}")
    
    def test_get_all_products(self):
        """Prueba la obtención de todos los productos."""
        success, productos, error = self.producto_service.get_all_products()
        assert success == True
        assert error is None
        assert len(productos) > 0
        
        # Verificar que los productos tienen los atributos correctos
        if productos:
            producto = productos[0]
            assert hasattr(producto, 'id_producto')
            assert hasattr(producto, 'codigo')
            assert hasattr(producto, 'nombre')
            assert hasattr(producto, 'precio_unitario')
            assert hasattr(producto, 'stock')
    
    def test_get_product_by_id(self):
        """Prueba la obtención de un producto por ID."""
        if not self.test_productos_ids:
            pytest.skip("No hay productos de prueba")
        
        success, producto, error = self.producto_service.get_product_by_id(
            self.test_productos_ids[0]
        )
        assert success == True
        assert error is None
        assert producto is not None
        assert producto.id_producto == self.test_productos_ids[0]
    
    def test_get_product_by_id_no_existe(self):
        """Prueba la obtención de un producto que no existe."""
        success, producto, error = self.producto_service.get_product_by_id(99999)
        assert success == False
        assert producto is None
        assert error is not None
        assert "no encontrado" in error.lower()
    
    def test_get_product_by_codigo(self):
        """Prueba la obtención de un producto por código."""
        if not self.test_productos_ids:
            pytest.skip("No hay productos de prueba")
        
        # Obtener el código del producto
        query = "SELECT codigo FROM productos WHERE id_producto = %s"
        success, result, error = self.db.fetch_one(query, (self.test_productos_ids[0],))
        if not result:
            pytest.skip("No se pudo obtener código del producto")
        
        success, producto, error = self.producto_service.get_product_by_codigo(
            result['codigo']
        )
        assert success == True
        assert error is None
        assert producto is not None
        assert producto.codigo == result['codigo']


class TestClienteService:
    """Pruebas para el servicio de clientes."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuración antes de cada prueba."""
        self.db = get_db_connection()
        self.cliente_service = ClienteService()
        
        # Crear clientes de prueba
        self.test_clientes_ids = []
        for i in range(3):
            query = """
                INSERT INTO clientes (identificacion, nombre, direccion, telefono, email) 
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (
                f"TEST-SERV-{os.urandom(4).hex().upper()}", 
                f'Cliente Servicio {i}', 
                f'Dirección {i}', 
                f'099999999{i}', 
                f'cliente{i}@test.com'
            )
            success, last_id, error = self.db.execute_insert(query, params)
            if success:
                self.test_clientes_ids.append(last_id)
        
        yield
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Limpia los datos de prueba."""
        try:
            for cliente_id in self.test_clientes_ids:
                self.db.execute("DELETE FROM clientes WHERE id_cliente = %s", (cliente_id,))
        except Exception as e:
            print(f"Warning: No se pudo limpiar datos: {e}")
    
    def test_get_all_clients(self):
        """Prueba la obtención de todos los clientes."""
        success, clientes, error = self.cliente_service.get_all_clients()
        assert success == True
        assert error is None
        assert len(clientes) > 0
        
        # Verificar que los clientes tienen los atributos correctos
        if clientes:
            cliente = clientes[0]
            assert hasattr(cliente, 'id_cliente')
            assert hasattr(cliente, 'identificacion')
            assert hasattr(cliente, 'nombre')
            assert hasattr(cliente, 'direccion')
            assert hasattr(cliente, 'telefono')
            assert hasattr(cliente, 'email')
    
    def test_get_client_by_id(self):
        """Prueba la obtención de un cliente por ID."""
        if not self.test_clientes_ids:
            pytest.skip("No hay clientes de prueba")
        
        success, cliente, error = self.cliente_service.get_client_by_id(
            self.test_clientes_ids[0]
        )
        assert success == True
        assert error is None
        assert cliente is not None
        assert cliente.id_cliente == self.test_clientes_ids[0]
    
    def test_get_client_by_id_no_existe(self):
        """Prueba la obtención de un cliente que no existe."""
        success, cliente, error = self.cliente_service.get_client_by_id(99999)
        assert success == False
        assert cliente is None
        assert error is not None
        assert "no encontrado" in error.lower()
    
    def test_get_client_by_identificacion(self):
        """Prueba la obtención de un cliente por identificación."""
        if not self.test_clientes_ids:
            pytest.skip("No hay clientes de prueba")
        
        # Obtener la identificación del cliente
        query = "SELECT identificacion FROM clientes WHERE id_cliente = %s"
        success, result, error = self.db.fetch_one(query, (self.test_clientes_ids[0],))
        if not result:
            pytest.skip("No se pudo obtener identificación del cliente")
        
        success, cliente, error = self.cliente_service.get_client_by_identificacion(
            result['identificacion']
        )
        assert success == True
        assert error is None
        assert cliente is not None
        assert cliente.identificacion == result['identificacion']


# Configuración para ejecutar pruebas
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=1"])