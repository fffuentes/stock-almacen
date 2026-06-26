"""Windows Dialog Explorer — inspecciona ventanas nativas de Windows.

Proporciona ``WindowsDialogExplorer`` que enumera ventanas visibles,
identifica diálogos de SAP Logon/sapgui.exe y analiza sus controles
hijos. Totalmente de solo lectura.

Utiliza pywin32 (win32gui, win32process, win32con).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class WindowControlInfo:
    """Información de un control hijo dentro de una ventana.

    Attributes
    ----------
    handle : int
        Handle de la ventana del control.
    class_name : str
        Clase de Windows (``"Button"``, ``"Static"``, ``"Edit"``, etc.).
    text : str
        Texto del control.
    control_id : int
        ID del control.
    enabled : bool
        Si está habilitado.
    visible : bool
        Si es visible.
    """

    handle: int = 0
    class_name: str = ""
    text: str = ""
    control_id: int = 0
    enabled: bool = False
    visible: bool = False


@dataclass
class WindowInfo:
    """Información de una ventana nativa de Windows.

    Attributes
    ----------
    handle : int
        Handle de la ventana.
    class_name : str
        Clase de Windows (``"#32770"`` = diálogo).
    title : str
        Título de la ventana.
    visible : bool
        Si es visible.
    enabled : bool
        Si está habilitada.
    process_id : int
        PID del proceso dueño.
    process_name : str
        Nombre del ejecutable (``"saplogon.exe"``, etc.).
    children : list[WindowControlInfo]
        Controles hijos.
    """

    handle: int = 0
    class_name: str = ""
    title: str = ""
    visible: bool = False
    enabled: bool = False
    process_id: int = 0
    process_name: str = ""
    children: List[WindowControlInfo] = field(default_factory=list)


class WindowsDialogExplorer:
    """Explora ventanas nativas de Windows y sus controles.

    Identifica diálogos pertenecientes a procesos SAP
    (saplogon.exe, sapgui.exe) o con clase ``#32770`` (diálogo).
    Totalmente de solo lectura.
    """

    # Procesos SAP a monitorear
    _SAP_PROCESSES: set[str] = {"saplogon.exe", "sapgui.exe", "sapfewdll.exe"}

    # Clases de diálogo
    _DIALOG_CLASSES: set[str] = {"#32770"}

    # ------------------------------------------------------------------
    def enumerate_windows(self) -> List[WindowInfo]:
        """Enumera todas las ventanas visibles de nivel superior.

        Returns
        -------
        list[WindowInfo]
            Ventanas encontradas.
        """
        import win32gui
        import win32process

        results: List[WindowInfo] = []

        def _callback(hwnd: int, _: Any) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True  # Continuar enumeración

            info = WindowInfo()
            info.handle = hwnd
            info.class_name = win32gui.GetClassName(hwnd)
            info.title = win32gui.GetWindowText(hwnd)
            info.visible = win32gui.IsWindowVisible(hwnd)
            info.enabled = win32gui.IsWindowEnabled(hwnd)

            # PID y nombre de proceso
            try:
                _, info.process_id = win32process.GetWindowThreadProcessId(hwnd)
                import win32api
                handle = win32api.OpenProcess(0x0400, False, info.process_id)
                info.process_name = win32process.GetModuleFileNameEx(
                    handle, 0
                ).split("\\")[-1].lower()
                win32api.CloseHandle(handle)
            except Exception:
                info.process_name = ""

            # Enumerar hijos si es SAP o diálogo
            if self._is_target(info):
                info.children = self.enumerate_children(hwnd)

            results.append(info)
            return True

        try:
            win32gui.EnumWindows(_callback, None)
        except Exception:
            pass

        return results

    # ------------------------------------------------------------------
    def enumerate_children(self, hwnd: int) -> List[WindowControlInfo]:
        """Enumera los controles hijos de una ventana.

        Parameters
        ----------
        hwnd : int
            Handle de la ventana padre.

        Returns
        -------
        list[WindowControlInfo]
            Controles encontrados.
        """
        import win32gui

        children: List[WindowControlInfo] = []

        def _callback(child_hwnd: int, _: Any) -> bool:
            try:
                ctrl = WindowControlInfo()
                ctrl.handle = child_hwnd
                ctrl.class_name = win32gui.GetClassName(child_hwnd)
                ctrl.text = win32gui.GetWindowText(child_hwnd)
                ctrl.control_id = win32gui.GetDlgCtrlID(child_hwnd)
                ctrl.enabled = win32gui.IsWindowEnabled(child_hwnd)
                ctrl.visible = win32gui.IsWindowVisible(child_hwnd)
                children.append(ctrl)
            except Exception:
                pass
            return True

        try:
            win32gui.EnumChildWindows(hwnd, _callback, None)
        except Exception:
            pass

        return children

    # ------------------------------------------------------------------
    def find_dialogs(self) -> List[WindowInfo]:
        """Encuentra solo ventanas que son diálogos SAP relevantes.

        Returns
        -------
        list[WindowInfo]
            Diálogos SAP encontrados.
        """
        all_windows: List[WindowInfo] = self.enumerate_windows()
        return [w for w in all_windows if self._is_target(w)]

    # ------------------------------------------------------------------
    def _is_target(self, win: WindowInfo) -> bool:
        """Determina si una ventana es de interés (SAP o diálogo).

        Parameters
        ----------
        win : WindowInfo
            Ventana a evaluar.

        Returns
        -------
        bool
            ``True`` si pertenece a SAP o es un diálogo de error.
        """
        if win.process_name in self._SAP_PROCESSES:
            return True
        # Solo diálogos (#32770) de procesos SAP o del sistema
        if win.class_name in self._DIALOG_CLASSES:
            # Filtrar: solo si el proceso es SAP o es un diálogo de error conocido
            if win.process_name in self._SAP_PROCESSES:
                return True
            # También diálogos con "SAP" en título pero SOLO si no son VS Code/Explorer
            title_upper = win.title.upper()
            if "SAP" in title_upper and "VISUAL STUDIO" not in title_upper and "EXPLORADOR" not in title_upper:
                return True
        return False
