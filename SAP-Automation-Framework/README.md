# SAP Automation Framework (SAF)

Framework para automatizar procesos SAP GUI, ejecutar workflows definidos
desde recursos VBS y publicar resultados para el Portal Web.

---

## Estructura del proyecto

```
SAP-Automation-Framework/
├── main.py                 # Punto de entrada y orquestación del flujo
├── requirements.txt        # Dependencias del proyecto
├── README.md               # Documentación del proyecto
├── .gitignore              # Exclusiones de Git
│
├── actions/                # Handlers de acciones SAF
├── config/                 # Configuración y asistente interactivo
│   ├── __init__.py
│   ├── config_manager.py   # Carga, validación y persistencia
│   └── config_wizard.py    # Asistente interactivo por consola
│
├── core/                   # Núcleo, workflows, SAP y publicación
│   ├── execution_engine.py # Ejecución de workflows sobre SAP
│   ├── resource_manager.py # Descubrimiento y procesamiento de VBS
│   ├── workflow.py         # Modelo de workflow SAF
│   ├── workflow_normalizer.py
│   ├── image_index_generator.py # Índice de imágenes del Portal Web
│   └── git_manager.py      # Publicación selectiva en Git
│
├── resources/              # VBS, metadata y workflows por transacción
│   └── MB52/
├── transactions/           # Automatizaciones SAP adicionales
├── exports/                # Exportaciones locales
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

### Gestión de recursos

```bash
python main.py resources
```

Escanea los archivos VBS dentro de `resources/`, calcula su hash y genera o
actualiza `metadata.json`, `workflow.raw.json` y `workflow.json` cuando es
necesario.

### Ejecución de una transacción

```bash
python main.py run MB52
```

El flujo de ejecución es:

1. Cargar el workflow SAF de la transacción.
2. Crear una sesión SAP GUI.
3. Ejecutar sus acciones mediante `ExecutionEngine`.
4. Verificar que el archivo exportado exista.
5. Generar `web/images/materials/material-index.json` mediante
	`ImageIndexGenerator`.
6. Publicar en Git únicamente los cambios de `web/data/MB52.txt`.

El índice de imágenes se genera a partir de los archivos `.jpg`, `.jpeg`,
`.png`, `.webp` y `.bmp` encontrados en `web/images/materials`. Los nombres
de archivo válidos se convierten en códigos de material, se eliminan los
duplicados y se ordenan ascendentemente.

---

## Funcionalidades implementadas

- [x] Estructura base del proyecto.
- [x] Sistema de configuración con persistencia en JSON.
- [x] Asistente interactivo por consola.
- [x] Validación de configuración.
- [x] Detección automática de SAP Logon.
- [x] Resumen de estado al iniciar.
- [x] Conexión y ejecución de workflows mediante SAP GUI Scripting.
- [x] Extracción y normalización de workflows desde archivos VBS.
- [x] Exportación de resultados hacia la ruta configurada.
- [x] Generación automática del índice de imágenes del Portal Web.
- [x] Publicación Git limitada al archivo `web/data/MB52.txt`.
- [x] Detección de commits pendientes antes de publicar.
- [x] Reintentos automáticos del `git push` (3 intentos).

---

## Notas de publicación

`GitManager` verifica únicamente los cambios de `web/data/MB52.txt`. Los
cambios de otros archivos del repositorio no activan el commit automático.
La generación del índice ocurre antes de la publicación, únicamente después
de una ejecución exitosa del workflow y de la validación de la exportación.

### Flujo de publicación

1. Validar que la ruta configurada sea un repositorio Git (carpeta `.git`).
2. Detectar si existen commits locales pendientes de publicar:
   - Si existen: no se ejecuta `git add` ni `git commit`; únicamente se
     publica con `git push origin main`.
   - Si no existen: se continúa con el flujo normal.
3. Verificar cambios en el working tree (`git status --porcelain`):
   - Sin cambios: finaliza sin publicar.
   - Con cambios: `git add web/data/MB52.txt` y
     `git commit -m "Actualización MB52 - AAAA-MM-DD HH:mm:ss"`.
4. Publicar con `git push origin main` (explícito, no depende del upstream
   configurado localmente).

### Reintentos automáticos del push

El push se realiza con hasta **3 intentos**:

- Intento 1: inmediato.
- Si falla, espera 5 segundos y reintenta.
- Si vuelve a fallar, espera 10 segundos y reintenta por última vez.
- Si los tres intentos fallan, se relanza el error original de Git.

Durante los reintentos **no** se ejecuta `git add` ni `git commit`.
Únicamente se vuelve a ejecutar `git push origin main`.

### Mensajes de GitManager

- Sin cambios: `No existen cambios para publicar.`
- Commits pendientes publicados: `Commit(s) pendientes publicados correctamente.`
- Publicación correcta: `Repositorio actualizado correctamente.`
- En caso de error: se muestra el error recibido desde Git.
