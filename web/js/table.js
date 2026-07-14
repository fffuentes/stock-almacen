/**
 * table.js — Renderizado dinámico de la tabla del Portal MB52.
 *
 * No utiliza nombres de columna fijos. Tanto los encabezados como
 * las filas se generan a partir de los datos recibidos del parser.
 */

/**
 * Reemplaza caracteres de sustitución Unicode (�) por sus equivalentes
 * correctos cuando es posible inferirlos del contexto.
 *
 * Esta función es EXCLUSIVAMENTE visual. No modifica el dataset original.
 *
 * @param {string} valor — Texto original.
 * @returns {string} Texto corregido para mostrar.
 */
function sanitizeDisplayValue(valor) {
    if (!valor || typeof valor !== "string") {
        return valor;
    }

    // Reemplazar el carácter de sustitución Unicode (U+FFFD) y
    // caracteres similares de codificación dañada por sus equivalentes
    // más probables en un contexto SAP (exportación Windows-1252 → UTF-8).
    return valor
        .replace(/\uFFFD/g, "°")
        .replace(/�/g, "°")
        .replace(/Ã±/g, "ñ")
        .replace(/Ã¡/g, "á")
        .replace(/Ã©/g, "é")
        .replace(/Ã­/g, "í")
        .replace(/Ã³/g, "ó")
        .replace(/Ãº/g, "ú")
        .replace(/Â°/g, "°")
        .replace(/â„¢/g, "\u2122")
        .replace(/â€œ/g, "\u201C")
        .replace(/â€/g, "\u201D")
        .replace(/â€˜/g, "\u2018")
        .replace(/â€™/g, "\u2019")
        .replace(/â€"/g, "-")
        .replace(/â€“/g, "\u2013");
}

/**
 * Clasifica una columna según su nombre para aplicar estilos CSS.
 *
 * Reglas (sin hardcodear nombres específicos):
 *   - Columnas cuyo nombre contiene "texto", "breve", "descrip"
 *     o "material" (pero no solo "Material") → col-expand
 *   - Columnas cuyo nombre es exactamente "Material" → col-fixed
 *   - Columnas de 2-5 caracteres (códigos: Alm., UMB, etc.) → col-fixed
 *   - Columnas que contienen "valor", "util", "libre", "insp",
 *     "bloq", "cant", "stock" → col-number
 *   - El resto → sin clase (ancho automático)
 *
 * @param {string} headerName — Nombre de la columna.
 * @returns {string} Clase CSS (puede ser múltiple: "col-fixed col-number").
 */
function _clasificarColumna(headerName) {
    const nombre = headerName.toLowerCase();
    const clases = [];

    // Columna expansible: descripciones largas
    if (
        nombre.includes("texto") ||
        nombre.includes("breve") ||
        nombre.includes("descrip")
    ) {
        clases.push("col-expand");
        return clases.join(" "); // expand anula fixed/number
    }

    // Columna fija (códigos cortos)
    const len = headerName.trim().length;
    if (
        headerName.trim() === "Material" ||
        (len >= 2 && len <= 5 && !nombre.includes(" ") && !/\d/.test(headerName))
    ) {
        clases.push("col-fixed");
    }

    // Columna numérica
    if (
        nombre.includes("valor") ||
        nombre.includes("util") ||
        nombre.includes("libre") ||
        nombre.includes("insp") ||
        nombre.includes("bloq") ||
        nombre.includes("cant") ||
        nombre.includes("stock")
    ) {
        clases.push("col-number");
    }

    return clases.join(" ");
}

// ═══════════════════════════════════════════════════════════════
// Utilidades para columnas calculadas
// ═══════════════════════════════════════════════════════════════

/**
 * Convierte una cadena con formato SAP (comas para miles, punto decimal)
 * en un número flotante utilizable para cálculos.
 *
 * @param {string} raw — Valor crudo (ej: "93,375.02", "5,757", "0.00")
 * @returns {number}
 */
function parseNumber(raw) {
    if (!raw || raw === "—") return NaN;
    return parseFloat(String(raw).replace(/,/g, ""));
}

/**
 * Formatea un número como moneda para mostrar en columna monetaria.
 *
 * @param {number} value — Valor numérico.
 * @returns {string} Ej: "Q16.22", "Q1,253.80"
 */
function formatCurrency(value) {
    if (isNaN(value)) return "—";
    return "Q" + value.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

/**
 * Renderiza la tabla de resultados de forma completamente dinámica.
 *
 * @param {string[]} headers — Nombres de columna (del TXT).
 * @param {Object[]} rows    — Arreglo de objetos con clave = nombre de columna.
 */
function renderTable(headers, rows) {
    const count = rows ? rows.length : 0;

    // ── DIAGNÓSTICO ───────────────────────────────────────────────
    console.log(`[table.js] Cantidad de filas recibidas: ${count}`);
    console.log(`[table.js] Cantidad de columnas (original): ${headers.length}`);
    if (count === 0) {
        console.log("[table.js] Render cancelado: sin registros");
    }
    // ──────────────────────────────────────────────────────────────

    // ── COLUMNA CALCULADA: Valor Unitario ─────────────────────────
    // Trabajar sobre una copia de headers para no modificar el original.
    const tableHeaders = [...headers];
    const valorLibreIdx = tableHeaders.indexOf("Valor libre util.");
    const libreIdx = tableHeaders.indexOf("LibrUtiliz");
    const nuevaColumna = "Valor Unitario";

    if (valorLibreIdx !== -1 && libreIdx !== -1 && count > 0) {
        tableHeaders.splice(valorLibreIdx + 1, 0, nuevaColumna);

        for (const row of rows) {
            const valorLibre = parseNumber(row["Valor libre util."]);
            const libre = parseNumber(row["LibrUtiliz"]);

            if (libre === 0 || isNaN(libre) || isNaN(valorLibre)) {
                row[nuevaColumna] = "—";
            } else {
                row[nuevaColumna] = formatCurrency(valorLibre / libre);
            }
        }
    }
    // ──────────────────────────────────────────────────────────────

    const theadRow = document.querySelector(".results-table thead tr");
    const tbody = document.querySelector(".results-table tbody");
    const counter = document.querySelector(".results-counter strong");
    const emptyState = document.querySelector(".empty-state");
    const statusValue = document.querySelector(".status-value.status-pending");
    const regsValue = document.querySelectorAll(".status-value")[1];
    const fechaValue = document.querySelectorAll(".status-value")[0];

    // 1. Generar encabezados dinámicamente (con clases CSS) -------------
    if (theadRow) {
        theadRow.innerHTML = "";
        for (const h of tableHeaders) {
            const th = document.createElement("th");
            th.textContent = h;
            const clase = _clasificarColumna(h);
            if (clase) {
                th.className = clase;
            }
            theadRow.appendChild(th);
        }
    }

    // 2. Limpiar cuerpo de la tabla -------------------------------------
    tbody.innerHTML = "";

    // 3. Actualizar contador --------------------------------------------
    if (counter) {
        counter.textContent = count;
    }

    // 4. Sin registros: mostrar empty state -----------------------------
    if (!rows || count === 0) {
        if (emptyState) {
            emptyState.style.display = "flex";
        }
        if (statusValue) {
            statusValue.textContent = "Sin datos";
        }
        return;
    }

    // 5. Ocultar empty state --------------------------------------------
    if (emptyState) {
        emptyState.style.display = "none";
    }

    // 6. Insertar filas dinámicamente (con clases CSS por columna) ------
    const fragmento = document.createDocumentFragment();

    for (const row of rows) {
        const tr = document.createElement("tr");

        for (const h of tableHeaders) {
            const td = document.createElement("td");
            const valor = (row[h] !== undefined ? row[h] : "");
            td.textContent = sanitizeDisplayValue(valor);
            // Tooltip con el texto completo para columnas con ellipsis
            if (valor.length > 0) {
                td.title = valor;
            }
            const clase = _clasificarColumna(h);
            if (clase) {
                td.className = clase;
            }
            tr.appendChild(td);
        }

        fragmento.appendChild(tr);
    }

    tbody.appendChild(fragmento);

    // 7. Actualizar indicadores del header ------------------------------
    if (statusValue) {
        statusValue.textContent = "Datos cargados";
        statusValue.classList.remove("status-pending");
        statusValue.classList.add("status-ok");
    }
    if (regsValue) {
        regsValue.textContent = count;
    }
    if (fechaValue) {
        const ahora = new Date();
        fechaValue.textContent =
            ahora.toLocaleDateString("es-GT", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
            }) +
            " " +
            ahora.toLocaleTimeString("es-GT", {
                hour: "2-digit",
                minute: "2-digit",
            });
    }

    // ── DIAGNÓSTICO ───────────────────────────────────────────────
    console.log(`[table.js] Render completado: ${count} filas × ${tableHeaders.length} columnas.`);
    // ──────────────────────────────────────────────────────────────
}
