"""
Script: test_api_manual.py
Descripción: Prueba manual de la API REST usando requests.
Autor: David Llivigañay
Fecha: 2026-06-20
"""

import requests
import json
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Configuración
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

# Colores para terminal (opcional)
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg: str):
    """Imprime mensaje de éxito."""
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg: str):
    """Imprime mensaje de error."""
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_info(msg: str):
    """Imprime mensaje informativo."""
    print(f"{Colors.BLUE}ℹ️ {msg}{Colors.RESET}")

def print_warning(msg: str):
    """Imprime mensaje de advertencia."""
    print(f"{Colors.YELLOW}⚠️ {msg}{Colors.RESET}")

def print_response(title: str, response: requests.Response, show_data: bool = True):
    """Imprime la respuesta de la API de forma formateada."""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    
    try:
        data = response.json()
        if response.status_code >= 200 and response.status_code < 300:
            print_success(f"Request exitosa")
        else:
            print_error(f"Request fallida")
        
        if show_data:
            print(f"Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(f"Response (texto):")
        print(response.text)
    
    print(f"{'='*60}")
    return response

def check_connection() -> bool:
    """Verifica que la API esté disponible."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("API disponible")
            return True
        else:
            print_error(f"API no disponible (status: {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print_error("No se puede conectar a la API")
        print_info("Verifica que la API esté ejecutándose en http://localhost:8000")
        return False
    except requests.exceptions.Timeout:
        print_error("Timeout al conectar con la API")
        return False
    except Exception as e:
        print_error(f"Error al conectar: {e}")
        return False

def get_cliente_disponible() -> Optional[int]:
    """Obtiene el ID del primer cliente disponible."""
    try:
        response = requests.get(f"{API_V1}/clientes")
        if response.status_code == 200:
            clientes = response.json()
            if clientes:
                cliente_id = clientes[0]['id_cliente']
                print_success(f"Cliente disponible: {clientes[0]['nombre']} (ID: {cliente_id})")
                return cliente_id
        print_warning("No hay clientes disponibles en la base de datos")
        return None
    except Exception as e:
        print_error(f"Error al obtener clientes: {e}")
        return None

def get_productos_disponibles(cantidad: int = 2) -> list:
    """Obtiene una lista de productos disponibles."""
    try:
        response = requests.get(f"{API_V1}/productos")
        if response.status_code == 200:
            productos = response.json()
            if len(productos) >= cantidad:
                print_success(f"{len(productos)} productos disponibles")
                return productos[:cantidad]
            elif productos:
                print_warning(f"Solo {len(productos)} productos disponibles (se necesitan {cantidad})")
                return productos
            else:
                print_warning("No hay productos disponibles en la base de datos")
                return []
    except Exception as e:
        print_error(f"Error al obtener productos: {e}")
        return []

def test_health():
    """Prueba el endpoint de salud."""
    print("\n" + "="*60)
    print("🏥 PRUEBA 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print_response("Health Check", response)
        
        if response.status_code == 200:
            data = response.json()
            print_info(f"Estado: {data.get('status')}")
            print_info(f"Base de datos: {data.get('database')}")
            print_info(f"Timestamp: {data.get('timestamp')}")
            return True
    except Exception as e:
        print_error(f"Error en health check: {e}")
    return False

def test_root():
    """Prueba el endpoint raíz."""
    print("\n" + "="*60)
    print("🏠 PRUEBA 2: Root Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print_response("Root Endpoint", response)
        
        if response.status_code == 200:
            data = response.json()
            print_info(f"Mensaje: {data.get('message')}")
            print_info(f"Versión: {data.get('version')}")
            print_info(f"Documentación: {data.get('docs')}")
            return True
    except Exception as e:
        print_error(f"Error en root endpoint: {e}")
    return False

def test_clientes():
    """Prueba los endpoints de clientes."""
    print("\n" + "="*60)
    print("👤 PRUEBA 3: Endpoints de Clientes")
    print("="*60)
    
    try:
        # 3.1 Obtener todos los clientes
        print("\n3.1 Obteniendo todos los clientes...")
        response = requests.get(f"{API_V1}/clientes")
        print_response("Clientes - Lista", response)
        
        if response.status_code != 200:
            print_error("No se pudieron obtener los clientes")
            return False
        
        clientes = response.json()
        if not clientes:
            print_warning("No hay clientes en la base de datos")
            return False
        
        print_success(f"Clientes encontrados: {len(clientes)}")
        
        # 3.2 Obtener un cliente específico
        cliente_id = clientes[0]['id_cliente']
        print(f"\n3.2 Obteniendo cliente ID: {cliente_id}...")
        response = requests.get(f"{API_V1}/clientes/{cliente_id}")
        print_response(f"Cliente ID {cliente_id}", response)
        
        if response.status_code == 200:
            cliente = response.json()
            print_info(f"Nombre: {cliente.get('nombre')}")
            print_info(f"Identificación: {cliente.get('identificacion')}")
            print_info(f"Email: {cliente.get('email', 'No especificado')}")
            return True
        else:
            print_error(f"No se pudo obtener el cliente {cliente_id}")
            return False
            
    except Exception as e:
        print_error(f"Error en pruebas de clientes: {e}")
        return False

def test_productos():
    """Prueba los endpoints de productos."""
    print("\n" + "="*60)
    print("📦 PRUEBA 4: Endpoints de Productos")
    print("="*60)
    
    try:
        # 4.1 Obtener todos los productos
        print("\n4.1 Obteniendo todos los productos...")
        response = requests.get(f"{API_V1}/productos")
        print_response("Productos - Lista", response)
        
        if response.status_code != 200:
            print_error("No se pudieron obtener los productos")
            return False
        
        productos = response.json()
        if not productos:
            print_warning("No hay productos en la base de datos")
            return False
        
        print_success(f"Productos encontrados: {len(productos)}")
        
        # 4.2 Obtener un producto específico
        producto_id = productos[0]['id_producto']
        print(f"\n4.2 Obteniendo producto ID: {producto_id}...")
        response = requests.get(f"{API_V1}/productos/{producto_id}")
        print_response(f"Producto ID {producto_id}", response)
        
        if response.status_code == 200:
            producto = response.json()
            print_info(f"Nombre: {producto.get('nombre')}")
            print_info(f"Código: {producto.get('codigo')}")
            print_info(f"Precio: ${producto.get('precio_unitario')}")
            print_info(f"Stock: {producto.get('stock')}")
            return True
        else:
            print_error(f"No se pudo obtener el producto {producto_id}")
            return False
            
    except Exception as e:
        print_error(f"Error en pruebas de productos: {e}")
        return False

def test_crear_factura():
    """Prueba la creación de una factura."""
    print("\n" + "="*60)
    print("📄 PRUEBA 5: Creación de Factura")
    print("="*60)
    
    try:
        # Obtener cliente disponible
        cliente_id = get_cliente_disponible()
        if not cliente_id:
            print_error("No hay cliente disponible para crear factura")
            return None
        
        # Obtener productos disponibles
        productos = get_productos_disponibles(2)
        if len(productos) < 2:
            print_error("No hay suficientes productos disponibles")
            return None
        
        # Crear datos de factura
        factura_data = {
            "id_cliente": cliente_id,
            "items": [
                {
                    "id_producto": productos[0]['id_producto'],
                    "cantidad": 2,
                    "precio_unitario": float(productos[0]['precio_unitario']),
                    "descuento": 0.0
                },
                {
                    "id_producto": productos[1]['id_producto'],
                    "cantidad": 1,
                    "precio_unitario": float(productos[1]['precio_unitario']),
                    "descuento": 0.0
                }
            ],
            "observaciones": "Factura de prueba desde script manual",
            "fecha_emision": datetime.now().date().isoformat()
        }
        
        print("\n📤 Enviando datos de factura:")
        print(json.dumps(factura_data, indent=2))
        
        response = requests.post(f"{API_V1}/facturas", json=factura_data)
        print_response("Crear Factura", response)
        
        if response.status_code == 201:
            factura = response.json()
            print_success(f"Factura creada exitosamente!")
            print_info(f"ID: {factura['id_factura']}")
            print_info(f"Número: {factura['numero_factura']}")
            print_info(f"Total: ${factura['total']:.2f}")
            print_info(f"Estado: {factura['estado']}")
            print_info(f"Detalles: {len(factura['detalles'])} items")
            return factura['id_factura']
        else:
            print_error("No se pudo crear la factura")
            if response.status_code == 400:
                error_data = response.json()
                print_info(f"Error: {error_data.get('detail', 'Error desconocido')}")
            return None
            
    except Exception as e:
        print_error(f"Error en creación de factura: {e}")
        return None

def test_obtener_factura(factura_id: int):
    """Prueba la obtención de una factura por ID."""
    print("\n" + "="*60)
    print("🔍 PRUEBA 6: Obtener Factura por ID")
    print("="*60)
    
    if not factura_id:
        print_warning("No hay factura para obtener")
        return False
    
    try:
        print(f"\nObteniendo factura ID: {factura_id}...")
        response = requests.get(f"{API_V1}/facturas/{factura_id}")
        print_response(f"Factura {factura_id}", response)
        
        if response.status_code == 200:
            factura = response.json()
            print_success("Factura obtenida correctamente")
            print_info(f"Número: {factura['numero_factura']}")
            print_info(f"Cliente: {factura['cliente']['nombre']}")
            print_info(f"Total: ${factura['total']:.2f}")
            print_info(f"Estado: {factura['estado']}")
            print_info(f"Detalles: {len(factura['detalles'])} items")
            return True
        else:
            print_error("No se pudo obtener la factura")
            return False
            
    except Exception as e:
        print_error(f"Error al obtener factura: {e}")
        return False

def test_actualizar_estado(factura_id: int):
    """Prueba la actualización del estado de una factura."""
    print("\n" + "="*60)
    print("🔄 PRUEBA 7: Actualizar Estado de Factura")
    print("="*60)
    
    if not factura_id:
        print_warning("No hay factura para actualizar")
        return False
    
    try:
        estados = ['PAGADA', 'VENCIDA']
        
        for estado in estados:
            print(f"\n📌 Actualizando a estado: {estado}")
            response = requests.put(
                f"{API_V1}/facturas/{factura_id}/estado",
                params={"estado": estado}
            )
            print_response(f"Actualizar Estado - {estado}", response)
            
            if response.status_code == 200:
                print_success(f"Estado actualizado a: {estado}")
                
                # Verificar el cambio
                verify_response = requests.get(f"{API_V1}/facturas/{factura_id}")
                if verify_response.status_code == 200:
                    factura = verify_response.json()
                    if factura['estado'] == estado:
                        print_success(f"Estado verificado: {factura['estado']}")
                    else:
                        print_error(f"Estado no coincide: esperado {estado}, obtenido {factura['estado']}")
                        return False
            else:
                print_error(f"No se pudo actualizar a {estado}")
                return False
        
        return True
            
    except Exception as e:
        print_error(f"Error al actualizar estado: {e}")
        return False

def test_anular_factura(factura_id: int):
    """Prueba la anulación de una factura."""
    print("\n" + "="*60)
    print("🚫 PRUEBA 8: Anular Factura")
    print("="*60)
    
    if not factura_id:
        print_warning("No hay factura para anular")
        return False
    
    try:
        # Primero cambiar a PENDIENTE para poder anular
        print("\n📌 Cambiando a estado PENDIENTE...")
        response = requests.put(
            f"{API_V1}/facturas/{factura_id}/estado",
            params={"estado": "PENDIENTE"}
        )
        
        if response.status_code != 200:
            print_warning("No se pudo cambiar a PENDIENTE")
        
        print("\n📌 Anulando factura...")
        response = requests.post(
            f"{API_V1}/facturas/{factura_id}/anular",
            params={"motivo": "Prueba de anulación desde script"}
        )
        print_response("Anular Factura", response)
        
        if response.status_code == 200:
            print_success("Factura anulada correctamente")
            
            # Verificar la anulación
            verify_response = requests.get(f"{API_V1}/facturas/{factura_id}")
            if verify_response.status_code == 200:
                factura = verify_response.json()
                if factura['estado'] == 'ANULADA':
                    print_success(f"Estado verificado: {factura['estado']}")
                    return True
                else:
                    print_error(f"Estado no es ANULADA: {factura['estado']}")
                    return False
        else:
            print_error("No se pudo anular la factura")
            return False
            
    except Exception as e:
        print_error(f"Error al anular factura: {e}")
        return False

def test_estadisticas():
    """Prueba el endpoint de estadísticas."""
    print("\n" + "="*60)
    print("📊 PRUEBA 9: Estadísticas del Sistema")
    print("="*60)
    
    try:
        response = requests.get(f"{API_V1}/estadisticas")
        print_response("Estadísticas", response)
        
        if response.status_code == 200:
            stats = response.json()
            print_success("Estadísticas obtenidas correctamente")
            print_info(f"Total clientes: {stats.get('total_clientes', 0)}")
            print_info(f"Total productos: {stats.get('total_productos', 0)}")
            print_info(f"Total facturas: {stats.get('total_facturas', 0)}")
            print_info(f"Total ingresos: ${stats.get('total_ingresos', 0):.2f}")
            print_info(f"Promedio factura: ${stats.get('promedio_factura', 0):.2f}")
            
            if stats.get('facturas_por_estado'):
                print_info("Facturas por estado:")
                for estado, cantidad in stats['facturas_por_estado'].items():
                    print(f"   - {estado}: {cantidad}")
            return True
        else:
            print_error("No se pudieron obtener las estadísticas")
            return False
            
    except Exception as e:
        print_error(f"Error al obtener estadísticas: {e}")
        return False

def test_api_info():
    """Prueba el endpoint de información de la API."""
    print("\n" + "="*60)
    print("ℹ️ PRUEBA 10: Información de la API")
    print("="*60)
    
    try:
        response = requests.get(f"{API_V1}")
        print_response("Información API", response)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Información obtenida correctamente")
            print_info(f"Nombre: {data.get('name')}")
            print_info(f"Versión: {data.get('version')}")
            print_info(f"Descripción: {data.get('description')}")
            
            if data.get('endpoints'):
                print_info("Endpoints disponibles:")
                for key, value in data['endpoints'].items():
                    print(f"   - {key}: {value}")
            return True
        else:
            print_error("No se pudo obtener la información")
            return False
            
    except Exception as e:
        print_error(f"Error al obtener información: {e}")
        return False

def main():
    """Función principal que ejecuta todas las pruebas."""
    print("\n" + "="*60)
    print(f"{Colors.BOLD}🚀 PRUEBA MANUAL DE LA API REST{Colors.RESET}")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API URL: {BASE_URL}")
    print("="*60)
    
    # Verificar conexión
    if not check_connection():
        print_error("No se puede continuar sin conexión a la API")
        sys.exit(1)
    
    # Ejecutar pruebas
    resultados = []
    
    # Pruebas del sistema
    resultados.append(("Health Check", test_health()))
    resultados.append(("Root Endpoint", test_root()))
    resultados.append(("Clientes", test_clientes()))
    resultados.append(("Productos", test_productos()))
    
    # Pruebas de facturación
    factura_id = test_crear_factura()
    if factura_id:
        resultados.append(("Obtener Factura", test_obtener_factura(factura_id)))
        resultados.append(("Actualizar Estado", test_actualizar_estado(factura_id)))
        resultados.append(("Anular Factura", test_anular_factura(factura_id)))
    else:
        print_warning("Saltando pruebas de facturación (no se pudo crear factura)")
    
    # Pruebas adicionales
    resultados.append(("Estadísticas", test_estadisticas()))
    resultados.append(("Información API", test_api_info()))
    
    # Resumen de resultados
    print("\n" + "="*60)
    print(f"{Colors.BOLD}📊 RESUMEN DE RESULTADOS{Colors.RESET}")
    print("="*60)
    
    aprobadas = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    for nombre, resultado in resultados:
        if resultado:
            print(f"{Colors.GREEN}✅ APROBADA{Colors.RESET}: {nombre}")
        else:
            print(f"{Colors.RED}❌ FALLIDA{Colors.RESET}: {nombre}")
    
    print(f"\n{Colors.BOLD}Total: {aprobadas}/{total} pruebas aprobadas{Colors.RESET}")
    
    if aprobadas == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ¡TODAS LAS PRUEBAS FUERON EXITOSAS!{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️ {total - aprobadas} pruebas fallaron. Revisar logs.{Colors.RESET}")
    
    print("\n" + "="*60)
    print("✅ PRUEBA COMPLETADA")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Prueba interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)