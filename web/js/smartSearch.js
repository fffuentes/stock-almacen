/**
 * smartSearch.js — Motor de búsqueda inteligente para el Portal MB52.
 *
 * Módulo independiente que concentra toda la lógica de comparación
 * de texto. Search.js delega en este módulo para determinar si una
 * fila coincide con el texto buscado.
 *
 * Principios:
 *  - Sin conocer nombres de columnas
 *  - Recorre dinámicamente Object.keys(row)
 *  - Ignora mayúsculas/minúsculas
 *  - Tres niveles de prioridad: exacto → empieza → contiene
 */

const SmartSearch = (function () {
    "use strict";

    /**
     * Normaliza un texto para comparación:
     *  1. Conversión segura a String
     *  2. Trim de espacios
     *  3. Minúsculas
     *  4. Eliminación de acentos (NFD)
     *  5. Eliminación de TODO carácter no alfanumérico
     *
     * @param {*} texto — Puede ser string, number, null, undefined, etc.
     * @returns {string} Texto normalizado (solo a-z y 0-9).
     */
    function normalize(texto) {
        return String(texto ?? "")
            .trim()
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-z0-9]/g, "");
    }

    /**
     * Determina si una fila coincide con el texto buscado y asigna
     * una puntuación (score) según la calidad de la coincidencia.
     *
     * @param {Object}   row        — Fila del dataset.
     * @param {string}   searchText — Texto ingresado por el usuario.
     * @returns {{ matched: boolean, score: number }}
     */
    function matches(row, searchText) {
        if (!searchText) return { matched: false, score: 0 };

        const term = normalize(searchText);
        let bestScore = 0;

        // Recorrer TODAS las propiedades del objeto dinámicamente
        for (const key of Object.keys(row)) {
            const valor = normalize(row[key]);

            if (valor === term) {
                bestScore = Math.max(bestScore, 300);   // Coincidencia exacta
            } else if (valor.startsWith(term)) {
                bestScore = Math.max(bestScore, 200);   // Empieza con
            } else if (valor.includes(term)) {
                bestScore = Math.max(bestScore, 100);   // Contiene
            }
        }

        return {
            matched: bestScore > 0,
            score: bestScore,
        };
    }

    // ── API pública ──────────────────────────────────────────────
    return {
        normalize,
        matches,
    };
})();
