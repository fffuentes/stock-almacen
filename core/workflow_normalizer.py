"""Normalizador de workflows del SAP Automation Framework.

Proporciona la clase `WorkflowNormalizer` que transforma un
``WorkflowRaw`` (lenguaje VBS) en un ``Workflow`` (lenguaje SAF).
Cada módulo conoce únicamente su dominio:

- ResourceExtractor → lenguaje VBS
- WorkflowNormalizer → lenguaje SAP
- Execution Engine → lenguaje SAF
"""

from __future__ import annotations

from typing import Dict, Callable, Any

from core.workflow_raw import WorkflowRaw, WorkflowRawStep
from core.workflow import Workflow, WorkflowStep


# ---------------------------------------------------------------------------
# Tipo para las funciones de normalización
# ---------------------------------------------------------------------------

NormalizerFunc = Callable[[WorkflowRawStep, Workflow], bool]


class WorkflowNormalizer:
    """Transforma un WorkflowRaw en un Workflow SAF.

    Aplica reglas de normalización que interpretan el VBS
    en términos del dominio SAP. Las reglas no cubiertas
    se transfieren sin interpretar (passthrough).

    Reglas implementadas:
    1. ``set_text`` + ``okcd`` → ``start_transaction``
    2. ``send_vkey`` + 0 → ``confirm``
    3. ``send_vkey`` + 8 → ``execute``
    4. ``export`` → ``export_file``
    """

    # ------------------------------------------------------------------
    def __init__(self) -> None:
        """Inicializa el normalizador con las reglas registradas."""
        self._rules: list[NormalizerFunc] = [
            self._norm_start_transaction,
            self._norm_confirm,
            self._norm_execute,
            self._norm_export_file,
        ]

    # ------------------------------------------------------------------
    # Método público principal
    # ------------------------------------------------------------------

    def normalize(self, raw: WorkflowRaw) -> Workflow:
        """Normaliza un workflow raw al lenguaje SAF.

        Parameters
        ----------
        raw : WorkflowRaw
            Workflow extraído del VBS.

        Returns
        -------
        Workflow
            Workflow en lenguaje SAF.
        """
        wf: Workflow = Workflow(transaction=raw.transaction)

        for raw_step in raw.steps:
            matched: bool = False

            # Intentar cada regla de normalización
            for rule in self._rules:
                if rule(raw_step, wf):
                    matched = True
                    break

            # Si ninguna regla aplicó → passthrough
            if not matched:
                self._passthrough(raw_step, wf)

        return wf

    # ------------------------------------------------------------------
    # Regla 1: set_text + okcd → start_transaction
    # ------------------------------------------------------------------

    @staticmethod
    def _norm_start_transaction(
        raw_step: WorkflowRawStep, wf: Workflow
    ) -> bool:
        """Normaliza inicio de transacción.

        ``set_text`` en campo ``okcd`` → ``start_transaction``.

        Returns
        -------
        bool
            ``True`` si la regla aplicó.
        """
        if raw_step.type != "set_text":
            return False
        if raw_step.data.get("field", "") != "okcd":
            return False

        wf.add_step(
            action="start_transaction",
            transaction=raw_step.data.get("value", ""),
        )
        return True

    # ------------------------------------------------------------------
    # Regla 2: send_vkey 0 → confirm
    # ------------------------------------------------------------------

    @staticmethod
    def _norm_confirm(
        raw_step: WorkflowRawStep, wf: Workflow
    ) -> bool:
        """Normaliza confirmación (Enter).

        ``send_vkey`` con valor 0 → ``confirm``.

        Returns
        -------
        bool
            ``True`` si la regla aplicó.
        """
        if raw_step.type != "send_vkey":
            return False
        if raw_step.data.get("value", -1) != 0:
            return False

        wf.add_step(action="confirm")
        return True

    # ------------------------------------------------------------------
    # Regla 3: send_vkey 8 → execute
    # ------------------------------------------------------------------

    @staticmethod
    def _norm_execute(
        raw_step: WorkflowRawStep, wf: Workflow
    ) -> bool:
        """Normaliza ejecución (F8).

        ``send_vkey`` con valor 8 → ``execute``.

        Returns
        -------
        bool
            ``True`` si la regla aplicó.
        """
        if raw_step.type != "send_vkey":
            return False
        if raw_step.data.get("value", -1) != 8:
            return False

        wf.add_step(action="execute")
        return True

    # ------------------------------------------------------------------
    # Regla 4: export → export_file
    # ------------------------------------------------------------------

    @staticmethod
    def _norm_export_file(
        raw_step: WorkflowRawStep, wf: Workflow
    ) -> bool:
        """Normaliza exportación de archivo.

        ``export`` → ``export_file``.
        Conserva ``filename``, descarta ``path``,
        agrega ``path_source: framework_configuration``.

        Returns
        -------
        bool
            ``True`` si la regla aplicó.
        """
        if raw_step.type != "export":
            return False

        wf.add_step(
            action="export_file",
            filename=raw_step.data.get("filename", ""),
            path_source="framework_configuration",
        )
        return True

    # ------------------------------------------------------------------
    # Passthrough: transferir sin interpretar
    # ------------------------------------------------------------------

    @staticmethod
    def _passthrough(
        raw_step: WorkflowRawStep, wf: Workflow
    ) -> None:
        """Transfiere un paso raw al workflow SAF sin interpretar.

        Mapeo de tipos:
        - ``set_text`` → ``set_field`` (conserva field, value)
        - ``press_button`` → ``press_button``
        - ``select_menu`` → ``select_menu``
        - ``send_vkey`` → ``send_vkey`` (otros valores)
        - ``double_click`` → ``double_click``
        - ``select_rows`` → ``select_rows``
        - ``current_row`` → ``current_row``

        Parameters
        ----------
        raw_step : WorkflowRawStep
            Paso raw.
        wf : Workflow
            Workflow SAF destino.
        """
        action_map: Dict[str, str] = {
            "set_text": "set_field",
            "press_button": "press_button",
            "select_menu": "select_menu",
            "send_vkey": "send_vkey",
            "double_click": "double_click",
            "select_rows": "select_rows",
            "current_row": "current_row",
        }

        saf_action: str = action_map.get(raw_step.type, raw_step.type)

        # Construir datos del paso SAF
        data: Dict[str, Any] = {}

        if raw_step.type == "set_text":
            # Conservar field, value y target (find_by_id)
            data["field"] = raw_step.data.get("field", "")
            data["value"] = raw_step.data.get("value", "")
            data["target"] = raw_step.data.get("find_by_id", "")
        elif raw_step.type == "send_vkey":
            data["value"] = raw_step.data.get("value", "")
        elif raw_step.type in ("select_rows", "current_row"):
            data["value"] = raw_step.data.get("value", "")
            data["target"] = raw_step.data.get("find_by_id", "")
        else:
            # press_button, select_menu, double_click
            data["target"] = raw_step.data.get("find_by_id", "")

        wf.add_step(action=saf_action, **data)
