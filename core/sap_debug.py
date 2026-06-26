"""Modo de diagnóstico detallado (verbose) usando el patrón oficial SAP.

Proporciona la clase `SAPDebug` que recorre la jerarquía COM de
SAP GUI Scripting utilizando exactamente el mismo patrón que el
grabador oficial de SAP GUI genera en sus archivos .VBS.

Totalmente de solo lectura. No abre SAP, no inicia sesión,
no ejecuta transacciones.
"""

from __future__ import annotations

import traceback
from typing import Any, List, Optional

from config.config_manager import ConfigManager


class SAPDebug:
    """Explorador detallado del árbol COM usando el patrón oficial SAP.

    Recorre la jerarquía completa de objetos COM siguiendo la misma
    secuencia del grabador VBS de SAP GUI, mostrando en cada paso
    el objeto encontrado y cualquier excepción.

    Patrón oficial (extraído del .VBS generado por SAP):
        1. GetObject("SAPGUI")              → SapGuiAuto
        2. SapGuiAuto.GetScriptingEngine    → Application  (propiedad)
        3. Application.Children(i)          → Connection
        4. Connection.Children(j)           → Session
        5. Session.Info                     → Info de sesión (solo lectura)

    Parameters
    ----------
    config_manager : ConfigManager
        Gestor de configuración del framework.
    """

    _SEPARATOR: str = "-" * 58

    # ------------------------------------------------------------------
    def __init__(self, config_manager: ConfigManager) -> None:
        """Inicializa el explorador verbose.

        Parameters
        ----------
        config_manager : ConfigManager
            Instancia del gestor de configuración.
        """
        self._config_manager: ConfigManager = config_manager

    # ------------------------------------------------------------------
    # Método público principal
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Ejecuta la exploración completa usando el patrón oficial SAP."""
        self._print_header()

        # Verificar pywin32
        if not self._ensure_pywin32():
            return

        # Paso 1: GetObject("SAPGUI") → SapGuiAuto
        sap_gui_auto: Optional[Any] = self._step_get_sap_gui()
        if sap_gui_auto is None:
            return

        # Paso 2: SapGuiAuto.GetScriptingEngine → Application
        application: Optional[Any] = self._step_get_scripting_engine(
            sap_gui_auto
        )
        if application is None:
            return

        # Paso 3: Application.Children → Conexiones
        connections: Optional[Any] = self._step_get_connections(application)

        # Paso 4-5: Iterar conexiones y sesiones
        if connections is not None:
            self._step_iterate_connections(connections)

        # Liberar COM
        self._release_com()
        self._print_footer()

    # ------------------------------------------------------------------
    # Paso 1: GetObject("SAPGUI") → SapGuiAuto
    # ------------------------------------------------------------------

    def _ensure_pywin32(self) -> bool:
        """Verifica que pywin32 esté instalado.

        Returns
        -------
        bool
            ``True`` si la dependencia está disponible.
        """
        print("Verificando pywin32...", end=" ")
        try:
            import pythoncom  # noqa: F401
            import win32com.client  # noqa: F401
            print("✓ Disponible")
            return True
        except ImportError as exc:
            print(f"✗ No disponible")
            print(f"  Excepción: {type(exc).__name__}: {exc}")
            print("  Instale con: pip install pywin32")
            return False

    # ------------------------------------------------------------------

    def _step_get_sap_gui(self) -> Optional[Any]:
        """Paso 1 del patrón VBS: GetObject("SAPGUI") → SapGuiAuto.

        Returns
        -------
        Any or None
            Objeto SapGuiAuto, o ``None`` si falla.
        """
        import pythoncom
        import win32com.client

        print()
        print(self._SEPARATOR)
        print('Paso 1: GetObject("SAPGUI")')
        print('  VBS: Set SapGuiAuto = GetObject("SAPGUI")')
        print(self._SEPARATOR)

        pythoncom.CoInitialize()

        try:
            sap_gui_auto = win32com.client.GetObject("SAPGUI")
            print("  ✓ SapGuiAuto obtenido")
            print(f"  Tipo:  {type(sap_gui_auto).__name__}")
            print(f"  repr:  {sap_gui_auto!r}")
            return sap_gui_auto
        except Exception:
            print('  ✗ Falló GetObject("SAPGUI")')
            print("  Excepción completa:")
            traceback.print_exc()
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
            return None

    # ------------------------------------------------------------------
    # Paso 2: SapGuiAuto.GetScriptingEngine → Application
    # ------------------------------------------------------------------

    def _step_get_scripting_engine(self, sap_gui_auto: Any) -> Optional[Any]:
        """Paso 2 del patrón VBS: SapGuiAuto.GetScriptingEngine → Application.

        ATENCIÓN: En el VBS de SAP esto es acceso a PROPIEDAD, no método.
        ``SapGuiAuto.GetScriptingEngine`` (sin paréntesis).

        Parameters
        ----------
        sap_gui_auto : Any
            Objeto SapGuiAuto obtenido en el paso 1.

        Returns
        -------
        Any or None
            Objeto Application, o ``None`` si falla.
        """
        print()
        print(self._SEPARATOR)
        print("Paso 2: SapGuiAuto.GetScriptingEngine  (PROPIEDAD)")
        print("  VBS: Set application = SapGuiAuto.GetScriptingEngine")
        print(self._SEPARATOR)

        # Intento 1: Acceso como propiedad (sin paréntesis) — patrón VBS
        try:
            application = sap_gui_auto.GetScriptingEngine
            print("  ✓ Application obtenido (vía propiedad GetScriptingEngine)")
            print(f"  Tipo:  {type(application).__name__}")
            print(f"  repr:  {application!r}")
            return application
        except Exception:
            print("  ✗ GetScriptingEngine como propiedad falló")
            print("  Excepción completa:")
            traceback.print_exc()

        # Intento 2: Acceso como método (con paréntesis) — alternativa
        print("\n  Intentando como método: GetScriptingEngine()")
        try:
            application = sap_gui_auto.GetScriptingEngine()
            print("  ✓ Application obtenido (vía método GetScriptingEngine())")
            print(f"  Tipo:  {type(application).__name__}")
            print(f"  repr:  {application!r}")
            return application
        except Exception:
            print("  ✗ GetScriptingEngine() como método también falló")
            print("  Excepción completa:")
            traceback.print_exc()

        return None

    # ------------------------------------------------------------------
    # Paso 3: Application.Children → Conexiones
    # ------------------------------------------------------------------

    def _step_get_connections(self, application: Any) -> Optional[Any]:
        """Paso 3 del patrón VBS: Application.Children → colección de conexiones.

        Parameters
        ----------
        application : Any
            Objeto Application obtenido en el paso 2.

        Returns
        -------
        Any or None
            Colección Children, o ``None`` si falla.
        """
        print()
        print(self._SEPARATOR)
        print("Paso 3: Application.Children")
        print("  VBS: Set connection = application.Children(0)")
        print(self._SEPARATOR)

        try:
            children = application.Children
            count = children.Count
            print("  ✓ Children obtenido")
            print(f"  Tipo:  {type(children).__name__}")
            print(f"  Count: {count}")
            return children
        except Exception:
            print("  ✗ Falló Application.Children")
            print("  Excepción completa:")
            traceback.print_exc()
            return None

    # ------------------------------------------------------------------
    # Paso 4-5: Iterar conexiones y sus sesiones
    # ------------------------------------------------------------------

    def _step_iterate_connections(self, children: Any) -> None:
        """Itera las conexiones y sus sesiones usando el patrón VBS.

        Paso 4: ``application.Children(i)`` → Connection
        Paso 5: ``connection.Children(j)`` → Session

        Parameters
        ----------
        children : Any
            Colección Children del Application.
        """
        try:
            count: int = children.Count
        except Exception:
            print("\n  ✗ No se pudo obtener Count de Children")
            return

        if count == 0:
            print("\n  (Count = 0, no hay conexiones para iterar)")
            return

        print(f"\n  Iterando {count} conexiones...")

        for conn_idx in range(count):
            print()
            print("  " + "-" * 50)
            print(f"  Conexión {conn_idx + 1} de {count}")
            print(f"  VBS: Set connection = application.Children({conn_idx})")
            print("  " + "-" * 50)

            try:
                connection = children(conn_idx)
                print("  ✓ Conexión obtenida")
                print(f"  Tipo: {type(connection).__name__}")
                print(f"  repr: {connection!r}")

                # Mostrar Description si existe
                try:
                    desc = connection.Description
                    print(f"  Description: {desc}")
                except Exception:
                    print("  Description: ✗ No disponible")
                    traceback.print_exc()

                # Obtener sesiones de esta conexión (patrón VBS)
                self._step_iterate_sessions(connection, conn_idx + 1)

            except Exception:
                print(f"  ✗ Error al acceder a Children({conn_idx})")
                traceback.print_exc()

    # ------------------------------------------------------------------

    def _step_iterate_sessions(
        self, connection: Any, conn_number: int
    ) -> None:
        """Itera las sesiones de una conexión usando el patrón VBS.

        Patrón VBS: ``connection.Children(j)`` → Session

        Parameters
        ----------
        connection : Any
            Objeto Connection.
        conn_number : int
            Número de conexión (para mostrar).
        """
        print(f"\n    --- Sesiones de Conexión {conn_number} ---")
        print("    VBS: Set session = connection.Children(0)")

        # Obtener colección Children de la conexión (son las sesiones)
        try:
            sessions = connection.Children
            scount = sessions.Count
            print("    ✓ connection.Children obtenido")
            print(f"    Count: {scount}")
        except Exception:
            print("    ✗ Falló connection.Children")
            print("    Excepción completa:")
            traceback.print_exc()

            # Intentar alternativa: connection.Sessions
            print("\n    Intentando alternativa: connection.Sessions")
            try:
                sessions = connection.Sessions
                scount = sessions.Count
                print("    ✓ connection.Sessions disponible")
                print(f"    Count: {scount}")
            except Exception:
                print("    ✗ connection.Sessions también falló")
                traceback.print_exc()
                return

        if scount == 0:
            print("    (Count = 0, no hay sesiones en esta conexión)")
            return

        for s_idx in range(scount):
            print(f"\n    --- Sesión {s_idx + 1} de {scount} ---")

            try:
                session = sessions(s_idx)
                print("    ✓ Sesión obtenida")
                print(f"    Tipo: {type(session).__name__}")
                print(f"    repr: {session!r}")

                # Explorar Info de sesión (solo lectura)
                self._step_session_info(session, s_idx + 1)

            except Exception:
                print(f"    ✗ Error al acceder a la sesión {s_idx}")
                traceback.print_exc()

    # ------------------------------------------------------------------
    # Paso 5b: Session.Info
    # ------------------------------------------------------------------

    def _step_session_info(self, session: Any, session_number: int) -> None:
        """Lee la información de solo lectura de una sesión SAP.

        Patrón VBS: se accede a ``session.findById(...)`` para UI,
        y a ``session.Info`` para metadatos.

        Parameters
        ----------
        session : Any
            Objeto Session.
        session_number : int
            Número de sesión (para mostrar).
        """
        print(f"\n      --- Info de Sesión {session_number} ---")
        print("      VBS: session.Info.SystemName / .Client / .User / .Transaction")

        try:
            sinfo = session.Info
            print("      ✓ session.Info obtenido")
            print(f"      Tipo: {type(sinfo).__name__}")
        except Exception:
            print("      ✗ session.Info no disponible")
            traceback.print_exc()
            return

        # Propiedades estándar de Session.Info (documentadas por SAP)
        info_props: List[str] = [
            "SystemName",
            "Client",
            "User",
            "Transaction",
            "Program",
            "ScreenNumber",
            "Language",
            "Application",
            "CodePage",
            "GuiCodepage",
            "I18NMode",
            "IsLowSpeedConnection",
        ]

        for prop in info_props:
            try:
                value = getattr(sinfo, prop)
                print(f"      .Info.{prop} = {value!r}")
            except Exception:
                print(f"      .Info.{prop} = ✗")

        # Estado de la sesión
        print()
        try:
            busy = session.Busy
            estado = "Ocupada" if busy else "Disponible"
            print(f"      .Busy = {busy} ({estado})")
        except Exception:
            print("      .Busy = ✗")

        try:
            session_id = session.ID
            print(f"      .ID = {session_id!r}")
        except Exception:
            print("      .ID = ✗")

    # ------------------------------------------------------------------
    # Presentación
    # ------------------------------------------------------------------

    @staticmethod
    def _print_header() -> None:
        """Imprime la cabecera del modo verbose."""
        print()
        print("=" * 58)
        print("  SAP Automation Framework")
        print("  Diagnóstico Verbose — Patrón oficial SAP (.VBS)")
        print("=" * 58)
        print()
        print("Este modo recorre la jerarquía COM de SAP GUI Scripting")
        print("utilizando exactamente el mismo patrón del grabador VBS")
        print("oficial de SAP:")
        print()
        print('  1. GetObject("SAPGUI")           → SapGuiAuto')
        print("  2. SapGuiAuto.GetScriptingEngine  → Application (propiedad)")
        print("  3. Application.Children(i)        → Connection")
        print("  4. Connection.Children(j)         → Session")
        print("  5. Session.Info                   → Info (solo lectura)")
        print()
        print("Todas las operaciones son de SOLO LECTURA.")
        print()

    # ------------------------------------------------------------------

    @staticmethod
    def _print_footer() -> None:
        """Imprime el pie del modo verbose."""
        print()
        print("=" * 58)
        print("  Fin del diagnóstico verbose.")
        print("=" * 58)
        print()

    # ------------------------------------------------------------------

    @staticmethod
    def _release_com() -> None:
        """Libera los recursos COM de forma segura."""
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass
