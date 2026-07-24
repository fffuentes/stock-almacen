/**
 * search.js — Coordinador de búsqueda para el Portal MB52.
 *
 * Maneja el evento input del buscador y delega toda la lógica de
 * comparación en SmartSearch (smartSearch.js).
 *
 * La lógica de filtrado, prioridad y normalización reside
 * exclusivamente en SmartSearch.
 */

/**
 * Filtra los registros según un texto de búsqueda.
 *
 * Delega la comparación de cada fila en SmartSearch.matches() y
 * ordena los resultados por puntuación (score) descendente.
 *
 * @param {Object[]} rows       — Arreglo original de objetos.
 * @param {string}   searchText — Texto ingresado por el usuario.
 * @returns {Object[]} Arreglo filtrado y ordenado por relevancia.
 */
function filterMaterials(rows, searchText) {
    // Sin texto → devolver todo
    if (!searchText || searchText.trim() === "") {
        return rows;
    }

    const scored = [];

    for (const row of rows) {
        const result = SmartSearch.matches(row, searchText);

        if (result.matched) {
            scored.push({ row, score: result.score });
        }
    }

    // Ordenar por score descendente (mayor puntuación primero)
    scored.sort((a, b) => b.score - a.score);

    // Retornar solo las filas
    return scored.map((item) => item.row);
}
