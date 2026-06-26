"""Administrador de sesiones del SAP Automation Framework.

Proporciona la clase `SessionManager` responsable de descubrir
conexiones y sesiones SAP, crear una nueva sesión exclusiva para
el Framework y gestionar su ciclo de vida.

El Framework nunca trabaja sobre sesiones del usuario.
Siempre crea su propia sesión mediante este administrador.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional, Tuple

from config.config_manager import ConfigManager
from core.sap_session import SAPSession


class SessionManager:
    """Administrador de sesiones SAP del Framework.

    Responsable de:
    - Conectarse a SAP GUI mediante el patrón oficial VBS.
    - Descubrir conexiones y sesiones existentes.
    - Crear una nueva sesión exclusiva para el Framework.
    - Mantener la referencia interna a esa sesión.
    - Cerrar únicamente la sesión creada por el Framework.

    Nunca modifica, cierra ni interfiere con sesiones del usuario.

    Parameters
    ----------
    config_manager : ConfigManager
        Gestor de configuración del Framework.
    """

    # ------------------------------------------------------------------
    def __init__(self, config_manager: ConfigManager) -> None:
        """Inicializa el administrador de sesiones.

        Parameters
        ----------
        config_manager : ConfigManager
            Instancia del gestor de configuración del Framework.
        """
        self._config_manager: ConfigManager = config_manager
        self._application: Any = None  # Objeto COM Application
        self._framework_session: Optional[SAPSession] = None

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def framework_session(self) -> Optional[SAPSession]:
        """Devuelve la sesión creada por el Framework, o ``None``."""
        return self._framework_session

    @property
    def has_framework_session(self) -> bool:
        """Indica si el Framework tiene una sesión activa."""
        return self._framework_session is not None

    # ------------------------------------------------------------------
    # Conexión COM
    # ------------------------------------------------------------------

    def _connect(self) -> Any:
        """Establece la conexión COM con SAP GUI.

        Utiliza el patrón oficial del VBS generado por SAP:
        1. ``GetObject("SAPGUI")`` → SapGuiAuto
        2. ``SapGuiAuto.GetScriptingEngine`` (propiedad) → Application

        Returns
        -------
        Any
            Objeto COM Application de SAP GUI Scripting.

        Raises
        ------
        RuntimeError
            Si no se puede establecer la conexión COM.
        """
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()

        try:
            sap_gui_auto: Any = win32com.client.GetObject("SAPGUI")
        except Exception as exc:
            raise RuntimeError(
                "No se pudo conectar con SAP GUI. "
                "Verifique que SAP Logon esté abierto."
            ) from exc

        try:
            application: Any = sap_gui_auto.GetScriptingEngine
        except Exception as exc:
            raise RuntimeError(
                "No se pudo obtener el ScriptingEngine de SAP GUI. "
                "Verifique que SAP GUI Scripting esté habilitado."
            ) from exc

        self._application = application
        return application

    # ------------------------------------------------------------------
    # Descubrimiento
    # ------------------------------------------------------------------

    def get_connection_count(self) -> int:
        """Devuelve la cantidad de conexiones SAP activas.

        Returns
        -------
        int
            Número de conexiones (0 si no hay ninguna).
        """
        app: Any = self._ensure_application()
        try:
            children: Any = app.Children
            return children.Count if children else 0
        except Exception:
            return 0

    # ------------------------------------------------------------------

    def get_session_count(self) -> int:
        """Devuelve la cantidad total de sesiones en la primera conexión.

        Returns
        -------
        int
            Número de sesiones en la primera conexión (0 si no hay).
        """
        app: Any = self._ensure_application()
        try:
            conn: Any = app.Children(0)
            children: Any = conn.Children
            return children.Count if children else 0
        except Exception:
            return 0

    # ------------------------------------------------------------------

    def get_connection_info(self) -> List[Tuple[int, str]]:
        """Obtiene información de todas las conexiones activas.

        Returns
        -------
        list[tuple[int, str]]
            Lista de tuplas ``(número, descripción)`` para cada conexión.
        """
        result: List[Tuple[int, str]] = []
        app: Any = self._ensure_application()

        try:
            children: Any = app.Children
            count: int = children.Count if children else 0
        except Exception:
            return result

        for i in range(count):
            try:
                conn: Any = children(i)
                desc: str = ""
                try:
                    desc = str(conn.Description or "")
                except Exception:
                    pass
                result.append((i + 1, desc))
            except Exception:
                pass

        return result

    # ------------------------------------------------------------------
    # Creación de sesión
    # ------------------------------------------------------------------

    def create_session(self) -> SAPSession:
        """Crea una nueva sesión SAP para uso exclusivo del Framework.

        Estrategia de captura de la nueva sesión:
        1. Registrar ``Children.Count`` antes de crear.
        2. Ejecutar ``CreateSession()`` (sin confiar en su retorno).
        3. Esperar activamente hasta que ``Children.Count`` aumente.
        4. Obtener la última sesión: ``Children(Count - 1)``.
        5. Encapsular en ``SAPSession`` y guardar referencia.

        A partir de ese momento, TODAS las operaciones usan la
        referencia COM almacenada en SAPSession. Nunca se re-busca
        por posición.

        Returns
        -------
        SAPSession
            La nueva sesión creada.

        Raises
        ------
        RuntimeError
            Si no hay conexiones, no hay sesiones, o la nueva sesión
            no aparece tras el tiempo de espera máximo.
        """
        app: Any = self._ensure_application()

        # Obtener la primera conexión
        try:
            conn: Any = app.Children(0)
        except Exception as exc:
            raise RuntimeError(
                "No se encontraron conexiones SAP activas."
            ) from exc

        # Obtener una sesión existente para crear una nueva a partir de ella
        try:
            existing: Any = conn.Children(0)
        except Exception as exc:
            raise RuntimeError(
                "No se encontraron sesiones activas en la conexión."
            ) from exc

        # ── Estrategia de captura por conteo ──
        # Paso 1: Registrar cantidad de sesiones antes de crear
        count_before: int = 0
        try:
            count_before = conn.Children.Count
        except Exception:
            count_before = 0

        # Paso 2: Ejecutar CreateSession() — NO confiar en su valor de retorno
        #    En SAP GUI Scripting, CreateSession() puede devolver:
        #    - La sesión que llamó al método (no la nueva)
        #    - None
        #    - O un objeto que no es válido como referencia a largo plazo.
        #    Por ello, IGNORAMOS su retorno y detectamos la nueva sesión
        #    observando el cambio en Children.Count.
        try:
            existing.CreateSession()
        except Exception as exc:
            raise RuntimeError(
                "No se pudo crear una nueva sesión SAP."
            ) from exc

        # Paso 3: Esperar activamente hasta que Children.Count aumente
        MAX_WAIT_SECONDS: float = 15.0
        POLL_INTERVAL: float = 0.5
        elapsed: float = 0.0
        new_com_session: Any = None

        while elapsed < MAX_WAIT_SECONDS:
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

            try:
                current_count: int = conn.Children.Count
            except Exception:
                continue

            if current_count > count_before:
                # Paso 4: La nueva sesión es la última en la colección
                try:
                    new_com_session = conn.Children(current_count - 1)
                except Exception:
                    continue
                break

        if new_com_session is None:
            raise RuntimeError(
                f"La nueva sesión no apareció tras {MAX_WAIT_SECONDS:.0f} "
                f"segundos de espera."
            )

        # Paso 5: Encapsular en SAPSession y almacenar referencia
        #    A partir de aquí, NUNCA se vuelve a buscar por posición.
        #    SAPSession._com_session es la única referencia COM utilizada.
        session: SAPSession = SAPSession(new_com_session)
        self._framework_session = session

        return session

    # ------------------------------------------------------------------
    # Cierre de sesión
    # ------------------------------------------------------------------

    def close_framework_session(self) -> bool:
        """Cierra únicamente la sesión creada por el Framework.

        Nunca cierra sesiones del usuario. Si el Framework no tiene
        una sesión activa, no hace nada.

        Returns
        -------
        bool
            ``True`` si la sesión se cerró correctamente,
            ``False`` si no había sesión que cerrar o falló el cierre.
        """
        if self._framework_session is None:
            return False

        success: bool = self._framework_session.close()
        if success:
            self._framework_session = None
        return success

    # ------------------------------------------------------------------
    # Utilidades privadas
    # ------------------------------------------------------------------

    def _ensure_application(self) -> Any:
        """Asegura que exista una conexión COM activa.

        Returns
        -------
        Any
            Objeto COM Application.

        Raises
        ------
        RuntimeError
            Si no se puede establecer la conexión.
        """
        if self._application is None:
            return self._connect()
        return self._application

    # ------------------------------------------------------------------

    def _release_com(self) -> None:
        """Libera los recursos COM de forma segura."""
        if self._application is not None:
            self._application = None
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
