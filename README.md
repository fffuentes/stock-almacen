# SAP Automation Framework (SAF)

Framework profesional para la automatización de procesos SAP.
**Fase 1 — Fundación del proyecto.**

---

## Estructura del proyecto

```
SAP-Automation-Framework/
├── main.py                 # Punto de entrada principal
├── requirements.txt        # Dependencias del proyecto
├── README.md               # Documentación del proyecto
├── .gitignore              # Exclusiones de Git
│
├── config/                 # Módulo de configuración
│   ├── __init__.py
│   ├── config_manager.py   # Carga, validación y persistencia
│   └── config_wizard.py    # Asistente interactivo por consola
│
├── core/                   # Núcleo del framework
│   ├── __init__.py
│   └── framework.py        # Orquestador principal
│
├── transactions/           # Automatizaciones SAP (fases futuras)
├── exports/                # Módulo de exportaciones (fases futuras)
├── logs/                   # Archivos de log
├── temp/                   # Archivos temporales
└── tests/                  # Pruebas unitarias y de integración
```

---

## Requisitos

- Python 3.9 o superior.
- Sistema operativo Windows (para SAP GUI Scripting en fases futuras).

---

## Instalación

```bash
# Clonar o copiar el proyecto
cd SAP-Automation-Framework

# (Opcional) Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## Uso

### Asistente de configuración

```bash
python main.py configure
```

Solicita interactivamente todos los parámetros necesarios:
- Ruta de SAP Logon (con detección automática).
- Sistema SAP.
- Cliente.
- Idioma.
- Usuario y contraseña.
- Ruta de exportaciones.
- Ruta del repositorio Git.

### Ejecución normal

```bash
python main.py
```

- Carga y valida la configuración.
- Muestra un resumen del estado.
- Si no existe configuración, inicia automáticamente el asistente.

---

## Fase 1 — Alcance

- [x] Estructura base del proyecto.
- [x] Sistema de configuración con persistencia en JSON.
- [x] Asistente interactivo por consola.
- [x] Validación de configuración.
- [x] Detección automática de SAP Logon.
- [x] Resumen de estado al iniciar.

---

## Próximas fases

La Fase 2 incorporará:
- Conexión con SAP GUI Scripting.
- Ejecución de transacciones automatizadas.
- Sistema de logging estructurado.
- Exportación de resultados.
- Integración con Git.
- Planificador de tareas (Scheduler).
