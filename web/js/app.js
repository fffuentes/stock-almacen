console.log("SAP Automation Framework Web");

// ── Estado global del Portal ─────────────────────────────────────────
let _allHeaders = [];       // Nombres de columna detectados
let _allRows = [];          // Arreglo completo de objetos (sin filtrar)
let _lastFileHash = null;   // Hash del último MB52.txt cargado
let _lastETag = null;       // ETag del último archivo (para polling ligero)
let _lastModified = null;   // Last-Modified del último archivo
let _currentFilter = "";    // Texto actual del buscador

/** ── Punto de entrada del Portal ─────────────────────────────────── */
document.addEventListener("DOMContentLoaded", async () => {
    await _loadAndRender();

    // Iniciar polling cada 30 segundos
    setInterval(_checkForUpdates, 30000);
});

/** ── Carga completa: download → parse → render ───────────────────── */
async function _loadAndRender() {
    const statusEl = document.querySelector(".status-value.status-pending");
    try {
        if (statusEl) statusEl.textContent = "Cargando...";

        const { headers, rows, fileHash, fileDate, etag, lastModified } = await loadMB52();

        // Guardar datos originales
        _allHeaders = headers;
        _allRows = rows;
        _lastFileHash = fileHash;
        _lastETag = etag;
        _lastModified = lastModified;

        // Renderizar tabla completa
        renderTable(headers, rows);

        // Configurar búsqueda en tiempo real (solo primera vez)
        if (!window.__searchConfigured) {
            _setupSearch();
            window.__searchConfigured = true;
        } else {
            _applyCurrentFilter();
        }

        // Actualizar fecha con la del archivo real
        _updateFileDate(fileDate);

        if (statusEl) {
            statusEl.textContent = "Datos cargados";
            statusEl.classList.remove("status-pending");
            statusEl.classList.add("status-ok");
        }

        console.log(`[_loadAndRender] OK — ${rows.length} registros`);
    } catch (err) {
        console.error("app.js: error durante la carga:", err);
        if (statusEl) {
            statusEl.textContent = "Error de actualización";
            statusEl.classList.remove("status-ok");
            statusEl.classList.add("status-pending");
        }
    }
}

/** ── Polling optimizado: detectar cambios vía headers HTTP ────────── */
async function _checkForUpdates() {
    try {
        const url = "data/MB52.txt?t=" + Date.now();
        const resp = await fetch(url, {
            method: "GET",
            cache: "no-cache",
        });

        if (!resp.ok) return;

        // Leer headers ligeros primero
        const etag = resp.headers.get("ETag") || "";
        const lastMod = resp.headers.get("Last-Modified") || "";

        // Si ambos headers coinciden con los últimos, sin cambios
        if (etag && lastMod && etag === _lastETag && lastMod === _lastModified) {
            return; // sin cambios, sin descargar body
        }

        // Cambio detectado → descargar y recargar
        console.log("[poll] Cambio detectado — recargando...");
        const statusEl = document.querySelector(".status-value.status-ok");
        if (statusEl) statusEl.textContent = "Actualizando...";

        // Guardar nuevos headers
        _lastETag = etag;
        _lastModified = lastMod;

        await _loadAndRender();
    } catch (err) {
        console.warn("[poll] Error al verificar actualización:", err);
    }
}

/** ── Hash simple para detectar cambios ───────────────────────────── */
function _simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const ch = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + ch;
        hash |= 0;
    }
    return hash.toString(36);
}

/** ── Actualizar fecha del archivo en el header ────────────────────── */
function _updateFileDate(fileDate) {
    const fechaEl = document.querySelectorAll(".status-value")[0];
    if (fechaEl && fileDate) {
        fechaEl.textContent = fileDate;
    }
}

/** ── Re-aplicar filtro actual después de recarga ──────────────────── */
function _applyCurrentFilter() {
    const searchInput = document.querySelector(".search-input");
    if (!searchInput || !searchInput.value) return;

    const term = searchInput.value;
    const filtered = filterMaterials(_allRows, term);
    renderTable(_allHeaders, filtered);
}

/** ── Configurar búsqueda en tiempo real ──────────────────────────── */
function _setupSearch() {
    const searchInput = document.querySelector(".search-input");
    if (!searchInput) return;

    searchInput.disabled = false;

    searchInput.addEventListener("input", () => {
        _currentFilter = searchInput.value;
        const filtered = filterMaterials(_allRows, _currentFilter);
        renderTable(_allHeaders, filtered);
    });
}
