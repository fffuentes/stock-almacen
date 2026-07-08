"""Núcleo del SAP Automation Framework.

Contiene la clase `Framework` que orquesta el ciclo de vida principal
de la aplicación: carga de configuración, validación y presentación
del resumen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from config.config_manager import ConfigManager, FrameworkConfig


class Framework:
    """Clase principal del SAP Automation Framework.

    Orquesta la inicialización, validación de configuración y
    ejecución del flujo base. En fases futuras, esta clase será
    el punto de extensión para todas las funcionalidades.

    Parameters
    ----------
    base_dir : Path
        Directorio raíz del proyecto.
    """

    # ------------------------------------------------------------------
    def __init__(self, base_dir: Path) -> None:
        """Inicializa el framework.

        Parameters
        ----------
        base_dir : Path
            Ruta al directorio raíz del proyecto.
        """
        self._base_dir: Path = base_dir
        self._config_dir: Path = base_dir / "config"
        self._config_manager: ConfigManager = ConfigManager(self._config_dir)
        self._config: Optional[FrameworkConfig] = None

    # ------------------------------------------------------------------
    @property
    def config_manager(self) -> ConfigManager:
        """Devuelve la instancia del gestor de configuración."""
        return self._config_manager

    # ------------------------------------------------------------------
    @property
    def base_dir(self) -> Path:
        """Devuelve el directorio raíz del proyecto."""
        return self._base_dir

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Ejecuta el flujo principal del framework.

        1. Carga la configuración desde disco.
        2. Valida que la configuración sea completa.
        3. Muestra un resumen indicando que todo está correcto.
        4. Finaliza.

        Raises
        ------
        SystemExit
            Si la configuración no existe o es inválida.
        """
        # 1. Cargar configuración
        try:
            self._config = self._config_manager.load()
        except FileNotFoundError as exc:
            print(f"\n[ERROR] {exc}")
            raise SystemExit(1) from exc
        except ValueError as exc:
            print(f"\n[ERROR] Archivo de configuración corrupto: {exc}")
            raise SystemExit(1) from exc

        # 2. Validar configuración
        validation: dict = self._config_manager.validate()
        if not validation["valid"]:
            print("\n[ERROR] La configuración contiene errores:")
            for error in validation["errors"]:
                print(f"  - {error}")
            print(
                "\nEjecute 'python main.py configure' para corregir la "
                "configuración."
            )
            raise SystemExit(1)

        # 3. Mostrar resumen
        print(self._config_manager.get_summary())
        print("\n[✓] Configuración cargada correctamente.")
        print("[✓] Framework listo para la siguiente fase.\n")

        # 4. Finalizar — Fase 1 no realiza ninguna acción adicional.
