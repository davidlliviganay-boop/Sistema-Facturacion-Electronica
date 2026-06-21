"""
Módulo: test_api.py
Descripción: Pruebas de la API REST usando FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
import os
import sys
import json
from typing import Dict, Any

# Configurar path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.main import app
    from src.database import get_db_connection
    from src.services import InvoiceService, ProductoService, ClienteService
except ImportError:
    from main import app
    from database import get_db_connection
    from services import InvoiceService, ProductoService, ClienteService

client = TestClient(app)


class TestAPI:
    """Pruebas de la API REST."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuración antes de cada prueba."""
        self.db = get_db_connection()
        self.test_data = {
            'cliente_id': None,
            'producto_ids': [],
            'factura_id': None
        }
        
        # Crear datos de prueba
        self._create_test_data()
        yield
        self._cleanup_test_data()
    
    def _create_test_data(self):
        """Crea datos de prueba necesarios."""
        try:
            # 1. Crear cliente de prueba
            query = """
                INSERT INTO clientes (identificacion, nombre, direccion, telefono, email) 
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (
                f"TEST-API-{os.urandom(4).hex().upper()}",
                'Cliente Test API',
                'Dirección Test API',
                '0999999999',
                'test_api@example.com'
            )
            success, cliente_id, error = self.db.execute_insert(query, params)
            if success:
                self.test_data['cliente_id'] = cliente_id
                print(f"✅ Cliente de prueba creado: {cliente_id}")
            
            # 2. Crear productos de prueba
            productos = [
                ('TEST-API-001', 'Producto API 1', 100.00, 50),
                ('TEST-API-002', 'Producto API 2', 75.00, 30),
                ('TEST-API-003', 'Producto API 3', 50.00, 10)
            ]
            
            for codigo, nombre, precio, stock in productos:
                query = """
                    INSERT INTO productos (codigo, nombre, precio_unitario, id_tipo_iva, stock) 
                    VALUES (%s, %s, %s, %s, %s)
                """
                params = (codigo, nombre, precio, 1, stock)
                success, prod_id, error = self.db.execute_insert(query, params)
                if success:
                    self.test_data['producto_ids'].append(prod_id)
                    print(f"✅ Producto de prueba creado: {prod_id}")
            
        except Exception as e:
            print(f"⚠️ Error al crear datos de prueba: {e}")
    
    def _cleanup_test_data(self):
        """Limpia los datos de prueba."""
        try:
            # Limpiar factura de prueba
            if self.test_data['factura_id']:
                query = "DELETE FROM facturas WHERE id_factura = %s"
                self.db.execute(query, (self.test_data['factura_id'],))
            
            # Limpiar productos de prueba
            for prod_id in self.test_data['producto_ids']:
                query = "DELETE FROM productos WHERE id_producto = %s"
                self.db.execute(query, (prod_id,))
            
            # Limpiar cliente de prueba
            if self.test_data['cliente_id']:
                query = "DELETE FROM clientes WHERE id_cliente = %s"
                self.db.execute(query, (self.test_data['cliente_id'],))
                
        except Exception as e:
            print(f"⚠️ Error al limpiar datos: {e}")
    
    def _create_test_factura(self, cliente_id: int = None) -> int:
        """Crea una factura de prueba y retorna su ID."""
        if not cliente_id:
            cliente_id = self.test_data['cliente_id']
        
        if not cliente_id or not self.test_data['producto_ids']:
            pytest.skip("No hay datos de prueba disponibles")
        
        factura_data = {
            "id_cliente": cliente_id,
            "items": [
                {
                    "id_producto": self.test_data['producto_ids'][0],
                    "cantidad": 2,
                    "precio_unitario": 100.00
                }
            ],
            "observaciones": "Factura de prueba API"
        }
        
        response = client.post("/api/v1/facturas", json=factura_data)
        if response.status_code != 201:
            pytest.skip(f"No se pudo crear factura: {response.text}")
        
        factura_id = response.json()["id_factura"]
        self.test_data['factura_id'] = factura_id
        return factura_id
    
    # ========== PRUEBAS DE SISTEMA ==========
    
    def test_root(self):
        """Prueba la ruta raíz."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Sistema de Facturación Electrónica API" in data["message"]
        assert "version" in data
        assert "docs" in data
    
    def test_health_check(self):
        """Prueba el endpoint de salud."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_api_info(self):
        """Prueba la información de la API."""
        response = client.get("/api/v1")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data
        assert "clientes" in data["endpoints"]
        assert "productos" in data["endpoints"]
        assert "facturas" in data["endpoints"]
    
    # ========== PRUEBAS DE CORS ==========
    
    def test_cors_headers(self):
        """Prueba que CORS esté configurado correctamente."""
        response = client.options(
            "/api/v1/clientes",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
    
    # ========== PRUEBAS DE CLIENTES ==========
    
    def test_get_clientes(self):
        """Prueba obtener todos los clientes."""
        response = client.get("/api/v1/clientes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verificar estructura de datos
        if data:
            cliente = data[0]
            assert "id_cliente" in cliente
            assert "identificacion" in cliente
            assert "nombre" in cliente
            assert "estado" in cliente
    
    def test_get_clientes_with_inactivos(self):
        """Prueba obtener todos los clientes incluyendo inactivos."""
        response = client.get("/api/v1/clientes?incluir_inactivos=true")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_cliente_by_id(self):
        """Prueba obtener un cliente por ID."""
        if not self.test_data['cliente_id']:
            pytest.skip("No hay cliente de prueba")
        
        response = client.get(f"/api/v1/clientes/{self.test_data['cliente_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id_cliente"] == self.test_data['cliente_id']
        assert "nombre" in data
        assert "identificacion" in data
    
    def test_get_cliente_not_found(self):
        """Prueba obtener un cliente inexistente."""
        response = client.get("/api/v1/clientes/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    # ========== PRUEBAS DE PRODUCTOS ==========
    
    def test_get_productos(self):
        """Prueba obtener todos los productos."""
        response = client.get("/api/v1/productos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verificar estructura de datos
        if data:
            producto = data[0]
            assert "id_producto" in producto
            assert "codigo" in producto
            assert "nombre" in producto
            assert "precio_unitario" in producto
            assert "stock" in producto
    
    def test_get_productos_with_inactivos(self):
        """Prueba obtener todos los productos incluyendo inactivos."""
        response = client.get("/api/v1/productos?incluir_inactivos=true")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_producto_by_id(self):
        """Prueba obtener un producto por ID."""
        if not self.test_data['producto_ids']:
            pytest.skip("No hay productos de prueba")
        
        producto_id = self.test_data['producto_ids'][0]
        response = client.get(f"/api/v1/productos/{producto_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id_producto"] == producto_id
        assert "nombre" in data
        assert "codigo" in data
    
    def test_get_producto_not_found(self):
        """Prueba obtener un producto inexistente."""
        response = client.get("/api/v1/productos/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    # ========== PRUEBAS DE FACTURAS ==========
    
    def test_create_factura(self):
        """Prueba crear una factura."""
        if not self.test_data['cliente_id'] or not self.test_data['producto_ids']:
            pytest.skip("No hay datos de prueba")
        
        factura_data = {
            "id_cliente": self.test_data['cliente_id'],
            "items": [
                {
                    "id_producto": self.test_data['producto_ids'][0],
                    "cantidad": 2,
                    "precio_unitario": 100.00
                },
                {
                    "id_producto": self.test_data['producto_ids'][1],
                    "cantidad": 1,
                    "precio_unitario": 75.00
                }
            ],
            "observaciones": "Factura de prueba desde API"
        }
        
        response = client.post("/api/v1/facturas", json=factura_data)
        assert response.status_code == 201
        data = response.json()
        
        # Verificar estructura de respuesta
        assert "id_factura" in data
        assert data["id_factura"] is not None
        assert "numero_factura" in data
        assert data["numero_factura"].startswith("FAC-")
        assert data["estado"] == "PENDIENTE"
        assert "subtotal" in data
        assert "iva" in data
        assert "total" in data
        assert "detalles" in data
        assert len(data["detalles"]) == 2
        
        # Guardar ID para limpieza
        self.test_data['factura_id'] = data["id_factura"]
    
    def test_create_factura_with_descuentos(self):
        """Prueba crear una factura con descuentos."""
        if not self.test_data['cliente_id'] or not self.test_data['producto_ids']:
            pytest.skip("No hay datos de prueba")
        
        factura_data = {
            "id_cliente": self.test_data['cliente_id'],
            "items": [
                {
                    "id_producto": self.test_data['producto_ids'][0],
                    "cantidad": 2,
                    "precio_unitario": 100.00,
                    "descuento": 20.00
                }
            ],
            "observaciones": "Factura con descuento"
        }
        
        response = client.post("/api/v1/facturas", json=factura_data)
        assert response.status_code == 201
        data = response.json()
        
        # Verificar descuento
        if data["detalles"]:
            assert data["detalles"][0]["descuento"] == 20.00
    
    def test_create_factura_invalid_cliente(self):
        """Prueba crear una factura con cliente inexistente."""
        if not self.test_data['producto_ids']:
            pytest.skip("No hay productos de prueba")
        
        factura_data = {
            "id_cliente": 99999,
            "items": [
                {
                    "id_producto": self.test_data['producto_ids'][0],
                    "cantidad": 1,
                    "precio_unitario": 100.00
                }
            ]
        }
        
        response = client.post("/api/v1/facturas", json=factura_data)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "cliente" in data["detail"].lower()
    
    def test_create_factura_invalid_producto(self):
        """Prueba crear una factura con producto inexistente."""
        if not self.test_data['cliente_id']:
            pytest.skip("No hay cliente de prueba")
        
        factura_data = {
            "id_cliente": self.test_data['cliente_id'],
            "items": [
                {
                    "id_producto": 99999,
                    "cantidad": 1,
                    "precio_unitario": 100.00
                }
            ]
        }
        
        response = client.post("/api/v1/facturas", json=factura_data)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "producto" in data["detail"].lower()
    
    def test_create_factura_sin_items(self):
        """Prueba crear una factura sin items (debe fallar)."""
        if not self.test_data['cliente_id']:
            pytest.skip("No hay cliente de prueba")
        
        factura_data = {
            "id_cliente": self.test_data['cliente_id'],
            "items": []
        }
        
        response = client.post("/api/v1/facturas", json=factura_data)
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data
    
    def test_get_factura_by_id(self):
        """Prueba obtener una factura por ID."""
        # Crear factura de prueba
        factura_id = self._create_test_factura()
        
        response = client.get(f"/api/v1/facturas/{factura_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["id_factura"] == factura_id
        assert "numero_factura" in data
        assert "cliente" in data
        assert "detalles" in data
        assert len(data["detalles"]) > 0
    
    def test_get_factura_not_found(self):
        """Prueba obtener una factura inexistente."""
        response = client.get("/api/v1/facturas/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_update_factura_estado(self):
        """Prueba actualizar el estado de una factura."""
        # Crear factura de prueba
        factura_id = self._create_test_factura()
        
        # Actualizar estado
        response = client.put(
            f"/api/v1/facturas/{factura_id}/estado?estado=PAGADA"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "PAGADA" in data["message"]
        
        # Verificar que se actualizó
        response = client.get(f"/api/v1/facturas/{factura_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "PAGADA"
    
    def test_update_factura_estado_invalido(self):
        """Prueba actualizar a un estado inválido."""
        factura_id = self._create_test_factura()
        
        response = client.put(
            f"/api/v1/facturas/{factura_id}/estado?estado=INVALIDO"
        )
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_anular_factura(self):
        """Prueba anular una factura."""
        # Crear factura de prueba
        factura_id = self._create_test_factura()
        
        # Verificar stock antes
        producto_id = self.test_data['producto_ids'][0]
        query = "SELECT stock FROM productos WHERE id_producto = %s"
        success, result, error = self.db.fetch_one(query, (producto_id,))
        stock_antes = result['stock'] if result else 0
        
        # Anular factura
        response = client.post(
            f"/api/v1/facturas/{factura_id}/anular?motivo=Prueba de anulación"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "anulada" in data["message"]
        
        # Verificar que el estado cambió
        response = client.get(f"/api/v1/facturas/{factura_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "ANULADA"
        
        # Verificar que el stock se restauró
        success, result, error = self.db.fetch_one(query, (producto_id,))
        stock_despues = result['stock'] if result else 0
        assert stock_despues == stock_antes + 2  # Se agregaron 2 unidades
    
    def test_get_facturas_cliente(self):
        """Prueba obtener facturas de un cliente."""
        if not self.test_data['cliente_id']:
            pytest.skip("No hay cliente de prueba")
        
        # Crear algunas facturas
        for _ in range(3):
            self._create_test_factura(self.test_data['cliente_id'])
        
        response = client.get(f"/api/v1/clientes/{self.test_data['cliente_id']}/facturas")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verificar que todas las facturas son del cliente
        for factura in data:
            assert factura["id_cliente"] == self.test_data['cliente_id']
    
    def test_buscar_facturas(self):
        """Prueba buscar facturas con filtros."""
        # Crear facturas de prueba
        for _ in range(3):
            self._create_test_factura()
        
        # Buscar por estado
        response = client.get("/api/v1/facturas/buscar?estado=PENDIENTE")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Buscar por cliente
        response = client.get(
            f"/api/v1/facturas/buscar?cliente_id={self.test_data['cliente_id']}"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Buscar por fecha
        response = client.get(
            "/api/v1/facturas/buscar?fecha_desde=2026-01-01&fecha_hasta=2026-12-31"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    # ========== PRUEBAS DE ESTADÍSTICAS ==========
    
    def test_get_estadisticas(self):
        """Prueba obtener estadísticas."""
        response = client.get("/api/v1/estadisticas")
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura
        assert "total_clientes" in data
        assert "total_productos" in data
        assert "total_facturas" in data
        assert "facturas_por_estado" in data
        assert "total_ingresos" in data
        assert "promedio_factura" in data
        assert "periodo" in data
        
        # Verificar tipos
        assert isinstance(data["total_clientes"], int)
        assert isinstance(data["total_productos"], int)
        assert isinstance(data["total_facturas"], int)
        assert isinstance(data["facturas_por_estado"], dict)
        assert isinstance(data["total_ingresos"], float)
        assert isinstance(data["promedio_factura"], float)
    
    # ========== PRUEBAS DE VALIDACIÓN ==========
    
    def test_validation_error_response(self):
        """Prueba que los errores de validación se manejan correctamente."""
        # Enviar datos inválidos
        invalid_data = {
            "id_cliente": "not_a_number",  # Debería ser int
            "items": []
        }
        
        response = client.post("/api/v1/facturas", json=invalid_data)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_error_response_format(self):
        """Prueba el formato de las respuestas de error."""
        response = client.get("/api/v1/clientes/99999")
        assert response.status_code == 404
        data = response.json()
        
        # Verificar formato de error
        assert "detail" in data
        assert "status_code" in data


# ========== PRUEBAS DE INTEGRACIÓN ==========

class TestAPIEndToEnd:
    """Pruebas end-to-end de la API."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuración antes de cada prueba."""
        self.db = get_db_connection()
        self.test_cliente_id = None
        self.test_producto_ids = []
        
        # Crear datos de prueba
        self._create_test_data()
        yield
        self._cleanup_test_data()
    
    def _create_test_data(self):
        """Crea datos de prueba."""
        try:
            # Crear cliente
            query = """
                INSERT INTO clientes (identificacion, nombre) 
                VALUES (%s, %s)
            """
            params = (f"TEST-E2E-{os.urandom(4).hex().upper()}", 'Cliente E2E Test')
            success, cliente_id, _ = self.db.execute_insert(query, params)
            if success:
                self.test_cliente_id = cliente_id
            
            # Crear producto
            query = """
                INSERT INTO productos (codigo, nombre, precio_unitario, id_tipo_iva, stock) 
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (f"TEST-E2E-{os.urandom(4).hex().upper()}", 'Producto E2E', 100.00, 1, 50)
            success, prod_id, _ = self.db.execute_insert(query, params)
            if success:
                self.test_producto_ids.append(prod_id)
                
        except Exception as e:
            print(f"⚠️ Error al crear datos E2E: {e}")
    
    def _cleanup_test_data(self):
        """Limpia los datos de prueba."""
        try:
            if self.test_cliente_id:
                self.db.execute("DELETE FROM clientes WHERE id_cliente = %s", (self.test_cliente_id,))
            for prod_id in self.test_producto_ids:
                self.db.execute("DELETE FROM productos WHERE id_producto = %s", (prod_id,))
        except Exception as e:
            print(f"⚠️ Error al limpiar datos E2E: {e}")
    
    def test_flujo_completo_facturacion(self):
        """Prueba el flujo completo de facturación."""
        if not self.test_cliente_id or not self.test_producto_ids:
            pytest.skip("No hay datos de prueba E2E")
        
        # 1. Crear factura
        factura_data = {
            "id_cliente": self.test_cliente_id,
            "items": [
                {
                    "id_producto": self.test_producto_ids[0],
                    "cantidad": 2,
                    "precio_unitario": 100.00
                }
            ],
            "observaciones": "Factura E2E Test"
        }
        
        response = client.post("/api/v1/facturas", json=factura_data)
        assert response.status_code == 201
        factura = response.json()
        factura_id = factura["id_factura"]
        
        # 2. Obtener factura
        response = client.get(f"/api/v1/facturas/{factura_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id_factura"] == factura_id
        assert data["estado"] == "PENDIENTE"
        
        # 3. Actualizar estado a PAGADA
        response = client.put(
            f"/api/v1/facturas/{factura_id}/estado?estado=PAGADA"
        )
        assert response.status_code == 200
        
        # 4. Verificar estado actualizado
        response = client.get(f"/api/v1/facturas/{factura_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "PAGADA"
        
        # 5. Anular la factura
        response = client.post(
            f"/api/v1/facturas/{factura_id}/anular?motivo=Prueba E2E"
        )
        assert response.status_code == 200
        
        # 6. Verificar anulación
        response = client.get(f"/api/v1/facturas/{factura_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "ANULADA"
        
        # 7. Verificar en estadísticas
        response = client.get("/api/v1/estadisticas")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_facturas"] >= 1


# Configuración para ejecutar pruebas
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=1"])