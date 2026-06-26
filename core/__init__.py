"""Módulo núcleo del SAP Automation Framework.

Contiene las clases fundamentales que orquestan la ejecución
del framework y sus componentes principales.
"""

from .framework import Framework
from .sap_diagnostics import SAPDiagnostics, SessionInfo, ConnectionInfo
from .sap_debug import SAPDebug
from .sap_session import SAPSession
from .session_manager import SessionManager
from .resource import Resource, ResourceStatus
from .resource_manager import ResourceManager
from .resource_extractor import ResourceExtractor
from .workflow_raw import WorkflowRaw, WorkflowRawStep, IgnoredInstruction, WorkflowStatistics
from .workflow import Workflow, WorkflowStep
from .workflow_normalizer import WorkflowNormalizer
from .workflow_definition import WorkflowDefinition, WorkflowStatus
from .action_registry import ActionRegistry
from .execution_engine import ExecutionEngine
from .sap_waiter import SAPWaiter
from .sap_connector import SAPConnector
from .login_manager import LoginManager, LoginState

__all__ = [
    "Framework",
    "SAPDiagnostics",
    "SAPDebug",
    "SAPSession",
    "SessionManager",
    "Resource",
    "ResourceStatus",
    "ResourceManager",
    "ResourceExtractor",
    "WorkflowRaw",
    "WorkflowRawStep",
    "IgnoredInstruction",
    "WorkflowStatistics",
    "Workflow",
    "WorkflowStep",
    "WorkflowNormalizer",
    "ActionRegistry",
    "ExecutionEngine",
    "SAPWaiter",
    "SAPConnector",
    "LoginManager",
    "LoginState",
    "WorkflowDefinition",
    "WorkflowStatus",
    "SessionInfo",
    "ConnectionInfo",
]
