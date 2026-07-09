"""Login Manager del SAP Automation Framework.

Proporciona la clase ``LoginManager`` que implementa el inicio de
sesión en SAP como una máquina de estados. Utiliza SAP GUI Scripting
para autenticar al usuario configurado y deja el sistema listo en
SESSION_MANAGER.

No ejecuta transacciones. No conoce workflows.
"""

from __future__ import annotations

import time
from enum import Enum, auto
from typing import Any, Optional

from config.config_manager import ConfigManager
from core.sap_waiter import SAPWaiter


# Rutas estándar de la pantalla de login SAP
_WND_MAIN: str = "wnd[0]"
_TXT_CLIENT: str = "wnd[0]/usr/txtRSYST-MANDT"
_TXT_USER: str = "wnd[0]/usr/txtRSYST-BNAME"
_PWD_PASSWORD: str = "wnd[0]/usr/pwdRSYST-BCODE"


class LoginState(Enum):
    """Estados de la máquina de login."""

    IDLE = auto()
    OPEN_CONNECTION = auto()
    WAIT_LOGIN_SCREEN = auto()
    FILL_CREDENTIALS = auto()
    SUBMIT_LOGIN = auto()
    WAIT_SESSION = auto()
    VALIDATE_SESSION = auto()
    READY = auto()
    ERROR = auto()


class LoginManager:
    """Gestiona el inicio de sesión en SAP como máquina de estados.

    Deja el Framework en estado:
    - SAP autenticado
    - SESSION_MANAGER activo
    - Listo para crear sesión del Framework

    Parameters
    ----------
    config_manager : ConfigManager
        Gestor de configuración (debe estar cargado).
    """

    # ------------------------------------------------------------------
    def __init__(self, config_manager: ConfigManager) -> None:
        """Inicializa el LoginManager.

        Parameters
        ----------
        config_manager : ConfigManager
            Instancia con la configuración cargada.
        """
        self._config: ConfigManager = config_manager
        self._state: LoginState = LoginState.IDLE
        self._sap_gui: Any = None
        self._application: Any = None
        self._connection: Any = None
        self._session_com: Any = None
        self._waiter: Optional[SAPWaiter] = None

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def state(self) -> LoginState:
        """Estado actual de la máquina."""
        return self._state

    @property
    def is_ready(self) -> bool:
        """Indica si el login fue exitoso."""
        return self._state == LoginState.READY

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    def ensure_logged_in(self) -> Any:
        """Garantiza que exista una sesión SAP autenticada.

        Si ya hay sesión autenticada, la reutiliza.
        Si no, ejecuta la máquina de estados completa.

        Returns
        -------
        Any
            Referencia COM a la sesión SAP autenticada.

        Raises
        ------
        RuntimeError
            Si el login falla.
        """
        import pythoncom
        import win32com.client

        # ¿Ya existe una sesión autenticada?
        if self._detect_existing_session():
            print("Sesión SAP ya autenticada. Reutilizando.")
            self._state = LoginState.READY
            return self._session_com

        return self.login()

    # ------------------------------------------------------------------

    def login(self) -> Any:
        """Ejecuta el login sin verificar estado previo.

        El llamante (SAPRecoveryEngine) ya determinó que se necesita
        login. Este método solo ejecuta, no decide.

        Returns
        -------
        Any
            Referencia COM a la sesión SAP autenticada.

        Raises
        ------
        RuntimeError
            Si el login falla en cualquier estado.
        """
        self._state = LoginState.IDLE

        try:
            self._state = LoginState.WAIT_LOGIN_SCREEN
            self._wait_login_screen()

            self._state = LoginState.FILL_CREDENTIALS
            self._fill_credentials()

            self._state = LoginState.SUBMIT_LOGIN
            self._submit_login()

            self._state = LoginState.WAIT_SESSION
            self._wait_session()

            self._state = LoginState.VALIDATE_SESSION
            self._validate_session()

            self._state = LoginState.READY
            print("Login exitoso. SAP listo.")
            return self._session_com

        except Exception as exc:
            self._state = LoginState.ERROR
            raise RuntimeError(
                f"Login falló en estado {self._state.name}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Detección de sesión existente
    # ------------------------------------------------------------------

    def _detect_existing_session(self) -> bool:
        """Detecta si ya existe una sesión SAP autenticada.

        Returns
        -------
        bool
            ``True`` si hay sesión válida.
        """
        try:
            import win32com.client
            self._sap_gui = win32com.client.GetObject("SAPGUI")
            self._application = self._sap_gui.GetScriptingEngine
        except Exception:
            return False

        try:
            conn = self._application.Children(0)
            session = conn.Children(0)
            sinfo = session.Info

            # Verificar que sea el sistema configurado
            system: str = str(sinfo.SystemName or "")
            expected: str = (self._config.config.system_name or self._config.config.sap_system)
            if system.upper() == expected.upper():
                self._session_com = session
                self._connection = conn
                self._waiter = SAPWaiter(session)
                return True
        except Exception:
            pass

        return False

    # ------------------------------------------------------------------
    # Estado: OPEN_CONNECTION
    # ------------------------------------------------------------------

    def _open_connection(self) -> None:
        """Abre la conexión SAP configurada usando OpenConnection."""
        import win32com.client

        self._sap_gui = win32com.client.GetObject("SAPGUI")
        self._application = self._sap_gui.GetScriptingEngine

        connection_name: str = self._config.config.sap_connection

        if not connection_name:
            raise RuntimeError(
                "No hay conexión SAP configurada. "
                "Ejecute: python main.py configure"
            )

        print(f"Abriendo conexión: {connection_name} ... ", end="", flush=True)

        try:
            self._application.OpenConnection(connection_name)
            print("OK")
        except Exception as exc:
            raise RuntimeError(
                f"La conexión '{connection_name}' no existe en SAP Logon.\n"
                f"Ejecute nuevamente: python main.py configure\n"
                f"Error COM: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Estado: WAIT_LOGIN_SCREEN
    # ------------------------------------------------------------------

    def _wait_login_screen(self) -> None:
        """Espera hasta que aparezca la pantalla de login."""
        import win32com.client
        # Obtener referencia fresca al application
        sap_gui = win32com.client.GetObject("SAPGUI")
        self._application = sap_gui.GetScriptingEngine

        # Obtener una sesión para el waiter
        try:
            conn = self._application.Children(0)
            session = conn.Children(0)
        except Exception:
            raise RuntimeError(
                "No se encontraron sesiones para la pantalla de login."
            )

        self._waiter = SAPWaiter(session)

        print("Esperando pantalla de login...")
        if not self._waiter.wait_control(_TXT_USER, timeout=30.0):
            raise RuntimeError("No apareció la pantalla de login.")

    # ------------------------------------------------------------------
    # Estado: FILL_CREDENTIALS
    # ------------------------------------------------------------------

    def _fill_credentials(self) -> None:
        """Completa mandante, usuario y contraseña."""
        cfg = self._config.config
        com = self._waiter.session_com

        print("Completando credenciales...")
        com.findById(_TXT_CLIENT).text = cfg.sap_client
        com.findById(_TXT_USER).text = cfg.sap_user
        com.findById(_PWD_PASSWORD).text = cfg.sap_password

    # ------------------------------------------------------------------
    # Estado: SUBMIT_LOGIN
    # ------------------------------------------------------------------

    def _submit_login(self) -> None:
        """Envía ENTER para iniciar sesión."""
        print("Enviando login...")
        self._waiter.session_com.findById(_WND_MAIN).sendVKey(0)

    # ------------------------------------------------------------------
    # Estado: WAIT_SESSION
    # ------------------------------------------------------------------

    def _wait_session(self) -> None:
        """Espera hasta que SAP procese el login y muestre SESSION_MANAGER."""
        print("Esperando sesión SAP...")
        if not self._waiter.wait_not_busy(timeout=30.0):
            raise RuntimeError("SAP no respondió tras el login.")
        if not self._waiter.wait_window(0, timeout=30.0):
            raise RuntimeError("No se detectó ventana principal tras login.")

        # Actualizar referencia de sesión
        try:
            conn = self._application.Children(0)
            self._session_com = conn.Children(0)
            self._waiter = SAPWaiter(self._session_com)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Estado: VALIDATE_SESSION
    # ------------------------------------------------------------------

    def _validate_session(self) -> None:
        """Valida que la sesión corresponda al sistema configurado."""
        expected: str = (self._config.config.system_name or self._config.config.sap_system).upper()

        try:
            sinfo = self._session_com.Info
            actual: str = str(sinfo.SystemName or "").upper()
        except Exception:
            raise RuntimeError("No se pudo leer SystemName de la sesión.")

        if actual != expected:
            raise RuntimeError(
                f"Validación fallida: sistema esperado={expected}, "
                f"real={actual}"
            )

        # Verificar que esté en una pantalla inicial (SESSION_MANAGER o similar)
        try:
            tx: str = str(sinfo.Transaction or "").upper()
            valid_tx = ("SESSION_MANAGER", "SAPLSMTR_NAVIGATION", "SAPLSEOD", "")
            if tx and tx not in valid_tx:
                print(f"  (Transacción inesperada: {tx}, continuando...)")
        except Exception:
            pass

        print(f"Sistema validado: {actual}")
