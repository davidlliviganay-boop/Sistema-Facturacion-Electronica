"""
Script: run.py
Descripción: Punto de entrada para ejecutar la API REST.
Autor: David Llivigañay
Fecha: 2026-06-20
"""

import uvicorn
import sys
import os

# Agregar src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )