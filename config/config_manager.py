"""Gestor de configuración del SAP Automation Framework.

Proporciona la clase `ConfigManager` responsable de cargar, validar,
guardar y exponer la configuración del framework desde y hacia
archivos internos del proyecto. El usuario nunca debe editar
estos archivos manualmente.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Modelo de datos de configuración
# ---------------------------------------------------------------------------

@dataclass
class FrameworkConfig:
    """Modelo de datos que representa la configuración completa del framework.

    Attributes
    ----------
    sap_logon_path : str
        Ruta absoluta al ejecutable de SAP Logon (saplogon.exe).
    sap_system : str
        Identificador del sistema SAP (ej. 'PRD', 'QAS').
    sap_client : str
        Mandante/cliente SAP (ej. '100', '200').
    sap_language : str
        Código de idioma para la sesión SAP (ej. 'ES', 'EN').
    sap_user : str
        Nombre de usuario SAP.
    sap_password : str
        Contraseña del usuario SAP.
    exports_path : str
        Ruta absoluta al directorio de exportaciones.
    git_repo_path : str
        Ruta absoluta al repositorio Git asociado.
    """

    sap_logon_path: str = ""
    sap_system: str = ""
    sap_client: str = ""
    sap_language: str = "ES"
    sap_user: str = ""
    sap_password: str = ""
    exports_path: str = ""
    git_repo_path: str = ""


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

class ConfigManager:
    """Gestiona la carga, validación y persistencia de la configuración.

    La configuración se almacena en un archivo JSON dentro del directorio
    ``config/`` del proyecto. Esta clase es la única vía para leer o
    escribir dicha configuración.

    Parameters
    ----------
    config_dir : Path
        Ruta al directorio que contiene los archivos de configuración.
    config_filename : str, optional
        Nombre del archivo de configuración (por defecto ``settings.json``).
    """

    DEFAULT_FILENAME: str = "settings.json"

    # ------------------------------------------------------------------
    def __init__(self, config_dir: Path, config_filename: Optional[str] = None) -> None:
        """Inicializa el gestor de configuración.

        Parameters
        ----------
        config_dir : Path
            Directorio donde se almacena el archivo de configuración.
        config_filename : str, optional
            Nombre del archivo (por defecto ``settings.json``).
        """
        self._config_dir: Path = config_dir
        self._filename: str = config_filename or self.DEFAULT_FILENAME
        self._config: Optional[FrameworkConfig] = None

    # ------------------------------------------------------------------
    @property
    def config_file_path(self) -> Path:
        """Ruta completa al archivo de configuración."""
        return self._config_dir / self._filename

    # ------------------------------------------------------------------
    @property
    def config(self) -> FrameworkConfig:
        """Devuelve la configuración cargada.

        Raises
        ------
        RuntimeError
            Si se intenta acceder a la configuración sin haberla cargado antes.
        """
        if self._config is None:
            raise RuntimeError(
                "La configuración no ha sido cargada. "
                "Ejecute load() primero."
            )
        return self._config

    # ------------------------------------------------------------------
    def exists(self) -> bool:
        """Indica si el archivo de configuración existe en disco."""
        return self.config_file_path.exists()

    # ------------------------------------------------------------------
    def load(self) -> FrameworkConfig:
        """Carga la configuración desde el archivo JSON.

        Returns
        -------
        FrameworkConfig
            Objeto con la configuración cargada.

        Raises
        ------
        FileNotFoundError
            Si el archivo de configuración no existe.
        ValueError
            Si el archivo JSON tiene un formato inválido.
        """
        if not self.exists():
            raise FileNotFoundError(
                f"Archivo de configuración no encontrado: {self.config_file_path}\n"
                f"Ejecute 'python main.py configure' para crear la configuración."
            )

        with open(self.config_file_path, "r", encoding="utf-8") as fh:
            data: dict = json.load(fh)

        self._config = FrameworkConfig(**data)
        return self._config

    # ------------------------------------------------------------------
    def save(self, config: FrameworkConfig) -> None:
        """Guarda la configuración en el archivo JSON.

        Parameters
        ----------
        config : FrameworkConfig
            Objeto de configuración a persistir.
        """
        self._config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_file_path, "w", encoding="utf-8") as fh:
            json.dump(asdict(config), fh, indent=2, ensure_ascii=False)

        self._config = config

    # ------------------------------------------------------------------
    def validate(self) -> dict:
        """Valida que la configuración cargada sea completa y coherente.

        Returns
        -------
        dict
            Diccionario con dos claves:
            - ``valid`` (bool): ``True`` si la configuración es válida.
            - ``errors`` (list[str]): Lista de mensajes de error (vacía si es válida).
        """
        errors: list[str] = []

        if self._config is None:
            errors.append("No hay configuración cargada.")
            return {"valid": False, "errors": errors}

        cfg: FrameworkConfig = self._config

        # Validaciones de campos obligatorios
        if not cfg.sap_logon_path.strip():
            errors.append("Ruta de SAP Logon es obligatoria.")
        elif not Path(cfg.sap_logon_path).exists():
            errors.append(
                f"Ruta de SAP Logon no encontrada: {cfg.sap_logon_path}"
            )

        if not cfg.sap_system.strip():
            errors.append("Sistema SAP es obligatorio.")

        if not cfg.sap_client.strip():
            errors.append("Cliente SAP es obligatorio.")

        if not cfg.sap_language.strip():
            errors.append("Idioma SAP es obligatorio.")

        if not cfg.sap_user.strip():
            errors.append("Usuario SAP es obligatorio.")

        if not cfg.sap_password.strip():
            errors.append("Contraseña SAP es obligatoria.")

        if not cfg.exports_path.strip():
            errors.append("Ruta de exportaciones es obligatoria.")

        if not cfg.git_repo_path.strip():
            errors.append("Ruta del repositorio Git es obligatoria.")

        return {"valid": len(errors) == 0, "errors": errors}

    # ------------------------------------------------------------------
    def get_summary(self) -> str:
        """Genera un resumen legible de la configuración cargada.

        Returns
        -------
        str
            Resumen en texto plano de la configuración (sin mostrar contraseña).
        """
        if self._config is None:
            return "No hay configuración cargada."

        cfg: FrameworkConfig = self._config

        lines: list[str] = [
            "=" * 55,
            "  CONFIGURACIÓN SAF",
            "=" * 55,
            f"  SAP Logon        : {cfg.sap_logon_path}",
            f"  Sistema SAP      : {cfg.sap_system}",
            f"  Cliente          : {cfg.sap_client}",
            f"  Idioma           : {cfg.sap_language}",
            f"  Usuario          : {cfg.sap_user}",
            f"  Contraseña       : {'*' * len(cfg.sap_password)}",
            f"  Exportaciones    : {cfg.exports_path}",
            f"  Repositorio Git  : {cfg.git_repo_path}",
            "=" * 55,
        ]

        return "\n".join(lines)
