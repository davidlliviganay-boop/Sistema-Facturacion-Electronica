"""
Script: test_connection.py
Descripción: Prueba rápida de la conexión a la base de datos.
"""

import sys
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Agregar src al path de manera más robusta
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from database import get_db_connection
except ImportError as e:
    print(f"❌ Error al importar database: {e}")
    print("Verifica que el módulo 'database.py' existe en la carpeta 'src'")
    sys.exit(1)

# Constantes de prueba
TEST_PRODUCT = {
    'codigo': 'TEST-PROD-001',
    'nombre': 'Producto de Prueba',
    'precio': 50.00,
    'iva': 1,
    'stock': 5
}


def test_quick_connection():
    """Prueba rápida de conexión y operaciones básicas."""
    print("\n" + "="*50)
    print("PRUEBA DE CONEXIÓN A LA BASE DE DATOS")
    print("="*50)
    
    try:
        # 1. Obtener instancia
        print("\n1. Obteniendo instancia de DatabaseConnection...")
        db = get_db_connection()
        print("   ✅ Instancia obtenida correctamente")
        
        # 2. Probar conexión
        print("\n2. Probando conexión...")
        if db.test_connection():
            print("   ✅ Conexión exitosa a la base de datos")
        else:
            print("   ❌ Error en la conexión")
            print("   Verifica que el servidor de base de datos esté en ejecución")
            return
        
        # 3. Consultar clientes
        print("\n3. Consultando clientes...")
        success, result, error = db.fetch_all("SELECT * FROM clientes LIMIT 3")
        if success:
            if result:
                print(f"   ✅ Se encontraron {len(result)} clientes:")
                for cliente in result:
                    print(f"      - {cliente.get('nombre', 'N/A')} ({cliente.get('identificacion', 'N/A')})")
            else:
                print("   ℹ️ No hay clientes en la base de datos")
        else:
            print(f"   ❌ Error: {error}")
        
        # 4. Consultar productos
        print("\n4. Consultando productos...")
        success, result, error = db.fetch_all("SELECT * FROM productos LIMIT 5")
        if success:
            if result:
                print(f"   ✅ Se encontraron {len(result)} productos:")
                for producto in result:
                    print(f"      - {producto.get('nombre', 'N/A')} - ${producto.get('precio_unitario', 0):.2f}")
            else:
                print("   ℹ️ No hay productos en la base de datos")
        else:
            print(f"   ❌ Error: {error}")
        
        # 5. Prueba de inserción segura
        print("\n5. Probando inserción con consulta parametrizada...")
        query = """
            INSERT INTO productos (codigo, nombre, precio_unitario, id_tipo_iva, stock) 
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (TEST_PRODUCT['codigo'], TEST_PRODUCT['nombre'], 
                 TEST_PRODUCT['precio'], TEST_PRODUCT['iva'], TEST_PRODUCT['stock'])
        success, last_id, error = db.execute_insert(query, params)
        if success:
            print(f"   ✅ Producto insertado correctamente. ID: {last_id}")
        else:
            print(f"   ❌ Error: {error}")
        
        # 6. Prueba de prevención de inyección SQL
        print("\n6. Probando prevención de inyección SQL...")
        malicious_input = "1' OR '1'='1' -- "
        query = "SELECT * FROM clientes WHERE identificacion = %s"
        params = (malicious_input,)
        success, result, error = db.fetch_one(query, params)
        if success:
            if result is None:
                print("   ✅ La inyección SQL fue prevenida correctamente")
            else:
                print("   ⚠️ La inyección SQL podría ser posible")
        else:
            print(f"   ❌ Error: {error}")
        
        # 7. Limpiar datos de prueba
        print("\n7. Limpiando datos de prueba...")
        try:
            db.execute("DELETE FROM productos WHERE codigo LIKE 'TEST-%'")
            print("   ✅ Datos de prueba limpiados")
        except Exception as e:
            print(f"   ⚠️ No se pudieron limpiar datos de prueba: {e}")
        
        print("\n" + "="*50)
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error inesperado durante la prueba: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_quick_connection()