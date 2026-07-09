"""Smart Wait Engine del SAP Automation Framework.

Proporciona la clase ``SAPWaiter`` que reemplaza ``time.sleep`` fijos
por esperas activas basadas en el estado real de SAP GUI Scripting.
Utiliza polling corto (~100 ms) con timeouts configurables.
"""

from __future__ import annotations

import time
from typing import Any, Callable


class SAPWaiter:
    """Espera inteligente basada en el estado real de SAP.

    Realiza polling sobre la referencia COM de la sesión SAP.
    Cada método verifica una condición específica hasta que se
    cumpla o expire el timeout.

    Parameters
    ----------
    session_com : Any
        Referencia COM a la sesión SAP (``GuiSession``).
    poll_interval : float
        Intervalo entre verificaciones en segundos (default 0.1).
    default_timeout : float
        Tiempo máximo de espera por defecto en segundos (default 30).
    """

    # ------------------------------------------------------------------
    def __init__(
        self,
        session_com: Any,
        poll_interval: float = 0.1,
        default_timeout: float = 30.0,
    ) -> None:
        self._com: Any = session_com
        self._poll_interval: float = poll_interval
        self._default_timeout: float = default_timeout

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def session_com(self) -> Any:
        """Referencia COM a la sesión SAP."""
        return self._com

    # ------------------------------------------------------------------
    # Método genérico
    # ------------------------------------------------------------------

    def wait_until(
        self,
        condition: Callable[[], bool],
        timeout: float = -1.0,
        description: str = "",
    ) -> bool:
        """Espera hasta que una condición sea verdadera.

        Método base usado internamente por todos los demás.

        Parameters
        ----------
        condition : callable
            Función sin argumentos que retorna ``True`` al cumplirse.
        timeout : float
            Tiempo máximo en segundos. Default si es negativo.
        description : str
            Descripción para mensajes de log.

        Returns
        -------
        bool
            ``True`` si se cumplió, ``False`` si expiró el timeout.
        """
        if timeout < 0:
            timeout = self._default_timeout

        label: str = description or "condición"
        print(f"  Esperando {label} ... ", end="", flush=True)

        start: float = time.monotonic()

        while time.monotonic() - start < timeout:
            try:
                if condition():
                    elapsed: float = time.monotonic() - start
                    print(f"OK ({elapsed:.1f}s)")
                    return True
            except Exception:
                pass  # Puede fallar mientras SAP procesa

            time.sleep(self._poll_interval)

        elapsed = time.monotonic() - start
        print(f"TIMEOUT ({elapsed:.1f}s)")
        return False

    # ------------------------------------------------------------------
    # Métodos específicos
    # ------------------------------------------------------------------

    def wait_not_busy(self, timeout: float = -1.0) -> bool:
        """Espera hasta que SAP no esté ocupado (``session.Busy == False``).

        Parameters
        ----------
        timeout : float
            Tiempo máximo de espera.

        Returns
        -------
        bool
            ``True`` si SAP quedó libre.
        """
        def _check() -> bool:
            return not bool(self._com.Busy)

        return self.wait_until(_check, timeout=timeout, description="SAP libre")

    # ------------------------------------------------------------------

    def wait_window(self, index: int = 0, timeout: float = -1.0) -> bool:
        """Espera hasta que ``wnd[N]`` esté disponible.

        Parameters
        ----------
        index : int
            Índice de la ventana (0 = principal, 1 = popup).
        timeout : float
            Tiempo máximo de espera.

        Returns
        -------
        bool
            ``True`` si la ventana existe.
        """
        window_id: str = f"wnd[{index}]"

        def _check() -> bool:
            try:
                self._com.findById(window_id)
                return True
            except Exception:
                return False

        return self.wait_until(
            _check, timeout=timeout, description=f"ventana {window_id}"
        )

    # ------------------------------------------------------------------

    def wait_control(self, find_by_id: str, timeout: float = -1.0) -> bool:
        """Espera hasta que un control SAP esté disponible.

        Parameters
        ----------
        find_by_id : str
            Ruta del control (ej. ``"wnd[0]/tbar[0]/okcd"``).
        timeout : float
            Tiempo máximo de espera.

        Returns
        -------
        bool
            ``True`` si el control existe.
        """
        def _check() -> bool:
            try:
                self._com.findById(find_by_id)
                return True
            except Exception:
                return False

        return self.wait_until(
            _check, timeout=timeout, description=f"control {find_by_id}"
        )

    # ------------------------------------------------------------------

    def wait_transaction(
        self, transaction: str, timeout: float = -1.0
    ) -> bool:
        """Espera hasta que SAP esté en la transacción indicada.

        Parameters
        ----------
        transaction : str
            Código de transacción (ej. ``"MB52"``).
        timeout : float
            Tiempo máximo de espera.

        Returns
        -------
        bool
            ``True`` si se alcanzó la transacción.
        """
        def _check() -> bool:
            try:
                current: str = str(self._com.Info.Transaction or "")
                return current.upper() == transaction.upper()
            except Exception:
                return False

        return self.wait_until(
            _check,
            timeout=timeout,
            description=f"transacción {transaction}",
        )

    # ------------------------------------------------------------------

    def wait_ready(self, timeout: float = -1.0) -> bool:
        """Espera hasta que SAP esté listo (no busy + ventana 0).

        Método principal usado por el Execution Engine después
        de ejecutar cada acción.

        Parameters
        ----------
        timeout : float
            Tiempo máximo de espera.

        Returns
        -------
        bool
            ``True`` si SAP está listo.
        """
        if not self.wait_not_busy(timeout=timeout):
            return False
        if not self.wait_window(0, timeout=timeout):
            return False
        return True
