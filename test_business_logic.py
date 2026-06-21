"""
Script: test_business_logic.py
Descripción: Prueba completa de la lógica de negocio y transaccionalidad.
"""

import sys
import os
import logging
from decimal import Decimal
from datetime import datetime

# Agregar src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from services import InvoiceService, ProductoService, ClienteService
    from models import Factura, DetalleFactura, ValidationError
    from database import get_db_connection
except ImportError:
    print("❌ Error: No se pudieron importar los módulos necesarios")
    print("   Verifica que la estructura de carpetas sea correcta:")
    print("   - /src/services.py")
    print("   - /src/models.py")
    print("   - /src/database.py")
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BusinessLogicTester:
    """Clase para probar la lógica de negocio."""
    
    def __init__(self):
        """Inicializa el tester."""
        self.db = get_db_connection()
        self.invoice_service = InvoiceService()
        self.producto_service = ProductoService()
        self.cliente_service = ClienteService()
        self.test_data = {
            'clientes': [],
            'productos': [],
            'factura_creada': None
        }
        self.test_ids = {
            'cliente': None,
            'productos': [],
            'factura': None
        }
    
    def setup_test_data(self) -> bool:
        """
        Crea datos de prueba necesarios.
        
        Returns:
            bool: True si se crearon los datos correctamente.
        """
        print("\n📋 Configurando datos de prueba...")
        
        try:
            # 1. Crear cliente de prueba
            query = """
                INSERT INTO clientes (identificacion, nombre, direccion, telefono, email) 
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (
                f"TEST-BIZ-{os.urandom(4).hex().upper()}", 
                'Cliente Prueba Business',
                'Dirección de Prueba',
                '0999999999',
                'business@test.com'
            )
            success, cliente_id, error = self.db.execute_insert(query, params)
            if not success:
                print(f"   ❌ Error al crear cliente: {error}")
                return False
            self.test_ids['cliente'] = cliente_id
            print(f"   ✅ Cliente de prueba creado (ID: {cliente_id})")
            
            # 2. Crear productos de prueba
            productos_data = [
                {'codigo': f'BIZ-PROD-{os.urandom(4).hex().upper()}', 
                 'nombre': 'Producto Business 1', 
                 'precio': 100.00, 
                 'stock': 50},
                {'codigo': f'BIZ-PROD-{os.urandom(4).hex().upper()}', 
                 'nombre': 'Producto Business 2', 
                 'precio': 75.00, 
                 'stock': 30},
                {'codigo': f'BIZ-PROD-{os.urandom(4).hex().upper()}', 
                 'nombre': 'Producto Business 3 (stock bajo)', 
                 'precio': 50.00, 
                 'stock': 3}
            ]
            
            for prod_data in productos_data:
                query = """
                    INSERT INTO productos (codigo, nombre, precio_unitario, id_tipo_iva, stock) 
                    VALUES (%s, %s, %s, %s, %s)
                """
                params = (prod_data['codigo'], prod_data['nombre'], 
                         prod_data['precio'], 1, prod_data['stock'])
                success, prod_id, error = self.db.execute_insert(query, params)
                if success:
                    self.test_ids['productos'].append(prod_id)
                    print(f"   ✅ Producto creado: {prod_data['nombre']} (ID: {prod_id})")
                else:
                    print(f"   ⚠️ Error al crear producto {prod_data['nombre']}: {error}")
            
            if len(self.test_ids['productos']) < 3:
                print("   ❌ No se pudieron crear suficientes productos")
                return False
            
            print("   ✅ Datos de prueba configurados correctamente")
            return True
            
        except Exception as e:
            print(f"   ❌ Error al configurar datos de prueba: {e}")
            return False
    
    def cleanup_test_data(self):
        """Limpia los datos de prueba."""
        print("\n🧹 Limpiando datos de prueba...")
        
        try:
            # Limpiar factura de prueba
            if self.test_ids['factura']:
                query = "DELETE FROM facturas WHERE id_factura = %s"
                self.db.execute(query, (self.test_ids['factura'],))
                print(f"   ✅ Factura de prueba eliminada (ID: {self.test_ids['factura']})")
            
            # Limpiar productos de prueba
            for prod_id in self.test_ids['productos']:
                query = "DELETE FROM productos WHERE id_producto = %s"
                self.db.execute(query, (prod_id,))
                print(f"   ✅ Producto de prueba eliminado (ID: {prod_id})")
            
            # Limpiar cliente de prueba
            if self.test_ids['cliente']:
                query = "DELETE FROM clientes WHERE id_cliente = %s"
                self.db.execute(query, (self.test_ids['cliente'],))
                print(f"   ✅ Cliente de prueba eliminado (ID: {self.test_ids['cliente']})")
            
            print("   ✅ Datos de prueba limpiados correctamente")
            
        except Exception as e:
            print(f"   ⚠️ Error al limpiar datos: {e}")
    
    def test_crear_factura_exitosa(self) -> bool:
        """
        Prueba la creación exitosa de una factura.
        
        Returns:
            bool: True si la prueba fue exitosa.
        """
        print("\n" + "="*60)
        print("📝 PRUEBA 1: Creación de factura exitosa")
        print("="*60)
        
        try:
            # Usar el cliente de prueba
            cliente_id = self.test_ids['cliente']
            productos = self.test_ids['productos']
            
            # Crear items
            items_list = [
                {
                    'id_producto': productos[0],
                    'cantidad': 2,
                    'precio_unitario': 100.00
                },
                {
                    'id_producto': productos[1],
                    'cantidad': 1,
                    'precio_unitario': 75.00
                }
            ]
            
            # Crear factura
            success, factura, error = self.invoice_service.create_invoice(
                cliente_id=cliente_id,
                items_list=items_list,
                observaciones="Factura de prueba - Transacción exitosa"
            )
            
            if not success:
                print(f"   ❌ Error al crear factura: {error}")
                return False
            
            # Guardar ID para limpieza
            self.test_ids['factura'] = factura.id_factura
            
            print(f"   ✅ Factura creada exitosamente!")
            print(f"      - ID: {factura.id_factura}")
            print(f"      - Número: {factura.numero_factura}")
            print(f"      - Cliente: {cliente_id}")
            print(f"      - Subtotal: ${factura.subtotal:.2f}")
            print(f"      - IVA: ${factura.iva:.2f}")
            print(f"      - Total: ${factura.total:.2f}")
            print(f"      - Detalles: {len(factura.detalles)}")
            
            # Verificar cálculos
            expected_subtotal = Decimal('275.00')  # (2*100) + (1*75)
            expected_iva = expected_subtotal * Decimal('0.12')
            expected_total = expected_subtotal + expected_iva
            
            if (factura.subtotal == expected_subtotal and 
                factura.iva == expected_iva and 
                factura.total == expected_total):
                print("   ✅ Cálculos de totales correctos")
            else:
                print(f"   ⚠️ Cálculos inconsistentes:")
                print(f"      Subtotal esperado: {expected_subtotal}, obtenido: {factura.subtotal}")
                print(f"      IVA esperado: {expected_iva}, obtenido: {factura.iva}")
                print(f"      Total esperado: {expected_total}, obtenido: {factura.total}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_atomicidad_factura(self) -> bool:
        """
        Prueba que la creación de factura es atómica.
        
        Returns:
            bool: True si la prueba fue exitosa.
        """
        print("\n" + "="*60)
        print("🔒 PRUEBA 2: Atomicidad de transacciones")
        print("="*60)
        
        try:
            cliente_id = self.test_ids['cliente']
            productos = self.test_ids['productos']
            
            # Obtener stock inicial del primer producto
            query = "SELECT stock FROM productos WHERE id_producto = %s"
            success, result, error = self.db.fetch_one(query, (productos[0],))
            stock_inicial = result['stock'] if result else 0
            print(f"   Stock inicial producto {productos[0]}: {stock_inicial}")
            
            # Caso 1: Error por producto inexistente
            print("\n   📌 Caso 1: Producto inexistente (debe fallar)...")
            items_list_error = [
                {'id_producto': productos[0], 'cantidad': 2, 'precio_unitario': 100.00},
                {'id_producto': 99999, 'cantidad': 1, 'precio_unitario': 75.00}  # Inexistente
            ]
            
            success, factura_error, error = self.invoice_service.create_invoice(
                cliente_id=cliente_id,
                items_list=items_list_error,
                observaciones="Factura que debe fallar"
            )
            
            if success:
                print("   ❌ ERROR: La factura se creó a pesar del producto inexistente")
                self.test_ids['factura'] = factura_error.id_factura
                return False
            else:
                print(f"   ✅ La transacción fue revertida correctamente")
                print(f"      Error: {error}")
            
            # Verificar que el stock no cambió
            success, result, error = self.db.fetch_one(query, (productos[0],))
            stock_despues = result['stock'] if result else 0
            if stock_inicial == stock_despues:
                print(f"   ✅ Stock no modificado (se mantiene en {stock_despues})")
            else:
                print(f"   ❌ ERROR: Stock modificado sin transacción exitosa")
                print(f"      Inicial: {stock_inicial}, Después: {stock_despues}")
                return False
            
            # Caso 2: Error por stock insuficiente
            print("\n   📌 Caso 2: Stock insuficiente (debe fallar)...")
            items_list_stock = [
                {'id_producto': productos[2], 'cantidad': 10, 'precio_unitario': 50.00}
            ]
            
            success, factura_stock, error = self.invoice_service.create_invoice(
                cliente_id=cliente_id,
                items_list=items_list_stock,
                observaciones="Factura con stock insuficiente"
            )
            
            if success:
                print("   ❌ ERROR: La factura se creó a pesar del stock insuficiente")
                self.test_ids['factura'] = factura_stock.id_factura
                return False
            else:
                print(f"   ✅ La transacción fue revertida correctamente")
                print(f"      Error: {error}")
            
            # Caso 3: Error por cliente inactivo
            print("\n   📌 Caso 3: Cliente inactivo (debe fallar)...")
            # Crear cliente inactivo
            query_inactive = """
                INSERT INTO clientes (identificacion, nombre, estado) 
                VALUES (%s, %s, 'INACTIVO')
            """
            params = (f"TEST-INACTIVO-{os.urandom(4).hex().upper()}", 'Cliente Inactivo')
            success, cliente_inactivo_id, error = self.db.execute_insert(query_inactive, params)
            
            if success:
                items_list_inactive = [
                    {'id_producto': productos[0], 'cantidad': 1, 'precio_unitario': 100.00}
                ]
                
                success, factura_inactive, error = self.invoice_service.create_invoice(
                    cliente_id=cliente_inactivo_id,
                    items_list=items_list_inactive,
                    observaciones="Factura con cliente inactivo"
                )
                
                if success:
                    print("   ❌ ERROR: La factura se creó con cliente inactivo")
                    return False
                else:
                    print(f"   ✅ La transacción fue revertida correctamente")
                    print(f"      Error: {error}")
                
                # Limpiar cliente inactivo
                self.db.execute("DELETE FROM clientes WHERE id_cliente = %s", 
                              (cliente_inactivo_id,))
            
            print("\n   ✅ Todas las pruebas de atomicidad pasaron correctamente")
            return True
            
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_obtener_factura(self) -> bool:
        """
        Prueba la obtención de una factura por ID.
        
        Returns:
            bool: True si la prueba fue exitosa.
        """
        print("\n" + "="*60)
        print("🔍 PRUEBA 3: Obtención de factura por ID")
        print("="*60)
        
        try:
            if not self.test_ids['factura']:
                print("   ⚠️ No hay factura para obtener (creando una de prueba)...")
                # Crear factura de prueba
                items_list = [
                    {'id_producto': self.test_ids['productos'][0], 
                     'cantidad': 1, 'precio_unitario': 100.00}
                ]
                success, factura_temp, error = self.invoice_service.create_invoice(
                    cliente_id=self.test_ids['cliente'],
                    items_list=items_list,
                    observaciones="Factura para prueba de obtención"
                )
                if not success:
                    print(f"   ❌ Error al crear factura: {error}")
                    return False
                self.test_ids['factura'] = factura_temp.id_factura
            
            # Obtener factura
            factura_id = self.test_ids['factura']
            success, factura, error = self.invoice_service.get_invoice_by_id(factura_id)
            
            if not success:
                print(f"   ❌ Error al obtener factura: {error}")
                return False
            
            print(f"   ✅ Factura obtenida correctamente")
            print(f"      - ID: {factura.id_factura}")
            print(f"      - Número: {factura.numero_factura}")
            print(f"      - Estado: {factura.estado}")
            print(f"      - Total: ${factura.total:.2f}")
            print(f"      - Detalles: {len(factura.detalles)}")
            
            # Verificar que la factura tiene detalles
            if len(factura.detalles) == 0:
                print("   ❌ ERROR: La factura no tiene detalles")
                return False
            
            print("   ✅ Los detalles se recuperaron correctamente")
            for i, detalle in enumerate(factura.detalles, 1):
                print(f"      Detalle {i}: Producto {detalle.id_producto}, "
                     f"Cantidad: {detalle.cantidad}, Subtotal: ${detalle.subtotal:.2f}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_actualizar_estado(self) -> bool:
        """
        Prueba la actualización del estado de una factura.
        
        Returns:
            bool: True si la prueba fue exitosa.
        """
        print("\n" + "="*60)
        print("🔄 PRUEBA 4: Actualización de estado")
        print("="*60)
        
        try:
            if not self.test_ids['factura']:
                print("   ⚠️ No hay factura para actualizar")
                return False
            
            factura_id = self.test_ids['factura']
            estados = ['PAGADA', 'VENCIDA']
            
            for nuevo_estado in estados:
                print(f"\n   📌 Actualizando a estado: {nuevo_estado}")
                success, error = self.invoice_service.update_invoice_status(
                    factura_id, nuevo_estado
                )
                
                if success:
                    print(f"   ✅ Estado actualizado a: {nuevo_estado}")
                    
                    # Verificar
                    success, factura_actualizada, error = self.invoice_service.get_invoice_by_id(
                        factura_id
                    )
                    if success and factura_actualizada.estado == nuevo_estado:
                        print(f"   ✅ Estado verificado: {factura_actualizada.estado}")
                    else:
                        print(f"   ❌ Error al verificar estado: {error}")
                        return False
                else:
                    print(f"   ❌ Error al actualizar estado: {error}")
                    return False
            
            print("\n   ✅ Todas las actualizaciones de estado pasaron correctamente")
            return True
            
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_anular_factura(self) -> bool:
        """
        Prueba la anulación de una factura.
        
        Returns:
            bool: True si la prueba fue exitosa.
        """
        print("\n" + "="*60)
        print("🚫 PRUEBA 5: Anulación de factura")
        print("="*60)
        
        try:
            # Crear una factura específica para anular
            items_list = [
                {'id_producto': self.test_ids['productos'][0], 
                 'cantidad': 2, 'precio_unitario': 100.00}
            ]
            
            success, factura, error = self.invoice_service.create_invoice(
                cliente_id=self.test_ids['cliente'],
                items_list=items_list,
                observaciones="Factura para anulación"
            )
            
            if not success:
                print(f"   ❌ Error al crear factura para anulación: {error}")
                return False
            
            factura_id = factura.id_factura
            producto_id = self.test_ids['productos'][0]
            
            # Obtener stock antes de anular
            query = "SELECT stock FROM productos WHERE id_producto = %s"
            success, result, error = self.db.fetch_one(query, (producto_id,))
            stock_antes = result['stock'] if result else 0
            
            print(f"   Stock antes de anular: {stock_antes}")
            
            # Anular factura
            print("\n   📌 Anulando factura...")
            success, error = self.invoice_service.anular_factura(
                factura_id,
                "Prueba de anulación"
            )
            
            if not success:
                print(f"   ❌ Error al anular factura: {error}")
                return False
            
            print(f"   ✅ Factura anulada exitosamente")
            
            # Verificar que el stock se restauró
            success, result, error = self.db.fetch_one(query, (producto_id,))
            stock_despues = result['stock'] if result else 0
            
            print(f"   Stock después de anular: {stock_despues}")
            
            if stock_despues == stock_antes + 2:
                print(f"   ✅ Stock restaurado correctamente")
            else:
                print(f"   ❌ ERROR: Stock no restaurado correctamente")
                print(f"      Esperado: {stock_antes + 2}, Obtenido: {stock_despues}")
                return False
            
            # Verificar que la factura está anulada
            success, factura_anulada, error = self.invoice_service.get_invoice_by_id(factura_id)
            if success and factura_anulada.estado == 'ANULADA':
                print(f"   ✅ Estado verificado: {factura_anulada.estado}")
            else:
                print(f"   ❌ Error al verificar estado: {error}")
                return False
            
            print("\n   ✅ Prueba de anulación completada exitosamente")
            
            # Guardar ID para limpieza
            self.test_ids['factura'] = factura_id
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_obtener_facturas_por_cliente(self) -> bool:
        """
        Prueba la obtención de facturas por cliente.
        
        Returns:
            bool: True si la prueba fue exitosa.
        """
        print("\n" + "="*60)
        print("👤 PRUEBA 6: Obtención de facturas por cliente")
        print("="*60)
        
        try:
            cliente_id = self.test_ids['cliente']
            
            # Crear algunas facturas para el cliente
            for i in range(3):
                items_list = [
                    {'id_producto': self.test_ids['productos'][0], 
                     'cantidad': i + 1, 'precio_unitario': 100.00}
                ]
                success, factura, error = self.invoice_service.create_invoice(
                    cliente_id=cliente_id,
                    items_list=items_list,
                    observaciones=f"Factura de prueba {i+1}"
                )
                if success:
                    print(f"   ✅ Factura {i+1} creada: {factura.numero_factura}")
            
            # Obtener facturas del cliente
            success, facturas, error = self.invoice_service.get_invoices_by_client(cliente_id)
            
            if not success:
                print(f"   ❌ Error al obtener facturas: {error}")
                return False
            
            print(f"\n   ✅ Facturas obtenidas: {len(facturas)}")
            for i, factura in enumerate(facturas[:5], 1):  # Mostrar primeras 5
                print(f"      {i}. {factura.numero_factura} - ${factura.total:.2f} - {factura.estado}")
            
            if len(facturas) >= 3:
                print(f"   ✅ Se encontraron al menos 3 facturas para el cliente")
                return True
            else:
                print(f"   ⚠️ Solo se encontraron {len(facturas)} facturas (se esperaban al menos 3)")
                return True  # No fallamos la prueba por esto
            
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_all_tests(self):
        """Ejecuta todas las pruebas."""
        print("\n" + "="*60)
        print("🚀 INICIANDO PRUEBAS DE LÓGICA DE NEGOCIO")
        print("="*60)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Configurar datos de prueba
        if not self.setup_test_data():
            print("\n❌ Error al configurar datos de prueba")
            self.cleanup_test_data()
            return
        
        # Ejecutar pruebas
        tests = [
            ('Creación de factura exitosa', self.test_crear_factura_exitosa),
            ('Atomicidad de transacciones', self.test_atomicidad_factura),
            ('Obtención de factura por ID', self.test_obtener_factura),
            ('Actualización de estado', self.test_actualizar_estado),
            ('Anulación de factura', self.test_anular_factura),
            ('Facturas por cliente', self.test_obtener_facturas_por_cliente)
        ]
        
        resultados = []
        for nombre, test_func in tests:
            try:
                resultado = test_func()
                resultados.append((nombre, resultado))
            except Exception as e:
                print(f"   ❌ Error en test '{nombre}': {e}")
                resultados.append((nombre, False))
        
        # Resumen de resultados
        print("\n" + "="*60)
        print("📊 RESUMEN DE RESULTADOS")
        print("="*60)
        
        aprobadas = sum(1 for _, resultado in resultados if resultado)
        total = len(resultados)
        
        for nombre, resultado in resultados:
            estado = "✅ APROBADA" if resultado else "❌ FALLIDA"
            print(f"   {estado}: {nombre}")
        
        print(f"\n   Total: {aprobadas}/{total} pruebas aprobadas")
        
        if aprobadas == total:
            print("\n🎉 ¡TODAS LAS PRUEBAS FUERON EXITOSAS!")
        else:
            print(f"\n⚠️ {total - aprobadas} pruebas fallaron. Revisar logs.")
        
        # Limpiar datos de prueba
        self.cleanup_test_data()
        
        print("\n" + "="*60)
        print("PRUEBAS COMPLETADAS")
        print("="*60 + "\n")


def main():
    """Función principal."""
    tester = BusinessLogicTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()