"""Módulo de configuración del SAP Automation Framework.

Contiene las clases responsables de la gestión, carga, validación
y persistencia de la configuración del framework.
"""

from .config_manager import ConfigManager
from .config_wizard import ConfigWizard

__all__ = ["ConfigManager", "ConfigWizard"]
