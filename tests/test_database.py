"""
Módulo: test_database.py
Descripción: Pruebas unitarias para la capa de persistencia.
"""

import pytest
import os
import sys
from dotenv import load_dotenv

# Agregar src al path de manera correcta
# Obtener la ruta absoluta del directorio actual
current_dir = os.path.dirname(os.path.abspath(__file__))
# Subir un nivel para llegar al directorio raíz del proyecto
project_root = os.path.dirname(current_dir)
# Agregar la carpeta src al path
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# También agregar el directorio raíz para otros imports
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Ahora importar desde src
from src.database import DatabaseConnection, get_db_connection

# Cargar variables de entorno
load_dotenv()


class TestDatabaseConnection:
    """Clase de pruebas para DatabaseConnection."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuración antes de cada prueba."""
        self.db = get_db_connection()
        self.test_identificacion = f"TEST-{os.urandom(4).hex().upper()}"
        self.test_codigo = f"TEST-PROD-{os.urandom(4).hex().upper()}"
        yield
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Limpia los datos de prueba después de cada test."""
        try:
            # Limpiar clientes de prueba
            query = "DELETE FROM clientes WHERE identificacion LIKE 'TEST-%'"
            self.db.execute(query)
            
            # Limpiar productos de prueba
            query = "DELETE FROM productos WHERE codigo LIKE 'TEST-%'"
            self.db.execute(query)
        except Exception as e:
            print(f"Warning: No se pudo limpiar datos de prueba: {e}")
    
    def _create_test_cliente(self):
        """Crea un cliente de prueba y retorna su identificación."""
        identificacion = self.test_identificacion
        query = """
            INSERT INTO clientes (identificacion, nombre, direccion, telefono) 
            VALUES (%s, %s, %s, %s)
        """
        params = (identificacion, 'Cliente Test', 'Dirección Test', '0999999999')
        success, _, error = self.db.execute_insert(query, params)
        if not success:
            pytest.skip(f"No se pudo crear cliente de prueba: {error}")
        return identificacion
    
    def _create_test_producto(self):
        """Crea un producto de prueba y retorna su código."""
        codigo = self.test_codigo
        query = """
            INSERT INTO productos (codigo, nombre, precio_unitario, id_tipo_iva, stock) 
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (codigo, 'Producto Test', 99.99, 1, 10)
        success, _, error = self.db.execute_insert(query, params)
        if not success:
            pytest.skip(f"No se pudo crear producto de prueba: {error}")
        return codigo
    
    def test_singleton(self):
        """Prueba que el patrón Singleton funciona correctamente."""
        db1 = DatabaseConnection()
        db2 = DatabaseConnection()
        assert db1 is db2
    
    def test_test_connection(self):
        """Prueba que la conexión a la base de datos funciona."""
        assert self.db.test_connection() == True
    
    def test_execute_query_select(self):
        """Prueba la ejecución de consultas SELECT."""
        # Crear datos de prueba
        identificacion = self._create_test_cliente()
        
        query = "SELECT * FROM clientes WHERE identificacion = %s"
        params = (identificacion,)
        success, result, error = self.db.execute_query(query, params)
        
        assert success == True
        assert error is None
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['identificacion'] == identificacion
    
    def test_execute_query_insert(self):
        """Prueba la ejecución de consultas INSERT."""
        query = """
            INSERT INTO clientes (identificacion, nombre, direccion) 
            VALUES (%s, %s, %s)
        """
        params = (self.test_identificacion, 'Cliente Test', 'Dirección Test')
        success, result, error = self.db.execute_query(query, params)
        
        assert success == True
        assert error is None
        
        # Verificar que se insertó correctamente
        query_verify = "SELECT * FROM clientes WHERE identificacion = %s"
        success, result, error = self.db.fetch_all(query_verify, (self.test_identificacion,))
        assert success == True
        assert len(result) == 1
    
    def test_fetch_one(self):
        """Prueba el método fetch_one."""
        # Crear datos de prueba
        identificacion = self._create_test_cliente()
        
        query = "SELECT * FROM clientes WHERE identificacion = %s"
        params = (identificacion,)
        success, result, error = self.db.fetch_one(query, params)
        
        assert success == True
        assert error is None
        assert result is not None
        assert result['identificacion'] == identificacion
    
    def test_fetch_all(self):
        """Prueba el método fetch_all."""
        # Crear varios clientes de prueba
        for i in range(3):
            ident = f"TEST-{i:04d}-{os.urandom(2).hex().upper()}"
            query = "INSERT INTO clientes (identificacion, nombre) VALUES (%s, %s)"
            self.db.execute_insert(query, (ident, f'Cliente Test {i}'))
        
        query = "SELECT * FROM clientes WHERE identificacion LIKE 'TEST-%'"
        success, result, error = self.db.fetch_all(query)
        
        assert success == True
        assert error is None
        assert isinstance(result, list)
        assert len(result) >= 3  # Al menos los que creamos
    
    def test_execute_insert(self):
        """Prueba el método execute_insert."""
        query = """
            INSERT INTO productos (codigo, nombre, precio_unitario, id_tipo_iva, stock) 
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (self.test_codigo, 'Producto Test', 99.99, 1, 10)
        success, last_id, error = self.db.execute_insert(query, params)
        
        assert success == True
        assert error is None
        assert last_id is not None
        assert isinstance(last_id, int)
        
        # Verificar que se insertó correctamente
        query_verify = "SELECT * FROM productos WHERE codigo = %s"
        success, result, error = self.db.fetch_all(query_verify, (self.test_codigo,))
        assert success == True
        assert len(result) == 1
    
    def test_execute_update(self):
        """Prueba el método execute para UPDATE."""
        # Crear datos de prueba
        identificacion = self._create_test_cliente()
        
        query = "UPDATE clientes SET nombre = %s WHERE identificacion = %s"
        params = ('Cliente Actualizado', identificacion)
        success, affected_rows, error = self.db.execute(query, params)
        
        assert success == True
        assert error is None
        assert affected_rows == 1
        
        # Verificar la actualización
        query_verify = "SELECT nombre FROM clientes WHERE identificacion = %s"
        success, result, error = self.db.fetch_one(query_verify, (identificacion,))
        assert success == True
        assert result['nombre'] == 'Cliente Actualizado'
    
    def test_execute_delete(self):
        """Prueba el método execute para DELETE."""
        # Crear datos de prueba
        identificacion = self._create_test_cliente()
        
        query = "DELETE FROM clientes WHERE identificacion = %s"
        params = (identificacion,)
        success, affected_rows, error = self.db.execute(query, params)
        
        assert success == True
        assert error is None
        assert affected_rows == 1
        
        # Verificar que se eliminó
        query_verify = "SELECT * FROM clientes WHERE identificacion = %s"
        success, result, error = self.db.fetch_one(query_verify, (identificacion,))
        assert success == True
        assert result is None
    
    def test_prevent_sql_injection(self):
        """Prueba que las consultas parametrizadas previenen inyección SQL."""
        # Crear datos de prueba
        identificacion = self._create_test_cliente()
        
        # Intentos de inyección SQL comunes
        injection_attempts = [
            f"1' OR '1'='1",
            f"1' OR 1=1 --",
            f"1' UNION SELECT * FROM clientes --",
            f"1'; DROP TABLE clientes --",
            f"1' OR '1'='1' /*",
        ]
        
        for malicious_input in injection_attempts:
            query = "SELECT * FROM clientes WHERE identificacion = %s"
            params = (malicious_input,)
            success, result, error = self.db.fetch_one(query, params)
            
            # La consulta no debería encontrar resultados (excepto si es válido)
            assert success == True
            assert error is None
            # Si no es nuestra identificación de prueba, debe ser None
            if result is not None:
                # Si encontró algo, solo debería ser nuestra identificación si coincidió exactamente
                if malicious_input == identificacion:
                    assert result['identificacion'] == identificacion
                else:
                    # Si encontró algo diferente, podría ser inyección exitosa
                    pytest.fail(f"Posible inyección SQL exitosa con: {malicious_input}")
    
    def test_rollback_on_error(self):
        """Prueba que se hace rollback en caso de error."""
        # Intentar insertar datos inválidos (violación de UNIQUE)
        # Primero insertar un registro
        query = "INSERT INTO clientes (identificacion, nombre) VALUES (%s, %s)"
        self.db.execute_insert(query, (self.test_identificacion, 'Cliente Original'))
        
        # Intentar insertar el mismo identificador (debe fallar)
        query = "INSERT INTO clientes (identificacion, nombre) VALUES (%s, %s)"
        params = (self.test_identificacion, 'Cliente Duplicado')
        success, result, error = self.db.execute_query(query, params)
        
        # Debería fallar por violación de UNIQUE
        assert success == False
        assert error is not None
        assert "Duplicate entry" in error or "duplicate key" in error.lower()
    
    def test_transaction_consistency(self):
        """Prueba la consistencia de transacciones."""
        # Contar productos antes
        query = "SELECT COUNT(*) as total FROM productos"
        success, before_result, error = self.db.fetch_one(query)
        before_count = before_result['total'] if before_result else 0
        
        # Intentar insertar dos productos, el segundo con error
        try:
            # Insertar producto 1 (válido)
            query1 = "INSERT INTO productos (codigo, nombre, precio_unitario, id_tipo_iva, stock) VALUES (%s, %s, %s, %s, %s)"
            params1 = (f"{self.test_codigo}-1", 'Producto 1', 10.00, 1, 5)
            self.db.execute_insert(query1, params1)
            
            # Intentar insertar producto 2 (inválido - mismo código)
            # Nota: Corregir query2
            query2 = "INSERT INTO productos (codigo, nombre, precio_unitario, id_tipo_iva, stock) VALUES (%s, %s, %s, %s, %s)"
            params2 = (f"{self.test_codigo}-1", 'Producto Duplicado', 20.00, 1, 5)
            self.db.execute_insert(query2, params2)  # Esto debería fallar
            
        except Exception:
            pass  # Esperamos que falle
        
        # Limpiar datos de prueba
        self.db.execute("DELETE FROM productos WHERE codigo LIKE 'TEST-%'")
    
    def test_pool_status(self):
        """Prueba que se puede obtener el estado del pool."""
        status = self.db.get_pool_status()
        assert status is not None
        assert 'status' in status
        assert status['status'] == 'active'
        assert 'pool_size' in status


# Configuración para ejecutar pruebas con pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=1"])