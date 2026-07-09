"""Módulo de acciones del Execution Engine.

Cada acción del lenguaje SAF tiene un Handler independiente
en este paquete. Los handlers se registran automáticamente
en el ActionRegistry al ser importados.
"""

from .base import BaseActionHandler

__all__ = ["BaseActionHandler"]
