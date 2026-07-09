"""Módulo de diagnóstico del entorno SAP.

Proporciona la clase `SAPDiagnostics` que inspecciona el entorno SAP
de forma únicamente consultiva (solo lectura). No abre SAP, no inicia
sesión, no ejecuta transacciones ni modifica ningún estado.

Utiliza SAP GUI Scripting (COM) para obtener información de conexiones
y sesiones activas cuando SAP Logon está en ejecución.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.config_manager import ConfigManager, FrameworkConfig


# ---------------------------------------------------------------------------
# Modelos de datos para el diagnóstico
# ---------------------------------------------------------------------------

@dataclass
class SessionInfo:
    """Información de solo lectura de una sesión SAP activa.

    Attributes
    ----------
    session_number : int
        Número de la sesión dentro de su conexión (base 1).
    system : str
        Identificador del sistema SAP (ej. 'PRD').
    client : str
        Mandante/cliente SAP (ej. '600').
    user : str
        Usuario autenticado en la sesión.
    transaction : str
        Código de transacción activa (ej. 'ME23N').
    program : str
        Programa ABAP en ejecución.
    screen_number : int
        Número de dynpro actual.
    is_busy : bool
        Si la sesión está ocupada procesando.
    """

    session_number: int
    system: str = ""
    client: str = ""
    user: str = ""
    transaction: str = ""
    program: str = ""
    screen_number: int = 0
    is_busy: bool = False


@dataclass
class ConnectionInfo:
    """Información de una conexión SAP activa y sus sesiones.

    Attributes
    ----------
    connection_number : int
        Número de la conexión (base 1).
    description : str
        Descripción textual de la conexión.
    sessions : list[SessionInfo]
        Sesiones activas dentro de esta conexión.
    """

    connection_number: int
    description: str = ""
    sessions: List[SessionInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# SAPDiagnostics
# ---------------------------------------------------------------------------

class SAPDiagnostics:
    """Ejecuta el diagnóstico completo del entorno SAP.

    Realiza verificaciones en cascada sobre la configuración,
    presencia de SAP GUI, disponibilidad de SAP GUI Scripting,
    y estado de conexiones y sesiones activas. Todas las
    operaciones son de solo lectura.

    Parameters
    ----------
    config_manager : ConfigManager
        Gestor de configuración del framework.
    """

    # ------------------------------------------------------------------
    def __init__(self, config_manager: ConfigManager) -> None:
        """Inicializa el módulo de diagnóstico.

        Parameters
        ----------
        config_manager : ConfigManager
            Instancia del gestor de configuración.
        """
        self._config_manager: ConfigManager = config_manager
        self._config: Optional[FrameworkConfig] = None
        self._sap_gui: Any = None  # objeto COM SAP GUI
        self._connections: List[ConnectionInfo] = []

        # Resultados acumulados para el resumen final
        self._checks_passed: int = 0
        self._checks_failed: int = 0

    # ------------------------------------------------------------------
    # Método público principal
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """Ejecuta todas las verificaciones de diagnóstico.

        Returns
        -------
        bool
            ``True`` si el entorno está preparado para automatización.
        """
        self._print_header()

        # 1. Configuración
        config_ok: bool = self._check_configuration()

        # Si no hay configuración, no podemos continuar con el resto
        if not config_ok:
            self._print_result(False)
            return False

        # 2. SAP GUI ejecutable
        gui_ok: bool = self._check_sap_gui_executable()

        # 3. SAP Logon en ejecución
        logon_running: bool = self._check_sap_logon_process()

        # 4. SAP GUI Scripting (COM)
        scripting_ok: bool = self._check_sap_gui_scripting()

        # 5-7. Conexiones, sesiones e info (solo si COM disponible)
        if scripting_ok and logon_running:
            self._check_connections_and_sessions()

        # Resultado final
        ready: bool = config_ok and gui_ok and scripting_ok and logon_running
        self._print_result(ready)
        return ready

    # ------------------------------------------------------------------
    # Verificaciones individuales
    # ------------------------------------------------------------------

    def _check_configuration(self) -> bool:
        """Verifica la existencia y validez de la configuración.

        Returns
        -------
        bool
            ``True`` si la configuración es válida.
        """
        print("Configuración", end="")

        if not self._config_manager.exists():
            print("\r✗ Configuración inexistente")
            self._checks_failed += 1
            return False

        try:
            self._config = self._config_manager.load()
        except (FileNotFoundError, ValueError) as exc:
            print(f"\r✗ Error al cargar configuración: {exc}")
            self._checks_failed += 1
            return False

        validation: dict = self._config_manager.validate()
        if not validation["valid"]:
            print("\r✗ Configuración inválida:")
            for error in validation["errors"]:
                print(f"     - {error}")
            self._checks_failed += 1
            return False

        print("\r✓ Configuración encontrada")
        self._checks_passed += 1
        return True

    # ------------------------------------------------------------------

    def _check_sap_gui_executable(self) -> bool:
        """Verifica que el ejecutable de SAP Logon exista en la ruta configurada.

        Returns
        -------
        bool
            ``True`` si el ejecutable existe.
        """
        if self._config is None:
            return False

        sap_path: str = self._config.sap_logon_path

        if not sap_path or not Path(sap_path).exists():
            print("✗ SAP GUI no encontrado")
            self._checks_failed += 1
            return False

        print(f"✓ SAP GUI encontrado")
        print(f"  Ruta: {sap_path}")
        self._checks_passed += 1
        return True

    # ------------------------------------------------------------------

    def _check_sap_logon_process(self) -> bool:
        """Detecta si el proceso SAP Logon está en ejecución.

        Utiliza ``tasklist`` de Windows para buscar el proceso
        ``saplogon.exe`` sin interactuar con SAP.

        Returns
        -------
        bool
            ``True`` si SAP Logon está ejecutándose.
        """
        print("SAP Logon", end="")

        try:
            result: subprocess.CompletedProcess = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq saplogon.exe"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            running: bool = "saplogon.exe" in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            running = False

        if running:
            print("\rEstado: Abierto")
            self._checks_passed += 1
        else:
            print("\rEstado: Cerrado")
            self._checks_failed += 1

        return running

    # ------------------------------------------------------------------

    def _check_sap_gui_scripting(self) -> bool:
        """Comprueba la disponibilidad de SAP GUI Scripting vía COM.

        Sigue el patrón oficial generado por SAP GUI Recorder:
        1. ``GetObject("SAPGUI")`` → SapGuiAuto
        2. ``SapGuiAuto.GetScriptingEngine`` (propiedad) → Application

        No abre SAP, no inicia sesión, no ejecuta comandos.

        Returns
        -------
        bool
            ``True`` si la interfaz COM de SAP GUI Scripting está disponible.
        """
        print("SAP GUI Scripting", end="")

        # Verificar que pywin32 está instalado
        try:
            import pythoncom  # noqa: F401
            import win32com.client  # noqa: F401
        except ImportError:
            print("\r✗ SAP GUI Scripting no disponible")
            print("  (pywin32 no instalado. Ejecute: pip install pywin32)")
            self._checks_failed += 1
            return False

        # Inicializar COM y obtener objeto SAP GUI (paso 1 del VBS)
        try:
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()

            # Paso 1: GetObject("SAPGUI") → SapGuiAuto
            sap_gui_auto: Any = win32com.client.GetObject("SAPGUI")

            # Paso 2: SapGuiAuto.GetScriptingEngine (PROPIEDAD, no método)
            #   El VBS oficial usa: Set application = SapGuiAuto.GetScriptingEngine
            #   En Python COM esto es acceso a propiedad, sin paréntesis.
            self._sap_gui = sap_gui_auto.GetScriptingEngine

        except Exception:
            # Limpiar COM si falló
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
            print("\r✗ SAP GUI Scripting no disponible")
            self._checks_failed += 1
            return False

        print("\r✓ SAP GUI Scripting disponible")
        self._checks_passed += 1
        return True

    # ------------------------------------------------------------------

    def _check_connections_and_sessions(self) -> None:
        """Itera sobre las conexiones y sesiones activas de SAP.

        Utiliza el patrón oficial del VBS generado por SAP GUI Recorder:
        - ``application.Children(i)`` → conexión
        - ``connection.Children(i)`` → sesión

        Para cada sesión recupera información básica de solo lectura
        (sistema, mandante, usuario, transacción, etc.).
        """
        if self._sap_gui is None:
            return

        # self._sap_gui ahora es el objeto Application
        # (resultado de SapGuiAuto.GetScriptingEngine)
        application: Any = self._sap_gui

        # application.Children → colección de conexiones (patrón VBS)
        try:
            children: Any = application.Children
            total_connections: int = children.Count if children else 0
        except Exception:
            total_connections = 0

        print(f"\nConexiones: {total_connections}")

        if total_connections == 0:
            return

        for conn_idx in range(total_connections):
            try:
                # application.Children(i) → conexión (patrón VBS)
                conn: Any = children(conn_idx)
                conn_info: ConnectionInfo = self._build_connection_info(
                    conn, conn_idx + 1
                )
                self._connections.append(conn_info)
                self._print_connection_info(conn_info)
            except Exception:
                pass

    # ------------------------------------------------------------------

    def _build_connection_info(
        self, conn: Any, conn_number: int
    ) -> ConnectionInfo:
        """Construye el modelo `ConnectionInfo` desde un objeto COM de conexión.

        Parameters
        ----------
        conn : Any
            Objeto COM ``GuiConnection``.
        conn_number : int
            Número de conexión (base 1).

        Returns
        -------
        ConnectionInfo
            Modelo con la información de la conexión y sus sesiones.
        """
        description: str = ""
        try:
            description = conn.Description or ""
        except Exception:
            pass

        info: ConnectionInfo = ConnectionInfo(
            connection_number=conn_number,
            description=description,
        )

        # Sesiones — patrón VBS: connection.Children(i) → sesión
        try:
            sessions: Any = conn.Children
            total_sessions: int = sessions.Count if sessions else 0
        except Exception:
            total_sessions = 0

        for sess_idx in range(total_sessions):
            try:
                session: Any = sessions(sess_idx)
                session_info: SessionInfo = self._build_session_info(
                    session, sess_idx + 1
                )
                info.sessions.append(session_info)
            except Exception:
                pass

        return info

    # ------------------------------------------------------------------

    def _build_session_info(
        self, session: Any, session_number: int
    ) -> SessionInfo:
        """Construye el modelo `SessionInfo` desde un objeto COM de sesión.

        Parameters
        ----------
        session : Any
            Objeto COM ``GuiSession``.
        session_number : int
            Número de sesión (base 1).

        Returns
        -------
        SessionInfo
            Modelo con la información de solo lectura de la sesión.
        """
        info: SessionInfo = SessionInfo(session_number=session_number)

        try:
            sinfo: Any = session.Info
            if sinfo:
                info.system = str(sinfo.SystemName or "")
                info.client = str(sinfo.Client or "")
                info.user = str(sinfo.User or "")
                info.transaction = str(sinfo.Transaction or "")
                info.program = str(sinfo.Program or "")
                try:
                    info.screen_number = int(sinfo.ScreenNumber or 0)
                except (ValueError, TypeError):
                    info.screen_number = 0
        except Exception:
            pass

        try:
            info.is_busy = bool(session.Busy)
        except Exception:
            info.is_busy = False

        return info

    # ------------------------------------------------------------------
    # Métodos de presentación
    # ------------------------------------------------------------------

    def _print_connection_info(self, conn_info: ConnectionInfo) -> None:
        """Imprime la información de una conexión y sus sesiones.

        Parameters
        ----------
        conn_info : ConnectionInfo
            Información de la conexión a imprimir.
        """
        print("-" * 42)
        print(f"Conexión {conn_info.connection_number}")
        if conn_info.description:
            print(f"  Descripción: {conn_info.description}")
        print(f"  Sesiones: {len(conn_info.sessions)}")

        for session in conn_info.sessions:
            print("-" * 42)
            print(f"  Sesión {session.session_number}")
            if session.system:
                print(f"    Sistema:      {session.system}")
            if session.client:
                print(f"    Mandante:     {session.client}")
            if session.user:
                print(f"    Usuario:      {session.user}")
            if session.transaction:
                print(f"    Transacción:  {session.transaction}")
            if session.program:
                print(f"    Programa:     {session.program}")
            if session.screen_number:
                print(f"    Dynpro:       {session.screen_number}")
            estado: str = "Ocupada" if session.is_busy else "Disponible"
            print(f"    Estado:       {estado}")

    # ------------------------------------------------------------------

    @staticmethod
    def _print_header() -> None:
        """Imprime la cabecera del diagnóstico."""
        print()
        print("=" * 42)
        print("  SAP Automation Framework")
        print("  Diagnóstico")
        print("=" * 42)
        print()

    # ------------------------------------------------------------------

    def _print_result(self, ready: bool) -> None:
        """Imprime el resultado final del diagnóstico.

        Parameters
        ----------
        ready : bool
            ``True`` si el entorno está listo para automatización.
        """
        print()
        print("=" * 42)
        print("  Resultado")
        if ready:
            print("  Entorno preparado para automatización.")
        else:
            print("  El entorno NO está preparado.")
            print(f"  Verificaciones superadas: {self._checks_passed}")
            print(f"  Verificaciones fallidas: {self._checks_failed}")
        print("=" * 42)
        print()

        # Liberar COM al finalizar
        self._release_com()

    # ------------------------------------------------------------------

    def _release_com(self) -> None:
        """Libera la interfaz COM de forma segura."""
        if self._sap_gui is not None:
            try:
                self._sap_gui = None
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
