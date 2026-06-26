"""Asistente interactivo de configuración por consola.

Proporciona la clase `ConfigWizard` que guía al usuario paso a paso
para configurar el SAP Automation Framework mediante una interfaz
de línea de comandos.
"""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path
from typing import Optional, List

from .config_manager import ConfigManager, FrameworkConfig


# Rutas comunes donde suele instalarse SAP Logon en Windows
_SAP_LOGON_COMMON_PATHS: List[str] = [
    r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe",
    r"C:\Program Files\SAP\FrontEnd\SAPgui\saplogon.exe",
]


class ConfigWizard:
    """Asistente de configuración interactivo por consola.

    Guía al usuario para recolectar todos los parámetros necesarios
    y los persiste mediante `ConfigManager`.

    Parameters
    ----------
    config_manager : ConfigManager
        Instancia del gestor de configuración donde se guardarán los datos.
    """

    # ------------------------------------------------------------------
    def __init__(self, config_manager: ConfigManager) -> None:
        """Inicializa el asistente de configuración.

        Parameters
        ----------
        config_manager : ConfigManager
            Gestor de configuración a utilizar para persistir los datos.
        """
        self._manager: ConfigManager = config_manager

    # ------------------------------------------------------------------
    def run(self) -> FrameworkConfig:
        """Ejecuta el asistente de configuración completo.

        Returns
        -------
        FrameworkConfig
            Configuración recolectada y persistida.
        """
        self._print_header()
        config: FrameworkConfig = FrameworkConfig()

        config.sap_logon_path = self._ask_sap_logon_path()
        config.sap_system = self._ask_required("Sistema SAP", "PRD")
        config.sap_client = self._ask_required("Cliente SAP", "100")
        config.sap_language = self._ask_required("Idioma SAP", "ES")
        config.sap_user = self._ask_required("Usuario SAP")
        config.sap_password = self._ask_password()
        config.exports_path = self._ask_path("Ruta de exportaciones")
        config.git_repo_path = self._ask_path("Ruta del repositorio Git")

        self._manager.save(config)
        self._print_success(config)
        return config

    # ------------------------------------------------------------------
    @staticmethod
    def _detect_sap_logon() -> Optional[str]:
        """Intenta detectar automáticamente la ruta de SAP Logon.

        Busca en las ubicaciones comunes de instalación en Windows.

        Returns
        -------
        str or None
            Ruta encontrada, o ``None`` si no se detectó.
        """
        for candidate in _SAP_LOGON_COMMON_PATHS:
            if os.path.isfile(candidate):
                return candidate
        return None

    # ------------------------------------------------------------------
    def _ask_sap_logon_path(self) -> str:
        """Solicita la ruta de SAP Logon, con detección automática.

        Returns
        -------
        str
            Ruta validada al ejecutable de SAP Logon.
        """
        detected: Optional[str] = self._detect_sap_logon()

        if detected:
            print(f"\n[✓] SAP Logon detectado automáticamente en:")
            print(f"    {detected}")
            answer: str = input("¿Usar esta ruta? [S/n]: ").strip().lower()
            if answer in ("", "s", "y", "si", "yes"):
                return detected

        return self._ask_path("Ruta de SAP Logon (saplogon.exe)")

    # ------------------------------------------------------------------
    @staticmethod
    def _ask_required(label: str, default: Optional[str] = None) -> str:
        """Solicita un valor obligatorio al usuario.

        Parameters
        ----------
        label : str
            Etiqueta descriptiva del campo.
        default : str, optional
            Valor por defecto si el usuario no ingresa nada.

        Returns
        -------
        str
            Valor ingresado (nunca vacío).
        """
        prompt: str = f"{label}"
        if default:
            prompt += f" [{default}]"
        prompt += ": "

        while True:
            value: str = input(prompt).strip()
            if not value and default:
                value = default
            if value:
                return value
            print(f"[!] El campo '{label}' es obligatorio. Intente nuevamente.")

    # ------------------------------------------------------------------
    @staticmethod
    def _ask_password() -> str:
        """Solicita la contraseña de forma segura (sin eco en pantalla).

        Returns
        -------
        str
            Contraseña ingresada (nunca vacía).
        """
        while True:
            pwd: str = getpass.getpass("Contraseña SAP: ").strip()
            if pwd:
                return pwd
            print("[!] La contraseña no puede estar vacía.")

    # ------------------------------------------------------------------
    @staticmethod
    def _ask_path(label: str) -> str:
        """Solicita una ruta de directorio válida al usuario.

        Parameters
        ----------
        label : str
            Etiqueta descriptiva del campo.

        Returns
        -------
        str
            Ruta absoluta ingresada.
        """
        while True:
            raw: str = input(f"{label}: ").strip()
            if not raw:
                print(f"[!] El campo '{label}' es obligatorio.")
                continue

            expanded: str = os.path.expandvars(os.path.expanduser(raw))
            path: Path = Path(expanded)

            # Si no existe, preguntar si se desea crear
            if not path.exists():
                ans: str = input(
                    f"    La ruta '{expanded}' no existe. ¿Crearla? [S/n]: "
                ).strip().lower()
                if ans in ("", "s", "y", "si", "yes"):
                    path.mkdir(parents=True, exist_ok=True)
                    print(f"    [✓] Directorio creado: {expanded}")
                else:
                    continue

            return str(path.resolve())

    # ------------------------------------------------------------------
    @staticmethod
    def _print_header() -> None:
        """Imprime la cabecera del asistente de configuración."""
        print()
        print("=" * 55)
        print("  SAP Automation Framework (SAF)")
        print("  Asistente de Configuración")
        print("=" * 55)
        print()
        print("A continuación se solicitarán los parámetros necesarios")
        print("para configurar el framework.")
        print("Presione Ctrl+C en cualquier momento para cancelar.")
        print()

    # ------------------------------------------------------------------
    @staticmethod
    def _print_success(config: FrameworkConfig) -> None:
        """Imprime el mensaje de éxito tras la configuración.

        Parameters
        ----------
        config : FrameworkConfig
            Configuración recién guardada.
        """
        print()
        print("=" * 55)
        print("  [✓] Configuración guardada exitosamente.")
        print("=" * 55)
        print(f"  Archivo: settings.json")
        print(f"  Sistema: {config.sap_system}")
        print(f"  Cliente: {config.sap_client}")
        print(f"  Usuario: {config.sap_user}")
        print("=" * 55)
        print()
