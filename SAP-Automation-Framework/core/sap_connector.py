"""Conector SAP del SAF — garantiza que SAP Logon esté disponible.

Proporciona la clase ``SAPConnector`` cuya única responsabilidad
es verificar y garantizar que SAP Logon esté en ejecución y su
interfaz COM lista para ser utilizada por el Framework.

No inicia sesión. No abre conexiones SAP. No interactúa con
el usuario de SAP.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional

from config.config_manager import ConfigManager


class SAPConnector:
    """Garantiza que SAP Logon esté ejecutándose y listo via COM.

    Responde una única pregunta: ¿SAP Logon está listo?
    Si no lo está, lo abre y espera hasta que lo esté.

    Parameters
    ----------
    config_manager : ConfigManager
        Gestor de configuración del Framework.
    """

    # ------------------------------------------------------------------
    def __init__(self, config_manager: ConfigManager) -> None:
        """Inicializa el conector SAP.

        Parameters
        ----------
        config_manager : ConfigManager
            Instancia del gestor de configuración (debe estar cargado).
        """
        self._config_manager: ConfigManager = config_manager

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def _sap_logon_path(self) -> str:
        """Ruta al ejecutable de SAP Logon desde la configuración."""
        return self._config_manager.config.sap_logon_path

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        """Verifica si el proceso ``saplogon.exe`` está en ejecución.

        Utiliza ``tasklist`` de Windows.

        Returns
        -------
        bool
            ``True`` si el proceso existe.
        """
        try:
            result: subprocess.CompletedProcess = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq saplogon.exe"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return "saplogon.exe" in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    # ------------------------------------------------------------------

    def start(self) -> None:
        """Abre SAP Logon utilizando la ruta configurada.

        No inicia sesión. No abre conexiones. Solo lanza el ejecutable.
        """
        sap_path: str = self._sap_logon_path
        if not sap_path or not Path(sap_path).exists():
            raise RuntimeError(
                f"No se encontró SAP Logon en: {sap_path}\n"
                "Verifique la configuración: python main.py configure"
            )

        print("  Iniciando SAP Logon...")
        subprocess.Popen(
            [sap_path],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # ------------------------------------------------------------------

    def wait_ready(self, timeout: float = 60.0) -> bool:
        """Espera hasta que SAP Logon y su interfaz COM estén listos.

        La validación es doble:
        1. El proceso ``saplogon.exe`` existe.
        2. La interfaz COM ``GetObject("SAPGUI")`` está disponible.

        Parameters
        ----------
        timeout : float
            Tiempo máximo de espera en segundos.

        Returns
        -------
        bool
            ``True`` si SAP Logon está listo.
        """
        import pythoncom
        import win32com.client

        print("  Esperando SAP Logon ... ", end="", flush=True)
        start: float = time.monotonic()

        while time.monotonic() - start < timeout:
            # Verificar proceso
            if not self.is_running():
                time.sleep(0.5)
                continue

            # Verificar COM
            try:
                pythoncom.CoInitialize()
                sap_gui = win32com.client.GetObject("SAPGUI")
                _ = sap_gui.GetScriptingEngine
                elapsed: float = time.monotonic() - start
                print(f"OK ({elapsed:.1f}s)")
                return True
            except Exception:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
                time.sleep(0.5)
                continue

        print(f"TIMEOUT ({timeout:.0f}s)")
        return False

    # ------------------------------------------------------------------

    def ensure_running(self) -> bool:
        """Garantiza que SAP Logon esté listo.

        Flujo:
        1. ¿SAP Logon ya está abierto? → retornar inmediatamente.
        2. ¿No? → abrir SAP Logon → esperar disponibilidad → retornar.

        Returns
        -------
        bool
            ``True`` si SAP Logon quedó listo.
        """
        if self.is_running():
            print("SAP Logon ya estaba abierto.")
            return True

        print("SAP Logon no estaba abierto.")
        self.start()
        return self.wait_ready()
