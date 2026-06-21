"""
Módulo: models.py
Descripción: Modelos de datos para el sistema de facturación.
Define las clases que representan las entidades del negocio.
Autor: David Llivigañay
Fecha: 2026-06-20
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal, getcontext, ROUND_HALF_UP
import json
import re

# Configurar precisión decimal
getcontext().prec = 10


class ValidationError(Exception):
    """Excepción personalizada para errores de validación."""
    pass


class BaseModel:
    """Clase base para todos los modelos con funcionalidad común."""
    
    def validate(self) -> bool:
        """Valida el modelo. Debe ser implementado por las subclases."""
        raise NotImplementedError("Subclases deben implementar validate()")
    
    def to_json(self) -> str:
        """Convierte el modelo a JSON."""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseModel':
        """Crea una instancia desde JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class Cliente(BaseModel):
    """Modelo de Cliente."""
    
    # Constantes para estados
    ESTADO_ACTIVO = "ACTIVO"
    ESTADO_INACTIVO = "INACTIVO"
    ESTADOS_VALIDOS = [ESTADO_ACTIVO, ESTADO_INACTIVO]
    
    def __init__(self, id_cliente: Optional[int] = None, identificacion: str = "", 
                 nombre: str = "", direccion: str = "", telefono: str = "", 
                 email: str = "", estado: str = ESTADO_ACTIVO):
        self.id_cliente = id_cliente
        self.identificacion = identificacion.strip()
        self.nombre = nombre.strip()
        self.direccion = direccion.strip()
        self.telefono = telefono.strip()
        self.email = email.strip().lower()
        self.estado = estado
        self.fecha_creacion = datetime.now()
        
        # Validación automática al crear
        self.validate()
    
    def validate(self) -> bool:
        """Valida los datos del cliente."""
        # Validar identificación (Cédula/RUC)
        if not self.identificacion:
            raise ValidationError("La identificación es requerida")
        if not (10 <= len(self.identificacion) <= 13):
            raise ValidationError("La identificación debe tener entre 10 y 13 dígitos")
        if not self.identificacion.isdigit():
            raise ValidationError("La identificación debe contener solo números")
        
        # Validar nombre
        if not self.nombre:
            raise ValidationError("El nombre es requerido")
        if len(self.nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres")
        
        # Validar email si está presente
        if self.email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, self.email):
                raise ValidationError("El formato del email no es válido")
        
        # Validar teléfono si está presente
        if self.telefono and not self.telefono.replace('+', '').replace('-', '').isdigit():
            raise ValidationError("El teléfono debe contener solo números")
        
        # Validar estado
        if self.estado not in self.ESTADOS_VALIDOS:
            raise ValidationError(f"Estado inválido. Debe ser: {', '.join(self.ESTADOS_VALIDOS)}")
        
        return True
    
    def to_dict(self) -> Dict:
        """Convierte el modelo a diccionario."""
        return {
            'id_cliente': self.id_cliente,
            'identificacion': self.identificacion,
            'nombre': self.nombre,
            'direccion': self.direccion,
            'telefono': self.telefono,
            'email': self.email,
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Cliente':
        """Crea una instancia desde un diccionario."""
        return cls(
            id_cliente=data.get('id_cliente'),
            identificacion=data.get('identificacion', ''),
            nombre=data.get('nombre', ''),
            direccion=data.get('direccion', ''),
            telefono=data.get('telefono', ''),
            email=data.get('email', ''),
            estado=data.get('estado', cls.ESTADO_ACTIVO)
        )
    
    def __str__(self) -> str:
        return f"{self.nombre} ({self.identificacion})"
    
    def __repr__(self) -> str:
        return f"<Cliente id={self.id_cliente} nombre='{self.nombre}'>"


class Producto(BaseModel):
    """Modelo de Producto."""
    
    ESTADO_ACTIVO = "ACTIVO"
    ESTADO_INACTIVO = "INACTIVO"
    ESTADOS_VALIDOS = [ESTADO_ACTIVO, ESTADO_INACTIVO]
    
    def __init__(self, id_producto: Optional[int] = None, codigo: str = "",
                 nombre: str = "", descripcion: str = "", 
                 precio_unitario: Union[Decimal, float, int] = Decimal('0.00'), 
                 stock: int = 0, id_tipo_iva: int = 1, estado: str = ESTADO_ACTIVO):
        self.id_producto = id_producto
        self.codigo = codigo.strip()
        self.nombre = nombre.strip()
        self.descripcion = descripcion.strip()
        self._precio_unitario = Decimal(str(precio_unitario))
        self.stock = max(0, stock)  # Asegurar que el stock no sea negativo
        self.id_tipo_iva = id_tipo_iva
        self.estado = estado
        self.fecha_creacion = datetime.now()
        
        # Validación automática
        self.validate()
    
    @property
    def precio_unitario(self) -> Decimal:
        """Getter para precio_unitario."""
        return self._precio_unitario
    
    @precio_unitario.setter
    def precio_unitario(self, value: Union[Decimal, float, int]):
        """Setter para precio_unitario con validación."""
        value = Decimal(str(value))
        if value < 0:
            raise ValidationError("El precio unitario no puede ser negativo")
        self._precio_unitario = value
    
    def validate(self) -> bool:
        """Valida los datos del producto."""
        # Validar código
        if not self.codigo:
            raise ValidationError("El código es requerido")
        if len(self.codigo) < 3:
            raise ValidationError("El código debe tener al menos 3 caracteres")
        
        # Validar nombre
        if not self.nombre:
            raise ValidationError("El nombre es requerido")
        if len(self.nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres")
        
        # Validar precio
        if self.precio_unitario < 0:
            raise ValidationError("El precio unitario no puede ser negativo")
        
        # Validar stock
        if self.stock < 0:
            raise ValidationError("El stock no puede ser negativo")
        
        # Validar estado
        if self.estado not in self.ESTADOS_VALIDOS:
            raise ValidationError(f"Estado inválido. Debe ser: {', '.join(self.ESTADOS_VALIDOS)}")
        
        return True
    
    def calcular_precio_con_iva(self, porcentaje_iva: Decimal) -> Decimal:
        """
        Calcula el precio con IVA incluido.
        
        Args:
            porcentaje_iva (Decimal): Porcentaje de IVA (ej. 0.12 para 12%)
        
        Returns:
            Decimal: Precio con IVA incluido
        """
        return self.precio_unitario * (Decimal('1') + porcentaje_iva)
    
    def to_dict(self) -> Dict:
        """Convierte el modelo a diccionario."""
        return {
            'id_producto': self.id_producto,
            'codigo': self.codigo,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio_unitario': str(self.precio_unitario),  # Mantener precisión
            'stock': self.stock,
            'id_tipo_iva': self.id_tipo_iva,
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Producto':
        """Crea una instancia desde un diccionario."""
        return cls(
            id_producto=data.get('id_producto'),
            codigo=data.get('codigo', ''),
            nombre=data.get('nombre', ''),
            descripcion=data.get('descripcion', ''),
            precio_unitario=Decimal(str(data.get('precio_unitario', 0))),
            stock=data.get('stock', 0),
            id_tipo_iva=data.get('id_tipo_iva', 1),
            estado=data.get('estado', cls.ESTADO_ACTIVO)
        )
    
    def __str__(self) -> str:
        return f"{self.nombre} (Cód: {self.codigo}) - ${self.precio_unitario:.2f}"
    
    def __repr__(self) -> str:
        return f"<Producto id={self.id_producto} codigo='{self.codigo}' nombre='{self.nombre}'>"


class DetalleFactura(BaseModel):
    """Modelo de Detalle de Factura."""
    
    def __init__(self, id_detalle: Optional[int] = None, 
                 id_producto: int = 0, cantidad: int = 1,
                 precio_unitario: Union[Decimal, float, int] = Decimal('0.00'),
                 descuento: Union[Decimal, float, int] = Decimal('0.00'),
                 id_tipo_iva: int = 1,
                 producto: Optional[Producto] = None):
        self.id_detalle = id_detalle
        self.id_producto = id_producto
        self.cantidad = max(1, cantidad)  # Asegurar cantidad positiva
        self._precio_unitario = Decimal(str(precio_unitario))
        self._descuento = Decimal(str(descuento))
        self.id_tipo_iva = id_tipo_iva
        self.producto = producto  # Referencia al objeto Producto (opcional)
        self.fecha_creacion = datetime.now()
        
        # Validación automática
        self.validate()
    
    @property
    def precio_unitario(self) -> Decimal:
        return self._precio_unitario
    
    @precio_unitario.setter
    def precio_unitario(self, value: Union[Decimal, float, int]):
        value = Decimal(str(value))
        if value < 0:
            raise ValidationError("El precio unitario no puede ser negativo")
        self._precio_unitario = value
    
    @property
    def descuento(self) -> Decimal:
        return self._descuento
    
    @descuento.setter
    def descuento(self, value: Union[Decimal, float, int]):
        value = Decimal(str(value))
        if value < 0:
            raise ValidationError("El descuento no puede ser negativo")
        if value > self.precio_unitario * self.cantidad:
            raise ValidationError("El descuento no puede ser mayor al subtotal")
        self._descuento = value
    
    @property
    def subtotal(self) -> Decimal:
        """Propiedad calculada: subtotal de la línea."""
        return (self.precio_unitario * self.cantidad) - self.descuento
    
    @property
    def iva(self) -> Decimal:
        """Propiedad calculada: IVA de la línea."""
        # Usar el tipo de IVA del producto si está disponible
        if self.producto and hasattr(self.producto, 'id_tipo_iva'):
            # Aquí se podría obtener el porcentaje desde la base de datos
            porcentaje = Decimal('0.12')  # Default 12%
        else:
            porcentaje = Decimal('0.12')
        return self.subtotal * porcentaje
    
    @property
    def total(self) -> Decimal:
        """Propiedad calculada: total de la línea (subtotal + IVA)."""
        return self.subtotal + self.iva
    
    def validate(self) -> bool:
        """Valida los datos del detalle."""
        if self.id_producto <= 0 and not self.producto:
            raise ValidationError("Debe especificar un producto")
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")
        if self.precio_unitario < 0:
            raise ValidationError("El precio unitario no puede ser negativo")
        if self.descuento < 0:
            raise ValidationError("El descuento no puede ser negativo")
        if self.descuento > self.precio_unitario * self.cantidad:
            raise ValidationError("El descuento no puede ser mayor al subtotal")
        return True
    
    def to_dict(self) -> Dict:
        """Convierte el modelo a diccionario."""
        return {
            'id_detalle': self.id_detalle,
            'id_producto': self.id_producto,
            'cantidad': self.cantidad,
            'precio_unitario': str(self.precio_unitario),
            'descuento': str(self.descuento),
            'subtotal': str(self.subtotal),
            'iva': str(self.iva),
            'total': str(self.total),
            'id_tipo_iva': self.id_tipo_iva,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DetalleFactura':
        """Crea una instancia desde un diccionario."""
        return cls(
            id_detalle=data.get('id_detalle'),
            id_producto=data.get('id_producto', 0),
            cantidad=data.get('cantidad', 1),
            precio_unitario=Decimal(str(data.get('precio_unitario', 0))),
            descuento=Decimal(str(data.get('descuento', 0))),
            id_tipo_iva=data.get('id_tipo_iva', 1)
        )
    
    def __str__(self) -> str:
        return f"Cant: {self.cantidad} - Subtotal: ${self.subtotal:.2f}"
    
    def __repr__(self) -> str:
        return f"<DetalleFactura id={self.id_detalle} producto={self.id_producto}>"


class Factura(BaseModel):
    """Modelo de Factura (Cabecera)."""
    
    # Constantes para estados
    ESTADO_PENDIENTE = "PENDIENTE"
    ESTADO_PAGADA = "PAGADA"
    ESTADO_ANULADA = "ANULADA"
    ESTADO_VENCIDA = "VENCIDA"
    ESTADOS_VALIDOS = [ESTADO_PENDIENTE, ESTADO_PAGADA, ESTADO_ANULADA, ESTADO_VENCIDA]
    
    def __init__(self, id_factura: Optional[int] = None, 
                 numero_factura: str = "",
                 fecha_emision: Optional[date] = None,
                 fecha_vencimiento: Optional[date] = None,
                 id_cliente: int = 0,
                 cliente: Optional[Cliente] = None,
                 estado: str = ESTADO_PENDIENTE,
                 observaciones: str = "",
                 detalles: Optional[List[DetalleFactura]] = None):
        self.id_factura = id_factura
        self.numero_factura = numero_factura.strip()
        self.fecha_emision = fecha_emision or date.today()
        self.fecha_vencimiento = fecha_vencimiento
        self.id_cliente = id_cliente
        self.cliente = cliente  # Referencia al objeto Cliente (opcional)
        self.estado = estado
        self.observaciones = observaciones.strip()
        self._detalles = detalles or []
        self.fecha_creacion = datetime.now()
        
        # Validación automática
        self.validate()
    
    @property
    def detalles(self) -> List[DetalleFactura]:
        """Getter para detalles."""
        return self._detalles
    
    @detalles.setter
    def detalles(self, value: List[DetalleFactura]):
        """Setter para detalles con validación."""
        if not isinstance(value, list):
            raise ValidationError("Los detalles deben ser una lista")
        self._detalles = value
        # Recalcular totales
        self.calcular_totales()
    
    def agregar_detalle(self, detalle: DetalleFactura):
        """Agrega un detalle a la factura."""
        if not isinstance(detalle, DetalleFactura):
            raise ValidationError("El detalle debe ser una instancia de DetalleFactura")
        self._detalles.append(detalle)
        self.calcular_totales()
    
    def eliminar_detalle(self, index: int):
        """Elimina un detalle por índice."""
        if 0 <= index < len(self._detalles):
            del self._detalles[index]
            self.calcular_totales()
        else:
            raise IndexError("Índice de detalle fuera de rango")
    
    @property
    def subtotal(self) -> Decimal:
        """Propiedad calculada: subtotal de la factura."""
        return sum(d.subtotal for d in self._detalles)
    
    @property
    def iva(self) -> Decimal:
        """Propiedad calculada: IVA total de la factura."""
        return sum(d.iva for d in self._detalles)
    
    @property
    def total(self) -> Decimal:
        """Propiedad calculada: total de la factura."""
        return self.subtotal + self.iva
    
    def calcular_totales(self) -> Dict[str, Decimal]:
        """
        Calcula y retorna los totales de la factura.
        
        Returns:
            Dict con subtotal, iva y total
        """
        return {
            'subtotal': self.subtotal,
            'iva': self.iva,
            'total': self.total
        }
    
    def validate(self) -> bool:
        """Valida los datos de la factura."""
        # Validar número de factura
        if not self.numero_factura:
            raise ValidationError("El número de factura es requerido")
        
        # Validar fechas
        if self.fecha_vencimiento and self.fecha_vencimiento < self.fecha_emision:
            raise ValidationError("La fecha de vencimiento no puede ser anterior a la fecha de emisión")
        
        # Validar cliente
        if self.id_cliente <= 0 and not self.cliente:
            raise ValidationError("Debe especificar un cliente")
        
        # Validar estado
        if self.estado not in self.ESTADOS_VALIDOS:
            raise ValidationError(f"Estado inválido. Debe ser: {', '.join(self.ESTADOS_VALIDOS)}")
        
        # Validar detalles
        if not self._detalles:
            raise ValidationError("La factura debe tener al menos un detalle")
        
        for detalle in self._detalles:
            if not isinstance(detalle, DetalleFactura):
                raise ValidationError("Todos los detalles deben ser instancias de DetalleFactura")
        
        return True
    
    def to_dict(self) -> Dict:
        """Convierte el modelo a diccionario."""
        return {
            'id_factura': self.id_factura,
            'numero_factura': self.numero_factura,
            'fecha_emision': self.fecha_emision.isoformat() if self.fecha_emision else None,
            'fecha_vencimiento': self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None,
            'id_cliente': self.id_cliente,
            'subtotal': str(self.subtotal),
            'iva': str(self.iva),
            'total': str(self.total),
            'estado': self.estado,
            'observaciones': self.observaciones,
            'detalles': [d.to_dict() for d in self._detalles],
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Factura':
        """Crea una instancia desde un diccionario."""
        detalles = []
        if 'detalles' in data:
            for detalle_data in data['detalles']:
                detalles.append(DetalleFactura.from_dict(detalle_data))
        
        return cls(
            id_factura=data.get('id_factura'),
            numero_factura=data.get('numero_factura', ''),
            fecha_emision=date.fromisoformat(data['fecha_emision']) if data.get('fecha_emision') else None,
            fecha_vencimiento=date.fromisoformat(data['fecha_vencimiento']) if data.get('fecha_vencimiento') else None,
            id_cliente=data.get('id_cliente', 0),
            estado=data.get('estado', cls.ESTADO_PENDIENTE),
            observaciones=data.get('observaciones', ''),
            detalles=detalles
        )
    
    def __str__(self) -> str:
        return f"Factura #{self.numero_factura} - Total: ${self.total:.2f}"
    
    def __repr__(self) -> str:
        return f"<Factura id={self.id_factura} numero='{self.numero_factura}'>"


class TipoIVA(BaseModel):
    """Modelo de Tipo de IVA."""
    
    ESTADO_ACTIVO = "ACTIVO"
    ESTADO_INACTIVO = "INACTIVO"
    ESTADOS_VALIDOS = [ESTADO_ACTIVO, ESTADO_INACTIVO]
    
    def __init__(self, id_tipo_iva: Optional[int] = None,
                 nombre: str = "", porcentaje: Union[Decimal, float, int] = Decimal('0.00'),
                 estado: str = ESTADO_ACTIVO):
        self.id_tipo_iva = id_tipo_iva
        self.nombre = nombre.strip()
        self._porcentaje = Decimal(str(porcentaje))
        self.estado = estado
        self.fecha_creacion = datetime.now()
        
        self.validate()
    
    @property
    def porcentaje(self) -> Decimal:
        return self._porcentaje
    
    @porcentaje.setter
    def porcentaje(self, value: Union[Decimal, float, int]):
        value = Decimal(str(value))
        if value < 0:
            raise ValidationError("El porcentaje no puede ser negativo")
        if value > 100:
            raise ValidationError("El porcentaje no puede ser mayor a 100")
        self._porcentaje = value
    
    def validate(self) -> bool:
        """Valida los datos del tipo de IVA."""
        if not self.nombre:
            raise ValidationError("El nombre es requerido")
        if self.porcentaje < 0:
            raise ValidationError("El porcentaje no puede ser negativo")
        if self.porcentaje > 100:
            raise ValidationError("El porcentaje no puede ser mayor a 100")
        if self.estado not in self.ESTADOS_VALIDOS:
            raise ValidationError(f"Estado inválido. Debe ser: {', '.join(self.ESTADOS_VALIDOS)}")
        return True
    
    def to_dict(self) -> Dict:
        """Convierte el modelo a diccionario."""
        return {
            'id_tipo_iva': self.id_tipo_iva,
            'nombre': self.nombre,
            'porcentaje': str(self.porcentaje),
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TipoIVA':
        """Crea una instancia desde un diccionario."""
        return cls(
            id_tipo_iva=data.get('id_tipo_iva'),
            nombre=data.get('nombre', ''),
            porcentaje=Decimal(str(data.get('porcentaje', 0))),
            estado=data.get('estado', cls.ESTADO_ACTIVO)
        )
    
    def __str__(self) -> str:
        return f"{self.nombre} ({self.porcentaje}%)"
    
    def __repr__(self) -> str:
        return f"<TipoIVA id={self.id_tipo_iva} nombre='{self.nombre}'>"