"""SAP Popup Manager — detecta, analiza y clasifica popups SAP modales.

Proporciona ``SAPPopupManager``, ``PopupType``, ``PopupInfo`` y ``PopupButton``.
Trabaja sobre ``wnd[1]`` de forma completamente pasiva: no responde
automáticamente, solo detecta y clasifica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, List, Optional


class PopupType(Enum):
    """Tipos de popups SAP reconocibles."""

    UNKNOWN = auto()
    REPORT_DIALOG = auto()
    CONFIRMATION = auto()
    WARNING = auto()
    ERROR = auto()
    INFORMATION = auto()
    FILE_OVERWRITE = auto()
    CUSTOM = auto()


@dataclass
class PopupButton:
    """Un botón dentro de un popup SAP.

    Attributes
    ----------
    index : int
        Posición del botón (0-based).
    id : str
        ID SAP del botón (ej. ``"btn[0]"``).
    text : str
        Texto visible del botón.
    """

    index: int
    id: str = ""
    text: str = ""


@dataclass
class PopupInfo:
    """Información completa de un popup SAP detectado.

    Attributes
    ----------
    popup_type : PopupType
        Tipo de popup clasificado.
    title : str
        Título de la ventana.
    message : str
        Texto o mensaje principal del popup.
    buttons : list[PopupButton]
        Botones disponibles.
    window_id : str
        ID de la ventana (normalmente ``"wnd[1]"``).
    confidence : int
        Porcentaje de confianza en la clasificación (0-100).
    """

    popup_type: PopupType = PopupType.UNKNOWN
    title: str = ""
    message: str = ""
    buttons: List[PopupButton] = field(default_factory=list)
    window_id: str = "wnd[1]"
    confidence: int = 0


class SAPPopupManager:
    """Detecta, analiza y clasifica popups SAP modales.

    Trabaja exclusivamente sobre ``wnd[1]``. No responde
    automáticamente — solo detecta y clasifica.

    Parameters
    ----------
    session_com : Any
        Referencia COM a una sesión SAP activa.
    """

    # Palabras clave para clasificación por título
    _TITLE_KEYWORDS: dict[str, PopupType] = {
        "error": PopupType.ERROR,
        "warning": PopupType.WARNING,
        "information": PopupType.INFORMATION,
        "confirm": PopupType.CONFIRMATION,
    }

    # Palabras clave para clasificación por contenido
    _TEXT_KEYWORDS: dict[str, PopupType] = {
        "overwrite": PopupType.FILE_OVERWRITE,
        "replace": PopupType.FILE_OVERWRITE,
        "sobrescribir": PopupType.FILE_OVERWRITE,
        "reemplazar": PopupType.FILE_OVERWRITE,
        "report": PopupType.REPORT_DIALOG,
        "informe": PopupType.REPORT_DIALOG,
    }

    # IDs de botones estándar SAP
    _BUTTON_PREFIXES: List[str] = [
        "wnd[1]/tbar[0]/btn[",
        "wnd[1]/usr/btnSPOP-OPTION",
        "wnd[1]/usr/btn",
    ]

    # ------------------------------------------------------------------
    def __init__(self, session_com: Any) -> None:
        """Inicializa el popup manager.

        Parameters
        ----------
        session_com : Any
            Referencia COM a la sesión SAP.
        """
        self._com: Any = session_com

    # ------------------------------------------------------------------
    def detect(self) -> Optional[PopupInfo]:
        """Detecta si existe un popup modal en ``wnd[1]``.

        Returns
        -------
        PopupInfo or None
            Información del popup, o ``None`` si no existe.
        """
        # Verificar que wnd[1] existe
        try:
            wnd1 = self._com.findById("wnd[1]")
        except Exception:
            return None

        info = PopupInfo()

        # Título
        try:
            info.title = str(wnd1.Text or "")
        except Exception:
            pass

        # Mensaje (intentar varios elementos de texto)
        info.message = self._extract_message()

        # Botones
        info.buttons = self._extract_buttons()

        # Clasificar
        info.popup_type = self._classify(info)

        # Confianza
        info.confidence = 100 if info.popup_type != PopupType.UNKNOWN else 50

        return info

    # ------------------------------------------------------------------
    def close(self, button_index: int = 0) -> bool:
        """Cierra el popup presionando el botón indicado.

        Parameters
        ----------
        button_index : int
            Índice del botón a presionar (default 0).

        Returns
        -------
        bool
            ``True`` si se presionó correctamente.
        """
        try:
            wnd1 = self._com.findById("wnd[1]")
            # Intentar btn estándar en tbar
            button = wnd1.findById(f"tbar[0]/btn[{button_index}]")
            button.press()
            return True
        except Exception:
            pass

        try:
            # Intentar btnSPOP-OPTION
            button = self._com.findById(
                f"wnd[1]/usr/btnSPOP-OPTION{button_index + 1}"
            )
            button.press()
            return True
        except Exception:
            pass

        return False

    # ------------------------------------------------------------------
    def press_button(self, index: int) -> bool:
        """Presiona un botón por índice (0-based).

        Parameters
        ----------
        index : int
            Índice del botón.

        Returns
        -------
        bool
            ``True`` si se presionó.
        """
        return self.close(button_index=index)

    # ------------------------------------------------------------------
    def press_button_by_text(self, text: str) -> bool:
        """Presiona un botón cuyo texto coincide parcialmente.

        Parameters
        ----------
        text : str
            Texto a buscar (case-insensitive, partial match).

        Returns
        -------
        bool
            ``True`` si se encontró y presionó.
        """
        buttons: List[PopupButton] = self._extract_buttons()
        target: str = text.lower()

        for btn in buttons:
            if target in btn.text.lower():
                return self.close(button_index=btn.index)

        return False

    # ------------------------------------------------------------------
    # Extracción
    # ------------------------------------------------------------------

    def _extract_message(self) -> str:
        """Extrae el mensaje principal del popup."""
        # Intentar varios caminos de texto estándar en popups SAP
        text_paths: List[str] = [
            "wnd[1]/usr/txtMESSTXT1",
            "wnd[1]/usr/txtMESSTXT2",
            "wnd[1]/usr/txtSPOP-TEXTLINE1",
            "wnd[1]/usr/txtSPOP-TEXTLINE2",
            "wnd[1]/usr/lbl[1,1]",
            "wnd[1]/usr/cntlTEXT_CONTAINER/shellcont/shell",
        ]

        texts: List[str] = []
        for path in text_paths:
            try:
                elem = self._com.findById(path)
                t = str(elem.Text or elem.text or "")
                if t.strip():
                    texts.append(t.strip())
            except Exception:
                pass

        return "\n".join(texts) if texts else ""

    # ------------------------------------------------------------------

    def _extract_buttons(self) -> List[PopupButton]:
        """Extrae todos los botones del popup."""
        buttons: List[PopupButton] = []

        # Método 1: Botones en toolbar de wnd[1]
        for i in range(20):
            try:
                btn = self._com.findById(f"wnd[1]/tbar[0]/btn[{i}]")
                text = str(btn.Text or btn.text or "")
                buttons.append(PopupButton(index=i, id=f"btn[{i}]", text=text))
            except Exception:
                break

        if buttons:
            return buttons

        # Método 2: Botones SPOP-OPTION (popups de confirmación/error)
        for i in range(1, 5):
            try:
                btn = self._com.findById(f"wnd[1]/usr/btnSPOP-OPTION{i}")
                text = str(btn.Text or btn.text or "")
                buttons.append(
                    PopupButton(index=i - 1, id=f"btnSPOP-OPTION{i}", text=text)
                )
            except Exception:
                pass

        return buttons

    # ------------------------------------------------------------------
    # Clasificación
    # ------------------------------------------------------------------

    def _classify(self, info: PopupInfo) -> PopupType:
        """Clasifica el popup por título, texto y botones.

        Parameters
        ----------
        info : PopupInfo
            Información extraída del popup.

        Returns
        -------
        PopupType
            Tipo clasificado.
        """
        # 1. Por botones estándar (SPOP-OPTION1 + SPOP-OPTION2 → CONFIRMATION)
        has_option1 = any("OPTION1" in b.id for b in info.buttons)
        has_option2 = any("OPTION2" in b.id for b in info.buttons)
        if has_option1 and has_option2:
            return PopupType.CONFIRMATION

        # 2. Por título
        title_lower: str = info.title.lower()
        for keyword, ptype in self._TITLE_KEYWORDS.items():
            if keyword in title_lower:
                return ptype

        # 3. Por contenido textual
        text_lower: str = (info.title + " " + info.message).lower()
        for keyword, ptype in self._TEXT_KEYWORDS.items():
            if keyword in text_lower:
                return ptype

        # 4. Tiene botones pero no se clasificó → CUSTOM
        if info.buttons:
            return PopupType.CUSTOM

        return PopupType.UNKNOWN
