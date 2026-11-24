# Documento de Conocimiento Técnico — SAP Automation Framework (SAF)

## 1. Descripción general de SAF

**SAF (SAP Automation Framework)** es una solución de automatización para **SAP GUI** cuya finalidad es extraer periódicamente datos del sistema SAP (hoy, la transacción **MB52** — reporte de existencias por material) y publicarlos de forma visual y consultable en un **Portal Web** alojado en GitHub Pages.

La solución está compuesta por dos componentes que viven en el **mismo repositorio** (`fffuentes/stock-almacen`) y que operan de forma integrada:

| Componente | Tecnología | Carpeta | Rol |
|---|---|---|---|
| **Framework** | Python 3.9+ + `pywin32` (COM) | `SAP-Automation-Framework/` | Núcleo de automatización: se conecta a SAP GUI, ejecuta workflows y exporta datos. |
| **Portal Web** | HTML + CSS + JavaScript (vanilla, sin frameworks) | `web/` | Interfaz de consulta: parsea, busca y visualiza los datos exportados. |

El **vínculo** entre ambos es, esencialmente, el sistema de archivos: el Framework exporta `MB52.txt` directamente en `web/data/`, genera `web/images/materials/material-index.json` y publica esos cambios vía Git. El Portal lee esos archivos estáticos.

**Objetivo funcional concreto (flujo de valor):** ejecutar la transacción SAP MB52 → exportar el reporte de existencias → enriquecerlo con fotografías de materiales → publicarlo para que un usuario final consulte materiales, existencias y fotos desde el navegador.

---

## 2. Arquitectura completa del proyecto

El proyecto está organizado en **capas con responsabilidades claras** y un **lenguaje intermedio propio** ("lenguaje SAF") que desacopla el VBS generado por SAP del motor de ejecución.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            REPOSITORIO (stock-almacen)                       │
│  ├── SAP-Automation-Framework/   ← Framework Python (automatización)        │
│  ├── web/                        ← Portal Web (consulta)                    │
│  └── .github/workflows/          ← CI/CD (GitHub Pages)                     │
└────────────────────────────────────────────────────────────────────────────┘

                        ┌────────────────────────────────────┐
                        │          SAP GUI (Windows)         │
                        │   SAP Logon → SAP GUI Scripting    │
                        └───────────────┬────────────────────┘
                                        │ COM (pywin32)
                                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         FRAMEWORK PYTHON                                    │
│                                                                             │
│  main.py (CLI / orquestación)                                               │
│     │                                                                       │
│     ├── config/        ConfigManager · ConfigWizard                         │
│     │                                                                       │
│     ├── resources/     MB52.vbs  (fuente, generado por SAP Recorder)        │
│     │        │                                                              │
│     │        ▼                                                              │
│     │   core/resource_manager.py  (descubrimiento + hash + metadata)        │
│     │   core/resource_extractor.py (VBS → workflow.raw.json)  ← patterns/   │
│     │   core/workflow_normalizer.py (raw → workflow.json "lenguaje SAF")    │
│     │                                                                       │
│     ├── core/execution_engine.py  (ejecuta workflow SAF)                    │
│     │        ├── core/session_manager.py → core/sap_session.py              │
│     │        ├── core/sap_recovery_engine.py (recupera estado SAP)          │
│     │        │     ├── core/sap_connector.py · sap_state_detector.py        │
│     │        │     ├── core/login_manager.py · sap_waiter.py                │
│     │        │     └── core/native_dialog_manager.py                        │
│     │        ├── actions/*  (handlers registrados en action_registry.py)    │
│     │        └── core/sap_waiter.py                                         │
│     │                                                                       │
│     ├── exports → (settings.json exports_path = web/data)                   │
│     ├── core/image_index_generator.py → web/images/materials/material-index.json
│     └── core/git_manager.py  (commit + push selectivo)                      │
└────────────────────────────────────────────────────────────────────────────┘
                                        │ git push origin main
                                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         PORTAL WEB (web/)                                   │
│  index.html                                                                │
│     ├── css/styles.css        (tema oscuro)                                │
│     └── js/                                                                │
│          app.js        (orquestación: carga, polling, estado)              │
│          parser.js     (data/MB52.txt → {headers, rows})                   │
│          smartSearch.js (motor de comparación + puntuación)                │
│          search.js     (filtrado + orden por score)                        │
│          table.js      (render dinámico de tabla)                          │
│          materialViewer.js (modal de detalle + foto)                       │
│                                                                             │
│  data/MB52.txt            ← exportado por el Framework                     │
│  images/materials/*.jpg   ← fotografías de materiales                      │
│  images/materials/material-index.json ← generado por el Framework          │
└────────────────────────────────────────────────────────────────────────────┘
                                        │ GitHub Actions (push a main)
                                        ▼
                              GitHub Pages (servicio estático)
```

La idea clave es un **pipeline de transformación por etapas**:

```
VBS (SAP Recorder) → workflow.raw.json → workflow.json (SAF) → ejecución COM → MB52.txt
```

Cada etapa conoce solo su "dominio" (VBS / dominio SAP / lenguaje SAF), lo que evita el acoplamiento.

---

## 3. Estructura de directorios y responsabilidades

### 3.1 Framework Python (`SAP-Automation-Framework/`)

| Ruta | Responsabilidad |
|---|---|
| `main.py` | Punto de entrada CLI. Interpreta subcomandos y orquesta cada flujo. |
| `requirements.txt` | Única dependencia real: `pywin32>=305`. |
| `run_mb52.bat` | Atajo de Windows: `python main.py run MB52` con pausa final. |
| `config/` | Configuración persistente en JSON. |
| `config/config_manager.py` | Modelo `FrameworkConfig` (dataclass) + `ConfigManager` (load/save/validate/summary). |
| `config/config_wizard.py` | `ConfigWizard`: asistente interactivo por consola (detección de SAP Logon, descubrimiento de conexiones via COM). |
| `config/settings.json` | Configuración real (gitignored; contiene credenciales). |
| `core/` | Núcleo lógico (ver tabla siguiente). |
| `core/patterns/` | Patrones de reconocimiento de instrucciones VBS (regex). |
| `actions/` | Handlers de acciones SAF (una clase por acción). |
| `resources/MB52/` | Recurso de la transacción MB52: VBS fuente + 3 archivos derivados. |
| `transactions/` | Vacío (reservado para automatizaciones SAP adicionales). |
| `exports/` | Paquete vacío (`__init__.py`); la exportación real va a `web/data`. |
| `logs/`, `temp/` | Carpetas con `.gitkeep` para runtime. |
| `tests/` | Pruebas (`test_image_index_generator.py`). |

### 3.2 `core/` — módulos del núcleo

| Módulo | Responsabilidad principal |
|---|---|
| `framework.py` | Clase `Framework`: orquesta config + validación + resumen (flujo base). |
| `execution_engine.py` | `ExecutionEngine`: ejecuta un `Workflow` SAF sobre SAP. |
| `action_registry.py` | `ActionRegistry`: registro central acción → handler (decorador). |
| `workflow.py` | `Workflow` / `WorkflowStep`: modelo SAF (load/save/add_step). |
| `workflow_raw.py` | `WorkflowRaw` / `WorkflowRawStep` / `IgnoredInstruction` / `WorkflowStatistics`. |
| `workflow_definition.py` | `WorkflowDefinition` / `WorkflowStatus` (placeholder/legacy). |
| `workflow_normalizer.py` | `WorkflowNormalizer`: raw → SAF (reglas + passthrough). |
| `resource.py` | `Resource` / `ResourceStatus`: hash SHA256, metadata, estado. |
| `resource_manager.py` | `ResourceManager`: descubrimiento, clasificación, extracción, normalización. |
| `resource_extractor.py` | `ResourceExtractor`: VBS → `workflow.raw.json` (aplica patrones). |
| `session_manager.py` | `SessionManager`: conexión COM, descubrimiento y ciclo de vida de sesión. |
| `sap_session.py` | `SAPSession`: encapsula `GuiSession`, solo lectura + cierre. |
| `sap_connector.py` | `SAPConnector`: garantiza que SAP Logon esté abierto y listo. |
| `login_manager.py` | `LoginManager`: login como máquina de estados. |
| `sap_recovery_engine.py` | `SAPRecoveryEngine`: lleva SAP a estado autenticado (detectar→actuar). |
| `sap_state_detector.py` | `SAPStateDetector`: análisis jerárquico Connection→Session→Window→Controls. |
| `sap_waiter.py` | `SAPWaiter`: espera inteligente (polling sobre estado real). |
| `sap_diagnostics.py` | `SAPDiagnostics`: diagnóstico solo-lectura del entorno. |
| `sap_debug.py` | `SAPDebug`: exploración verbose del árbol COM. |
| `sap_popup_manager.py` | `SAPPopupManager`: detección/clasificación pasiva de popups (`wnd[1]`). |
| `connection_explorer.py` | `ConnectionExplorer`: explora conexiones/propiedades COM. |
| `open_connection_tester.py` | `OpenConnectionTester`: prueba experimental de `OpenConnection`. |
| `windows_dialog_explorer.py` | `WindowsDialogExplorer`: enumera ventanas nativas Win32. |
| `native_dialog_manager.py` | `NativeDialogManager`: cierra el diálogo nativo de error de conexión. |
| `image_index_generator.py` | `ImageIndexGenerator`: genera `material-index.json`. |
| `git_manager.py` | `GitManager`: publicación selectiva en Git. |
| `exceptions.py` | `ConnectionUnavailableError` (excepción de dominio). |

### 3.3 `actions/` — handlers

| Handler (acción SAF) | Efecto sobre SAP |
|---|---|
| `start_transaction` | Escribe el código en `wnd[0]/tbar[0]/okcd` y presiona Enter (`sendVKey 0`). |
| `confirm` | `sendVKey(0)` (Enter) sobre `wnd[0]`. |
| `execute` | `sendVKey(8)` (F8) sobre `wnd[0]`. |
| `set_field` | Escribe `value` en el control `target` (findById). |
| `press_button` | `press()` sobre `target`. |
| `select_menu` | `select()` sobre `target`. |
| `send_vkey` | `sendVKey(value)` sobre `wnd[0]`. |
| `export_file` | Rellena `DY_PATH` (desde configuración) y `DY_FILENAME`; elimina archivo previo. |

### 3.4 `resources/MB52/`

| Archivo | Generado por | Propósito |
|---|---|---|
| `MB52.vbs` | SAP GUI Recorder (manual) | Fuente de verdad del workflow (UTF-16 LE). |
| `workflow.raw.json` | `ResourceExtractor` | VBS estructurado (pasos + ignoradas + stats). |
| `workflow.json` | `WorkflowNormalizer` | Workflow en lenguaje SAF (listo para ejecutar). |
| `metadata.json` | `ResourceManager` | Hash SHA256 + fecha + versión (detección de cambios). |

### 3.5 Portal Web (`web/`)

| Ruta | Responsabilidad |
|---|---|
| `index.html` | Estructura: header (estado), tarjetas de búsqueda y resultados, carga de scripts en orden. |
| `css/styles.css` | Único CSS: variables de tema oscuro, tarjetas, tabla sticky, modal. |
| `js/app.js` | Orquestador: carga índice de imágenes, carga inicial, polling 30 s, estado global. |
| `js/parser.js` | `loadMB52()`: fetch + parseo genérico de `MB52.txt`. |
| `js/smartSearch.js` | `SmartSearch`: normalización y matching con puntuación. |
| `js/search.js` | `filterMaterials()`: delega en SmartSearch y ordena por score. |
| `js/table.js` | `renderTable()`: tabla dinámica, columna calculada, indicador de foto. |
| `js/materialViewer.js` | `MaterialViewer`: modal de detalle al hacer clic en una fila. |
| `data/MB52.txt` | Datos exportados (delimitado por tabulaciones). |
| `images/materials/*.jpg` | Fotografías de materiales (nombradas por código SAP). |
| `images/materials/material-index.json` | Índice de materiales con foto (generado por el Framework). |

### 3.6 CI/CD

- `.github/workflows/deploy-pages.yml`: en cada push a `main`, publica la carpeta `web/` como artefacto en **GitHub Pages**.

### Discrepancias detectadas entre documentación y código

(Registradas para tenerlas presentes, sin corregir en este estudio.)

1. **README — estructura de `core/` incompleta.** El README lista 6 módulos de `core/`; el código tiene ~26 módulos (incluye `sap_connector`, `session_manager`, `sap_session`, `login_manager`, `sap_recovery_engine`, `sap_state_detector`, `sap_waiter`, los 5 módulos de diagnóstico, `action_registry`, `exceptions`, `resource`, `resource_extractor`, `workflow_definition`, `workflow_raw` y el subpaquete `patterns/`).
2. **README — campos de configuración incompletos.** El README describe: SAP Logon, Sistema, Cliente, Idioma, Usuario, Contraseña, Exportaciones, Git. El código (`FrameworkConfig`) incluye además `sap_connection` (conexión SAP Logon) y `system_name` (SystemName real, p. ej. `PS4`), ambos obligatorios en `validate()`.
3. **README — subcomandos no documentados.** `main.py` soporta `config`, `test`, `session`, `resources`, `run`, `connections`, `login-test`, `state`, `popup`, `win-dialogs`, `native-dialog`, además de `configure`. El README solo documenta `configure`, `resources` y `run`.
4. **README — "tests de integración".** El README menciona pruebas unitarias y de integración; solo existe `test_image_index_generator.py`.
5. **Comentarios obsoletos en `framework.py` y `requirements.txt`.** El código conserva referencias a "Fase 1"/"Fase 2" de un desarrollo por fases; el proyecto ya supera ampliamente esa fase (ejecuta workflows, exporta y publica).
6. **`workflow_definition.py` es mayormente legado.** El formato actual de `workflow.json` es el SAF ("steps"); `WorkflowDefinition` genera un placeholder transitorio que `WorkflowNormalizer` sobrescribe.
7. **`.gitignore` raíz con contenido anómalo.** El `.gitignore` raíz termina con caracteres de codificación corrupta/artefacto (`BACKUP_*.zip` seguido de texto UTF-16 con nulos). No es crítico pero difiere del `.gitignore` limpio de `SAP-Automation-Framework/`.

---

## 4. Funcionamiento interno del Framework Python

### 4.1 Punto de entrada y orquestación (`main.py`)

`main.py` crea un `Framework(base_dir)` y despacha por `sys.argv`:

| Comando | Función | Acción |
|---|---|---|
| *(sin args)* | `_run_default` | Si no hay config → lanza `ConfigWizard`; luego `framework.run()` (carga/valida/muestra resumen). **No** ejecuta transacciones. |
| `configure` | `_run_configure` | Asistente interactivo. |
| `config` | `_run_show_config` | Muestra la config (sin contraseña). |
| `test [--verbose]` | `_run_test` | Diagnóstico (`SAPDiagnostics`) o verbose (`SAPDebug`). |
| `session` | `_run_session` | Prueba el `SessionManager` (crea y cierra una sesión). |
| `resources` | `_run_resources` | Escanea y normaliza recursos VBS. |
| `run <TX>` | `_run_workflow` | **Flujo de automatización completo.** |
| `connections` / `login-test` / `state` / `popup` / `win-dialogs` / `native-dialog` | varios | Herramientas de diagnóstico independientes. |

### 4.2 Sistema de configuración

- `FrameworkConfig` es una `dataclass` con campos: `sap_logon_path`, `sap_connection`, `sap_system`, `system_name`, `sap_client`, `sap_language`, `sap_user`, `sap_password`, `exports_path`, `git_repo_path`.
- `ConfigManager` es la **única** vía de lectura/escritura: `load()` (JSON → dataclass), `save()` (JSON con `indent=2, ensure_ascii=False`), `validate()` (campos obligatorios + existencia de `sap_logon_path`), `get_summary()` (enmascara la contraseña con `*`).
- `ConfigWizard` recolecta cada campo, detecta `saplogon.exe` en rutas comunes, **descubre conexiones SAP Logon via COM** (`tasklist` + `GetObject("SAPGUI")`), y persiste con `ConfigManager`.
- El archivo `settings.json` está en `.gitignore` (contiene credenciales en texto plano; es una decisión de confianza-local, no un secreto versionado).

### 4.3 Sistema de recursos y extracción VBS

`ResourceManager.scan()` implementa el ciclo:

```
descubrir *.vbs → clasificar (hash SHA256 vs metadata) → metadata.json → workflow → extraer+normalizar
```

- `Resource` calcula SHA256 y `last_modified`; su `transaction` se deriva del **nombre del directorio padre**.
- Clasificación por hash: `NEW`, `UNCHANGED`, `UPDATED`, `DELETED`.
- `ResourceExtractor.extract()`:
  1. Lee el VBS detectando **BOM UTF-16 LE** (`\xff\xfe`) con fallback UTF-8.
  2. Ignora líneas vacías, comentarios (`'`) e **infraestructura VBS** (`Set `, `If `, `WScript.`, `.maximize`, `.caretPosition`, `.setFocus`, `.CreateSession`).
  3. Aplica `ExportPattern` primero (estado acumulativo de `DY_PATH` + `DY_FILENAME`), luego los patrones en orden de `ALL_PATTERNS` (SendVKey → Rows → DoubleClick → Press → Select → SetText).
  4. Produce `workflow.raw.json` con `steps`, `ignored` y `statistics`.
- Los **patrones** (`core/patterns/`) son clases con `matches(line) → PatternMatch | None`, usando regex sobre `session.findById("...").<acción>`.

### 4.4 Normalización a lenguaje SAF

`WorkflowNormalizer.normalize(raw)` aplica reglas en orden y hace *passthrough* del resto:

| Entrada raw | Regla | Salida SAF |
|---|---|---|
| `set_text` en campo `okcd` | `_norm_start_transaction` | `start_transaction` (con `transaction`) |
| `send_vkey` valor `0` | `_norm_confirm` | `confirm` |
| `send_vkey` valor `8` | `_norm_execute` | `execute` |
| `export` | `_norm_export_file` | `export_file` (conserva `filename`, agrega `path_source: framework_configuration`) |
| `set_text` (otros campos) | passthrough | `set_field` (field, value, target) |
| `press_button` / `select_menu` / `double_click` | passthrough | idem (solo `target`) |
| `send_vkey` (otros valores) | passthrough | `send_vkey` (value) |
| `select_rows` / `current_row` | passthrough | idem (value, target) |

Esto produce el `workflow.json` en lenguaje SAF (ej. el de MB52 tiene 13 pasos).

### 4.5 Execution Engine

`ExecutionEngine.run(workflow)`:

```
enable_login() en SessionManager
create_session()                     ← sesión propia del Framework
for cada step:
    handler = ActionRegistry.get(step.action)
    si action == "export_file": step.data["export_path"] = config.exports_path
    handler.execute(step, com)       ← actúa sobre COM
    waiter.wait_ready()              ← espera "no busy + wnd[0]"
_verify_exports(workflow)            ← comprueba existencia/tamaño del TXT
close_framework_session()            ← en finally
```

- `ActionRegistry` es un diccionario de clase; los handlers se auto-registran con `@ActionRegistry.register("...")` al importarse. `_ensure_actions_loaded()` importa explícitamente los 8 módulos de `actions/`.
- El Engine **no conoce clases concretas**: resuelve por nombre de acción.

### 4.6 Manejo de excepciones

- `core/exceptions.py` define una única excepción de dominio: `ConnectionUnavailableError` (indica que el diálogo nativo de error de conexión fue detectado y cerrado).
- `ExecutionEngine.run()` captura cualquier `Exception`, imprime el error y retorna `False` (no propaga); garantiza el cierre de sesión en `finally`.
- `SAPRecoveryEngine._open_connection()` transforma el fallo de `OpenConnection` en `ConnectionUnavailableError` tras intentar cerrar el diálogo nativo; `main._run_workflow` lo captura específicamente.

---

## 5. Funcionamiento interno del Portal Web

### 5.1 Arranque y orden de carga

`index.html` carga los scripts en este orden (importante porque dependen de símbolos globales definidos por los anteriores):

```
app.js → parser.js → smartSearch.js → search.js → materialViewer.js → table.js
```

`app.js` registra el evento `DOMContentLoaded` y ejecuta:

```
1. _loadImageIndex()      → fetch images/materials/material-index.json → window.MaterialImages (Set)
2. _loadAndRender()       → loadMB52() → renderTable() → _setupSearch()
3. setInterval(_checkForUpdates, 30000)   → polling
```

### 5.2 Procesamiento y lectura de datos (`parser.js`)

`loadMB52()`:
1. `fetch("data/MB52.txt")` → texto.
2. **Pre-procesado**: une líneas partidas (descripciones largas que SAP exporta en dos renglones; una línea que no empieza con tab/espacio y cuya anterior sí lo hace se concatena).
3. **Detección dinámica de cabecera**: busca la primera línea con ≥3 campos no vacíos cuyo primer campo no vacío sea texto; calcula un `headerOffset` para alinear registros que empiezan con tabs.
4. **Construye filas**: cada registro con ≥3 campos cuyo primer campo no vacío sea numérico (código de material) se convierte en objeto `{columna: valor}`.
5. Descarta filas sin `Material` (p. ej. totales de SAP).
6. Calcula `fileHash` (hash simple), extrae la fecha del contenido (formato `DD.MM.YYYY`) y los headers HTTP `ETag`/`Last-Modified`.

**Principio clave:** no asume nombres de columna fijos; todo es dinámico (robustez ante cambios de formato del reporte).

### 5.3 Búsqueda (`search.js` + `smartSearch.js`)

- `SmartSearch.normalize()`: string seguro → trim → minúsculas → quita acentos (NFD) → quita todo lo no alfanumérico.
- `SmartSearch.matches(row, term)` recorre `Object.keys(row)` y asigna puntuación: **exacto = 300**, **empieza con = 200**, **contiene = 100**.
- `filterMaterials(rows, text)` devuelve filas con `matched`, ordenadas por score descendente.

### 5.4 Generación de tabla (`table.js`)

`renderTable(headers, rows)`:
- **Columna calculada** "Valor Unitario" = `Valor libre util. / LibrUtiliz` (formateada como `Q…` con `parseNumber`/`formatCurrency`), insertada tras "Valor libre util.".
- Encabezados y filas generados dinámicamente; `_clasificarColumna()` aplica clases CSS (`col-expand`, `col-fixed`, `col-number`) por heurística de nombre.
- `sanitizeDisplayValue()` corrige caracteres mal codificados (mojibake Windows-1252 → UTF-8).
- Si un `Material` está en `window.MaterialImages`, añade el icono `📷`.
- Registra **una sola vez** un listener de clic en `<tbody>` que abre `MaterialViewer` con el objeto de la fila.

### 5.5 Visualizaciones e imágenes (`materialViewer.js`)

- Al hacer clic en una fila, `MaterialViewer.open(row, headers)` crea un **modal overlay** con código de material, descripción y un área de foto.
- `_loadMaterialImage(code)` intenta cargar `images/materials/<code>.jpg` de forma asíncrona; si falla, muestra el placeholder "Sin fotografía disponible".

### 5.6 Estructura de datos JSON

`material-index.json` tiene la forma:
```json
{ "version": 1, "generated": "2026-11-23T19:09:36+00:00", "materials": ["210225", "301420", ...] }
```
El Portal lo consume como `Set` de códigos con fotografía.

### 5.7 Relación entre módulos del frontend

```
app.js ──(llama)──> parser.js (loadMB52)
   │                   │
   │              renderTable (table.js)
   │                   │  (lee window.MaterialImages)
   │                   └──> MaterialViewer (materialViewer.js)
   │
   └──(búsqueda)──> search.js ──(delega)──> smartSearch.js
                         │
                         └──> renderTable (tabla filtrada)
```

La comunicación es por **funciones globales** y un estado global en `app.js` (`_allHeaders`, `_allRows`, `_currentFilter`, `window.MaterialImages`, etc.), coherente con una SPA vanilla sin bundler.

---

## 6. Flujo completo de ejecución de una transacción

Para `python main.py run MB52` (o `run_mb52.bat`):

```
[1] main._run_workflow(framework, "MB52")
      │  verifica config → config_manager.load()
      │  carga resources/MB52/workflow.json → Workflow.load()
      ▼
[2] SessionManager(config).enable_login()
    ExecutionEngine(session_manager)  → _ensure_actions_loaded()
      │
      ▼
[3] engine.run(workflow):
      ├─ session_manager.create_session()
      │     └─ _connect(): GetObject("SAPGUI") → .GetScriptingEngine
      │         └─ SAPRecoveryEngine.ensure_ready()   ← (login activado)
      │              └─ loop detect→actuar (SAPStateDetector + acciones)
      │
      ├─ por cada step:
      │     handler = ActionRegistry.get(step.action)
      │     handler.execute(step, com)   ← acciones SAP reales
      │     SAPWaiter.wait_ready()
      │
      ├─ _verify_exports()   ← existe web/data/MB52.txt + tamaño
      └─ close_framework_session()
      ▼
[4] Si workflow_ok:
      ├─ ImageIndexGenerator(base_dir).generate()
      │     └─ web/images/materials/material-index.json
      └─ GitManager(git_repo_path).publish()
            └─ commit selectivo de web/data/MB52.txt → push origin main
```

El caso MB52 concretamente ejecuta (del `workflow.json`):
`start_transaction mb52` → `confirm` → `press_button` (variante de layout) → `set_field` (planta/texto "FRAMEWORK 1.0") → `set_field` (creador) → `press_button` (ejecutar variante) → `execute` (F8) → `select_menu` (menú exportar) → `select_menu` (opción hoja de cálculo) → `press_button` (confirmar) → `export_file` (DY_PATH/DY_FILENAME) → `press_button` (btn[11], ejecuta exportación) → `send_vkey 3` (F3, volver).

---

## 7. Flujo de información entre Framework y Portal Web

La integración es por **sistema de archivos + Git**, sin API ni base de datos:

```
SAP GUI (MB52)
   │ SAP GUI Scripting (COM)
   ▼
Framework (ExecutionEngine → export_file)
   │ escribe directamente en exports_path = …/web/data/MB52.txt
   ▼
web/data/MB52.txt  ◄─────────────── consumido por parser.js
   │
   │  (además) ImageIndexGenerator
   ▼
web/images/materials/material-index.json  ◄── consumido por app.js (Set)
   │
   ▼
GitManager: git add web/data/MB52.txt → commit → push origin main
   ▼
GitHub Actions (deploy-pages.yml) → GitHub Pages
   ▼
Portal Web (index.html + JS) → tabla + búsqueda + fotos
```

**Qué componente genera cada archivo y quién lo consume:**

| Archivo | Genera | Consume | Formato |
|---|---|---|---|
| `web/data/MB52.txt` | Framework (`export_file`) | `parser.js` | Texto delimitado por tabs (SAP) |
| `web/images/materials/material-index.json` | Framework (`ImageIndexGenerator`) | `app.js` | JSON (`{version, generated, materials[]}`) |
| `web/images/materials/*.jpg` | (manual/proceso externo) | `table.js`, `materialViewer.js` | JPEG/PNG/etc. |
| `resources/MB52/workflow.json` | Framework (`WorkflowNormalizer`) | `ExecutionEngine` | JSON (lenguaje SAF) |
| `resources/MB52/workflow.raw.json` | Framework (`ResourceExtractor`) | `WorkflowNormalizer` (intermedio) | JSON |
| `resources/MB52/metadata.json` | Framework (`ResourceManager`) | `ResourceManager` (detección de cambios) | JSON |

**Sincronización de la información publicada:** el punto de convergencia es `exports_path` apuntando a `web/data`. Cada ejecución sobrescribe `MB52.txt` (y `ExportFileHandler` elimina el archivo previo para evitar el popup "¿reemplazar?"). El índice de imágenes se regenera tras cada ejecución exitosa, y `GitManager` publica selectivamente solo ese archivo. El Portal se actualiza por **polling cada 30 s** comparando `ETag`/`Last-Modified` (evita descargar el body si no cambió).

---

## 8. Integración con SAP GUI Scripting

SAF usa **SAP GUI Scripting** a través de **COM** (`pywin32`), replicando el patrón oficial del grabador VBS:

```
GetObject("SAPGUI")            → SapGuiAuto
SapGuiAuto.GetScriptingEngine  → Application     (PROPIEDAD, no método)
Application.Children(i)        → GuiConnection
Connection.Children(j)         → GuiSession
Session.findById("wnd[0]/…")   → control de UI
Session.Info.*                 → metadatos de sesión (solo lectura)
```

Puntos de diseño relevantes:

- **`SAPSession` encapsula la `GuiSession`**: nunca expone el COM directamente (excepto `_get_com_session()` reservado al `ExecutionEngine`). Sus propiedades (`system`, `client`, `user`, `transaction`, `program`, `screen`) se leen de `session.Info`.
- **`SessionManager` nunca toca sesiones del usuario**: crea una sesión exclusiva del Framework mediante la estrategia de **captura por conteo** (`Children.Count` antes/después de `CreateSession()`), porque el retorno de `CreateSession()` no es confiable en SAP GUI Scripting. Tras capturarla, **nunca** se re-busca por posición; se usa la referencia almacenada.
- **Cierre de sesión** con triple intento: `Close()` → `CloseSession()` → `findById("wnd[0]").Close()`.
- **Espera inteligente** (`SAPWaiter`): reemplaza `time.sleep` fijo por polling (~100 ms) sobre `session.Busy`, `wnd[N]`, controles o transacción activa.
- **Recuperación automática** (`SAPRecoveryEngine`): máquina detectar→actuar (hasta 5 ciclos) sobre estados de `SAPStateDetector` (`CLOSED`, `LOGON`, `LOGIN_SCREEN`, `AUTHENTICATED`, `FRAMEWORK_SESSION`, `CONNECTING`, `ERROR_POPUP`, `UNKNOWN`).
- **Login como máquina de estados** (`LoginManager`): espera pantalla de login → completa mandante/usuario/contraseña → envía Enter → espera sesión → valida `SystemName`.
- **Diálogos nativos Win32** (`NativeDialogManager`): cierra el diálogo de error de conexión (clase `#32770`, proceso `saplogon.exe`) enviando `BM_CLICK` vía `SendMessage` al botón con ID=2 (sin mouse).

---

## 9. Integración con Git y publicación

`GitManager.publish()` implementa una publicación **selectiva y defensiva**:

```
1. validate_repository()              → existe la ruta y tiene .git
2. _has_unpushed_commits()            → git rev-list --count origin/main..HEAD
     └─ si > 0 → solo _push_with_retry()   (NO hace add/commit)
3. has_changes()                      → git status --porcelain -- web/data/MB52.txt
     └─ sin cambios → finaliza sin publicar
4. commit(mensaje "Actualización MB52 - <timestamp>")
     └─ git add web/data/MB52.txt     ← SOLO ese archivo (evita colar otros cambios)
        git commit -m ...
5. _push_with_retry()                 → git push origin main
     └─ hasta 3 intentos: inmediato → 5 s → 10 s
```

Diseño destacable:
- **`_PUBLISH_FILE = "web/data/MB52.txt"`**: el commit automático solo incluye el dato exportado; cambios no relacionados del desarrollador no se cuelan.
- **`push origin main` explícito** (no depende del upstream local).
- Los **reintentos del push** no repiten `add`/`commit`, solo reintentan `push`.
- La **publicación de páginas** la hace GitHub Actions (`deploy-pages.yml`) al recibir el push a `main`, desplegando `./web`.

El historial Git muestra el ciclo real: commits recurrentes `"Actualización MB52 - <fecha>"` (del Framework) intercalados con `"actualizacion de imagen(es)"` (fotografías).

---

## 10. Principales clases, módulos y sus relaciones

**Clases/núcleo del dominio:**

| Clase | Ubicación | Relaciones |
|---|---|---|
| `Framework` | `core/framework.py` | Compone `ConfigManager`; es el contexto de `main.py`. |
| `ConfigManager` / `FrameworkConfig` | `config/config_manager.py` | Única vía de config; consumida por casi todo el núcleo. |
| `ConfigWizard` | `config/config_wizard.py` | Usa `ConfigManager`; descubre conexiones via COM. |
| `Resource` / `ResourceStatus` | `core/resource.py` | Entrada de `ResourceManager`. |
| `ResourceManager` | `core/resource_manager.py` | Orquesta `ResourceExtractor` + `WorkflowNormalizer`. |
| `ResourceExtractor` | `core/resource_extractor.py` | Usa `core.patterns.ALL_PATTERNS` + `ExportPattern`. |
| `WorkflowRaw` / `WorkflowRawStep` | `core/workflow_raw.py` | Modelo intermedio (VBS). |
| `WorkflowNormalizer` | `core/workflow_normalizer.py` | `raw → Workflow`. |
| `Workflow` / `WorkflowStep` | `core/workflow.py` | Modelo SAF; entrada de `ExecutionEngine`. |
| `ActionRegistry` | `core/action_registry.py` | Registro acción→handler; puente al `actions/`. |
| `ExecutionEngine` | `core/execution_engine.py` | Depende de `SessionManager`, `ActionRegistry`, `SAPWaiter`, `ConfigManager`. |
| `SessionManager` | `core/session_manager.py` | Produce `SAPSession`; usa `SAPRecoveryEngine`. |
| `SAPSession` | `core/sap_session.py` | Envuelve `GuiSession` (COM). |
| `SAPWaiter` | `core/sap_waiter.py` | Espera inteligente usada por Engine/Login/Recovery. |
| `SAPStateDetector` | `core/sap_state_detector.py` | Proporciona `SAPStateInfo` a `SAPRecoveryEngine`. |
| `SAPRecoveryEngine` | `core/sap_recovery_engine.py` | Compone `SAPConnector`, `LoginManager`, `NativeDialogManager`, `SAPWaiter`. |
| `SAPConnector` | `core/sap_connector.py` | Garantiza SAP Logon en ejecución. |
| `LoginManager` | `core/login_manager.py` | Login como máquina de estados. |
| `ImageIndexGenerator` | `core/image_index_generator.py` | Genera `material-index.json`. |
| `GitManager` | `core/git_manager.py` | Publica `web/data/MB52.txt`. |

**Módulos de diagnóstico (solo lectura, no usados en el flujo de producción):** `SAPDiagnostics`, `SAPDebug`, `SAPPopupManager`, `ConnectionExplorer`, `OpenConnectionTester`, `WindowsDialogExplorer`, `NativeDialogManager` (este último sí se usa en recuperación).

**Diagrama de dependencias simplificado (producción):**

```
ConfigManager ◄────────── SessionManager ──► SAPRecoveryEngine ──► SAPConnector
     ▲                        │                      │                LoginManager
     │                        │                      └────────────► NativeDialogManager
     │                        ▼
     │                  SAPSession ──► SAPWaiter
     │                        │
     └── ExecutionEngine ◄────┘
             │
             ├──► ActionRegistry ◄── actions/* (decorador)
             ├──► Workflow (cargado desde workflow.json)
             └──► (post) ImageIndexGenerator · GitManager
```

**Relación clave de desacoplamiento:** `ResourceExtractor` (dominio VBS) y `WorkflowNormalizer` (dominio SAP) y `ExecutionEngine` (dominio SAF) **no se importan entre sí**; se comunican a través de artefactos intermedios (`workflow.raw.json`, `workflow.json`).

---

## 11. Decisiones de diseño y criterios arquitectónicos

1. **Separación en dos componentes (Framework vs Portal)** que comparten repo pero no código: el backend automatiza SAP (Windows + COM), el frontend es estático (GitHub Pages). No hay servidor de aplicación; el "contrato" es un archivo TXT + un JSON de índice.

2. **Lenguaje intermedio SAF (pipeline VBS → raw → SAF):** desacopla el formato generado por SAP Recorder (frágil, específico de la versión) de la ejecución. Añadir una transacción nueva es "añadir un recurso VBS", no reescribir el motor. Cada etapa conoce solo su dominio.

3. **Patrones desacoplados (`core/patterns/`):** cada instrucción VBS reconocible es una clase con una regex; añadir reconocimiento nuevo es añadir un patrón. `ExportPattern` se maneja aparte por su estado acumulativo (`DY_PATH` + `DY_FILENAME`).

4. **Registro de acciones por decorador (`ActionRegistry`):** el `ExecutionEngine` no conoce handlers concretos; el acoplamiento es solo por el *nombre de acción*. Añadir una acción es crear una clase con `@register`.

5. **Gestión de sesiones aislada:** el Framework **nunca** opera sobre sesiones del usuario; siempre crea la suya y solo la cierra la suya (`SessionManager` + `SAPSession`). La captura por conteo reconoce la no-confiabilidad del retorno de `CreateSession()`.

6. **Recuperación automática del estado SAP** (detectar→actuar, máquina de estados): hace el sistema robusto frente a SAP Logon cerrado, sin conexión, pantalla de login o popups de error, sin intervención humana.

7. **Espera inteligente en vez de `sleep` fijo:** evita *flaky* tests de timing; se espera el estado real de SAP (`Busy`, ventanas, controles).

8. **Exportación dirigida por configuración:** el path de exportación del VBS se descarta y se toma de `settings.json` (`path_source: framework_configuration`). Así el mismo workflow es portable y el destino (`web/data`) se controla centralmente.

9. **Integración Python↔JavaScript por archivos:** sin API; el TXT y el JSON son los puntos de contrato. El frontend es **genérico** (detecta columnas dinámicamente) para sobrevivir a cambios de formato del reporte SAP.

10. **Publicación Git selectiva y defensiva:** solo se versiona `web/data/MB52.txt` (no cambios no relacionados), se detectan commits pendientes previos, y el push tiene reintentos con backoff. La publicación de páginas es responsabilidad de CI (GitHub Actions), no del Framework.

11. **Diagnóstico como ciudadano de primera clase:** numerosos subcomandos y módulos de solo lectura (`test`, `state`, `connections`, `login-test`, `popup`, `win-dialogs`, `native-dialog`) reflejan una estrategia de "comprender el entorno antes de actuar".

12. **Credenciales fuera del repositorio:** `config/settings.json` está en `.gitignore`; la seguridad se apoya en el aislamiento local más que en cifrado (limitación conocida del enfoque actual).

---

## 12. Glosario de términos y conceptos propios

| Término | Definición |
|---|---|
| **SAF** | SAP Automation Framework. |
| **Workflow SAF** | Secuencia de pasos en lenguaje interno (`start_transaction`, `set_field`, `execute`, …) lista para ejecutar; se persiste en `workflow.json`. |
| **Workflow RAW** | Representación estructurada del VBS antes de interpretación semántica; se persiste en `workflow.raw.json`. |
| **Recurso (Resource)** | Un archivo `.vbs` gestionado por el Framework, con hash, estado y metadata. |
| **Patrón (Pattern)** | Clase que reconoce una instrucción VBS concreta mediante regex. |
| **Normalización** | Transformación de un paso VBS a un paso SAF con significado de dominio SAP. |
| **Passthrough** | Transferencia de un paso raw al workflow SAF sin interpretación. |
| **Handler de acción** | Clase (`actions/*`) que ejecuta una acción SAF sobre la sesión COM. |
| **ActionRegistry** | Registro central acción → handler (patrón registro/decorador). |
| **Execution Engine** | Motor que recorre y ejecuta los pasos de un workflow SAF. |
| **Session Manager** | Administrador de sesiones SAP (conexión COM, creación/cierre de sesión propia). |
| **SAPSession** | Abstracción que encapsula una `GuiSession` COM, sin exponerla. |
| **SAPWaiter** | Motor de espera inteligente basado en el estado real de SAP. |
| **SAPStateDetector** | Detector jerárquico del estado SAP (Connection→Session→Window→Controls). |
| **SAPRecoveryEngine** | Motor que lleva SAP al estado autenticado (detectar→actuar). |
| **LoginManager** | Login SAP implementado como máquina de estados. |
| **SAPConnector** | Garantiza que SAP Logon esté en ejecución y su COM listo. |
| **SAP GUI Scripting** | API de scripting de SAP GUI expuesta vía COM. |
| **`findById`** | Método COM para localizar un control SAP por ruta (`wnd[0]/tbar[0]/okcd`). |
| **`okcd`** | Campo de comandos de SAP (donde se teclea el código de transacción). |
| **`sendVKey N`** | Envío de tecla virtual: `0` = Enter, `3` = F3, `8` = F8. |
| **`DY_PATH` / `DY_FILENAME`** | Campos del diálogo de exportación SAP (ruta y nombre de archivo). |
| **`wnd[0]` / `wnd[1]`** | Ventana principal / ventana modal (popup) de una sesión SAP. |
| **Material index** | `material-index.json`: lista de códigos de material con fotografía. |
| **Portal Web** | Interfaz estática (HTML/CSS/JS) que consulta los datos exportados. |
| **Polling** | Verificación periódica (30 s) del portal para detectar datos nuevos. |
| **GitManager** | Módulo de publicación selectiva en Git (`web/data/MB52.txt`). |
| **Comandos de diagnóstico** | Subcomandos CLI de solo lectura (`test`, `state`, `connections`, …). |
