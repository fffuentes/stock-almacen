"""Excepciones personalizadas del SAP Automation Framework."""


class ConnectionUnavailableError(RuntimeError):
    """No se pudo establecer conexión con el servidor SAP.

    Indica que el diálogo de error de conexión fue detectado
    y cerrado automáticamente. No representa errores internos
    del Framework.
    """

    pass
