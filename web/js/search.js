/**
 * search.js — Motor de búsqueda en tiempo real para el Portal MB52.
 *
 * Busca en TODAS las columnas del dataset de forma dinámica,
 * sin conocer los nombres de las columnas. No asume que exista
 * "Material", "Descripción" ni ninguna columna en particular.
 */

/**
 * Filtra los registros según un texto de búsqueda.
 *
 * Recorre dinámicamente TODAS las propiedades de cada fila
 * y compara sus valores contra el texto ingresado. Si el
 * texto está vacío, retorna el arreglo completo sin cambios.
 *
 * La comparación ignora mayúsculas/minúsculas.
 *
 * Orden de prioridad en los resultados:
 *   1. Coincidencia exacta (el valor de alguna propiedad es
 *      idéntico al texto buscado).
 *   2. Empieza con (el valor comienza con el texto buscado).
 *   3. Contiene (el valor contiene el texto en cualquier posición).
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

    const term = searchText.trim().toLowerCase();

    // Clasificar cada fila en uno de tres niveles de prioridad
    const exactas = [];
    const empieza = [];
    const contiene = [];

    for (const row of rows) {
        let mejorNivel = 0; // 0 = no coincide, 1 = contiene, 2 = empieza, 3 = exacta

        // Recorrer TODAS las propiedades del objeto dinámicamente
        for (const key of Object.keys(row)) {
            const valor = String(row[key] ?? "").toLowerCase();

            if (valor === term) {
                mejorNivel = Math.max(mejorNivel, 3);
            } else if (valor.startsWith(term) && mejorNivel < 2) {
                mejorNivel = Math.max(mejorNivel, 2);
            } else if (valor.includes(term) && mejorNivel < 1) {
                mejorNivel = Math.max(mejorNivel, 1);
            }
        }

        // Asignar al grupo correspondiente
        if (mejorNivel === 3) {
            exactas.push(row);
        } else if (mejorNivel === 2) {
            empieza.push(row);
        } else if (mejorNivel === 1) {
            contiene.push(row);
        }
        // mejorNivel === 0 → no se incluye
    }

    // Concatenar en orden de prioridad
    return [...exactas, ...empieza, ...contiene];
}
