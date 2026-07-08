"""Registro central de acciones del SAP Automation Framework.

Proporciona el ``ActionRegistry`` que mapea nombres de acciones
SAF (``"start_transaction"``, ``"set_field"``, etc.) a sus
clases Handler correspondientes.

Los handlers se registran mediante el decorador ``@ActionRegistry.register``.
El Execution Engine consulta este registro para resolver qué
handler ejecutar para cada paso del workflow.
"""

from __future__ import annotations

from typing import Dict, Optional, Type

from actions.base import BaseActionHandler


class ActionRegistry:
    """Registro central de handlers de acciones SAF.

    Los handlers se auto-registran al decorar su clase con
    ``@ActionRegistry.register("nombre_accion")``.

    El Execution Engine nunca conoce las clases concretas;
    solo consulta este registro por nombre de acción.
    """

    _handlers: Dict[str, Type[BaseActionHandler]] = {}

    # ------------------------------------------------------------------

    @classmethod
    def register(cls, action_name: str):
        """Decorador para registrar un handler de acción.

        Usage::

            @ActionRegistry.register("start_transaction")
            class StartTransactionHandler(BaseActionHandler):
                ...

        Parameters
        ----------
        action_name : str
            Nombre de la acción SAF (ej. ``"start_transaction"``).
        """

        def decorator(handler_cls: Type[BaseActionHandler]):
            cls._handlers[action_name] = handler_cls
            return handler_cls

        return decorator

    # ------------------------------------------------------------------

    @classmethod
    def get(cls, action_name: str) -> Optional[Type[BaseActionHandler]]:
        """Obtiene la clase handler para una acción.

        Parameters
        ----------
        action_name : str
            Nombre de la acción.

        Returns
        -------
        Type[BaseActionHandler] or None
            Clase del handler, o ``None`` si no está registrada.
        """
        return cls._handlers.get(action_name)

    # ------------------------------------------------------------------

    @classmethod
    def is_registered(cls, action_name: str) -> bool:
        """Verifica si una acción tiene handler registrado.

        Parameters
        ----------
        action_name : str
            Nombre de la acción.

        Returns
        -------
        bool
            ``True`` si está registrada.
        """
        return action_name in cls._handlers

    # ------------------------------------------------------------------

    @classmethod
    def registered_actions(cls) -> list[str]:
        """Lista de todas las acciones registradas.

        Returns
        -------
        list[str]
            Nombres de acciones con handler.
        """
        return list(cls._handlers.keys())
