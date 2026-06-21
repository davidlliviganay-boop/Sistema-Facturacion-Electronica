# Sistema de Facturación Electrónica - Capa de Persistencia

## Descripción
Implementación de la capa de persistencia (Data Access Layer) para el sistema de facturación electrónica utilizando Python y MySQL.

## Características
- ✅ Patrón Singleton para conexión única
- ✅ Pool de conexiones para mejor rendimiento
- ✅ Consultas parametrizadas (prevención de inyección SQL)
- ✅ Manejo completo de excepciones
- ✅ Transacciones explícitas
- ✅ Logging integrado
- ✅ Pruebas unitarias con pytest

## Requisitos
- Python 3.8+
- MySQL 5.7+ / 8.0+
- Dependencias listadas en `requirements.txt`

## Instalación
```bash
# Clonar el repositorio
git clone [url-del-repositorio]

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales