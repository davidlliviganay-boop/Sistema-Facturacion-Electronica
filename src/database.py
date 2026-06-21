"""
Módulo: database.py
Descripción: Capa de Persistencia (Data Access Layer) para el sistema de facturación.
Implementa un patrón Singleton para manejar la conexión a MySQL de forma segura.
Autor: David Llivigañay
Fecha: 2026-06-20
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime  # Añadir esta importación
import mysql.connector
from mysql.connector import Error, pooling
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Clase Singleton para manejar la conexión a la base de datos MySQL.
    Implementa un pool de conexiones para mejorar el rendimiento.
    """
    
    _instance = None
    _connection_pool = None
    
    def __new__(cls):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self):
        """
        Inicializa el pool de conexiones a la base de datos.
        Lee las credenciales desde las variables de entorno.
        """
        try:
            # Validar variables de entorno críticas
            required_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Variables de entorno faltantes: {', '.join(missing_vars)}")
            
            # Configuración del pool de conexiones
            pool_config = {
                'pool_name': 'facturacion_pool',
                'pool_size': int(os.getenv('DB_POOL_SIZE', 5)),
                'pool_reset_session': True,
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT', 3306)),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'database': os.getenv('DB_NAME'),
                'use_pure': True,
                'autocommit': False,
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', 10))
            }
            
            # Crear el pool de conexiones
            self._connection_pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"Pool de conexiones inicializado correctamente (tamaño: {pool_config['pool_size']})")
            
        except ValueError as e:
            logger.error(f"Error de configuración: {e}")
            raise
        except Error as e:
            logger.error(f"Error al inicializar el pool de conexiones: {e}")
            raise
    
    def get_connection(self):
        """
        Obtiene una conexión del pool.
        
        Returns:
            MySQLConnection: Objeto de conexión a la base de datos.
        
        Raises:
            Error: Si no se puede obtener una conexión.
        """
        try:
            connection = self._connection_pool.get_connection()
            logger.debug(f"Conexión obtenida del pool (ID: {id(connection)})")
            return connection
        except Error as e:
            logger.error(f"Error al obtener conexión del pool: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[Union[tuple, dict]] = None) -> Tuple[bool, Any, Optional[str]]:
        """
        Ejecuta una consulta SQL con parámetros (prepared statements).
        Previene inyecciones SQL mediante consultas parametrizadas.
        
        Args:
            query (str): Consulta SQL con placeholders (%s o %(key)s).
            params (Optional[Union[tuple, dict]]): Parámetros para la consulta.
            
        Returns:
            Tuple[bool, Any, Optional[str]]: 
                - Éxito de la operación (True/False)
                - Resultado de la consulta (cursor o None)
                - Mensaje de error (si existe)
        """
        connection = None
        cursor = None
        
        try:
            # Obtener conexión del pool
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Ejecutar consulta con parámetros
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Obtener resultados si es SELECT
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                # No commit para SELECT
            else:
                connection.commit()
                result = cursor.rowcount
                
            logger.debug(f"Consulta ejecutada exitosamente: {query[:50]}...")
            return True, result, None
            
        except Error as e:
            if connection:
                connection.rollback()
            error_msg = f"Error en la consulta: {e}"
            logger.error(error_msg)
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            return False, None, error_msg
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def fetch_one(self, query: str, params: Optional[Union[tuple, dict]] = None) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Ejecuta una consulta SELECT y retorna un solo registro.
        
        Args:
            query (str): Consulta SQL con placeholders.
            params (Optional[Union[tuple, dict]]): Parámetros para la consulta.
            
        Returns:
            Tuple[bool, Optional[Dict], Optional[str]]:
                - Éxito de la operación
                - Diccionario con el registro o None
                - Mensaje de error (si existe)
        """
        success, result, error = self.execute_query(query, params)
        if success and result:
            return True, result[0] if result else None, None
        return success, None, error
    
    def fetch_all(self, query: str, params: Optional[Union[tuple, dict]] = None) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
        """
        Ejecuta una consulta SELECT y retorna todos los registros.
        
        Args:
            query (str): Consulta SQL con placeholders.
            params (Optional[Union[tuple, dict]]): Parámetros para la consulta.
            
        Returns:
            Tuple[bool, Optional[List[Dict]], Optional[str]]:
                - Éxito de la operación
                - Lista de diccionarios con los registros
                - Mensaje de error (si existe)
        """
        success, result, error = self.execute_query(query, params)
        if success:
            return True, result or [], None
        return False, [], error
    
    def execute_insert(self, query: str, params: Optional[Union[tuple, dict]] = None) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Ejecuta una consulta INSERT y retorna el ID generado.
        
        Args:
            query (str): Consulta SQL INSERT con placeholders.
            params (Optional[Union[tuple, dict]]): Parámetros para la consulta.
            
        Returns:
            Tuple[bool, Optional[int], Optional[str]]:
                - Éxito de la operación
                - ID generado por LAST_INSERT_ID() o None
                - Mensaje de error (si existe)
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            connection.commit()
            
            # Obtener el ID generado
            last_id = cursor.lastrowid
            
            logger.debug(f"INSERT ejecutado exitosamente. ID: {last_id}")
            return True, last_id, None
            
        except Error as e:
            if connection:
                connection.rollback()
            error_msg = f"Error en INSERT: {e}"
            logger.error(error_msg)
            return False, None, error_msg
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def execute(self, query: str, params: Optional[Union[tuple, dict]] = None) -> Tuple[bool, int, Optional[str]]:
        """
        Ejecuta una consulta que no retorna resultados (UPDATE, DELETE, etc.)
        
        Args:
            query (str): Consulta SQL con placeholders.
            params (Optional[Union[tuple, dict]]): Parámetros para la consulta.
            
        Returns:
            Tuple[bool, int, Optional[str]]:
                - Éxito de la operación
                - Número de filas afectadas
                - Mensaje de error (si existe)
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            affected_rows = cursor.rowcount
            connection.commit()
            
            logger.debug(f"Consulta ejecutada. Filas afectadas: {affected_rows}")
            return True, affected_rows, None
            
        except Error as e:
            if connection:
                connection.rollback()
            error_msg = f"Error al ejecutar consulta: {e}"
            logger.error(error_msg)
            return False, 0, error_msg
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def begin_transaction(self):
        """
        Inicia una transacción explícita.
        NOTA: Este método debe ser usado con cuidado. Es mejor usar
        los métodos execute_query/execute_insert que manejan transacciones automáticamente.
        """
        logger.warning("begin_transaction() está obsoleto. Use ejecución directa con commit/rollback automático.")
        # No implementamos este método porque con el pool de conexiones
        # no podemos mantener el estado de la transacción fácilmente
    
    def commit_transaction(self):
        """Método obsoleto - no implementado."""
        logger.warning("commit_transaction() está obsoleto. Use ejecución directa con commit/rollback automático.")
        return False
    
    def rollback_transaction(self):
        """Método obsoleto - no implementado."""
        logger.warning("rollback_transaction() está obsoleto. Use ejecución directa con commit/rollback automático.")
        return False
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión a la base de datos.
        
        Returns:
            bool: True si la conexión es exitosa, False en caso contrario.
        """
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if result and result[0] == 1:
                logger.info("Prueba de conexión exitosa")
                return True
            else:
                logger.error("Prueba de conexión falló: resultado inesperado")
                return False
                
        except Error as e:
            logger.error(f"Prueba de conexión fallida: {e}")
            return False
    
    def get_pool_status(self) -> Dict:
        """
        Obtiene el estado actual del pool de conexiones.
        
        Returns:
            Dict: Información del estado del pool.
        """
        if not self._connection_pool:
            return {'status': 'not_initialized'}
        
        return {
            'status': 'active',
            'pool_name': self._connection_pool.pool_name,
            'pool_size': self._connection_pool.pool_size,
            'connections_in_use': self._connection_pool._connections_in_use if hasattr(self._connection_pool, '_connections_in_use') else 'unknown'
        }


# Función de utilidad para obtener una instancia de la conexión
def get_db_connection() -> DatabaseConnection:
    """
    Obtiene la instancia única de DatabaseConnection.
    
    Returns:
        DatabaseConnection: Instancia de la conexión a la base de datos.
    """
    return DatabaseConnection()


# Función para probar la conexión
def test_connection() -> bool:
    """
    Función de utilidad para probar rápidamente la conexión.
    
    Returns:
        bool: True si la conexión es exitosa.
    """
    db = get_db_connection()
    return db.test_connection()