console.log("SAP Automation Framework Web");

// ── Estado global del Portal ─────────────────────────────────────────
let _allHeaders = [];   // Nombres de columna detectados
let _allRows = [];      // Arreglo completo de objetos (sin filtrar)

/**
 * Punto de entrada del Portal MB52.
 *
 * 1. Lee el archivo MB52.txt mediante el parser dinámico.
 * 2. Guarda el arreglo original en variables globales.
 * 3. Configura el listener de búsqueda en tiempo real.
 * 4. Renderiza la tabla completa.
 */
document.addEventListener("DOMContentLoaded", async () => {
    try {
        const { headers, rows } = await loadMB52();

        // ── DIAGNÓSTICO ───────────────────────────────────────────
        console.log("[app.js] headers.length:", headers.length);
        console.log("[app.js] rows.length:", rows.length);
        console.log("[app.js] headers:", headers);
        if (rows.length > 0) {
            console.log("[app.js] primer registro:", JSON.stringify(rows[0], null, 2));
        } else {
            console.log("[app.js] primer registro: N/A");
        }
        // ──────────────────────────────────────────────────────────

        // Guardar datos originales
        _allHeaders = headers;
        _allRows = rows;

        // Renderizar tabla completa
        renderTable(headers, rows);

        // Configurar búsqueda en tiempo real
        _setupSearch();

    } catch (err) {
        console.error("app.js: error durante la carga inicial:", err);
        // Mantener el estado vacío.
    }
});

/**
 * Configura el listener "input" sobre el cuadro de búsqueda.
 *
 * Cada vez que el usuario escribe, se filtran los datos originales
 * y se re-renderiza la tabla SIN modificar el arreglo _allRows.
 */
function _setupSearch() {
    const searchInput = document.querySelector(".search-input");
    if (!searchInput) {
        return;
    }

    // Habilitar el input (estaba disabled en la interfaz inicial)
    searchInput.disabled = false;

    searchInput.addEventListener("input", () => {
        const term = searchInput.value;
        const filtered = filterMaterials(_allRows, term);
        renderTable(_allHeaders, filtered);
    });
}
