/**
 * parser.js — Lector genérico del archivo MB52.txt.
 *
 * No asume nombres de columnas, no agrega columnas inexistentes,
 * no mapea campos fijos. Todo se detecta dinámicamente desde el TXT.
 *
 * Formato esperado (exportación SAP delimitada por tabulaciones):
 *
 *   Línea 1:     Fecha y título del reporte
 *   Líneas 2-3:  Vacías
 *   Línea 4:     Fila de encabezados (delimitados por TAB)
 *   Línea 5:     Vacía
 *   Línea 6+:    Filas de datos (misma cantidad de columnas que cabecera)
 */

/**
 * Resultado del parser.
 *
 * @typedef {Object} ParseResult
 * @property {string[]}   headers    — Nombres de columna detectados (orden original).
 * @property {Object[]}   rows       — Arreglo de objetos, cada clave = nombre de columna.
 * @property {number}     dataLines  — Líneas de datos procesadas.
 * @property {number}     skipped    — Líneas descartadas (vacías, cabecera, etc.).
 */

/**
 * Carga y analiza el archivo MB52.txt.
 *
 * Lee el archivo data/mb52.txt, detecta automáticamente la fila de
 * encabezados, extrae los nombres de columna exactamente como aparecen
 * en el TXT, y construye un arreglo de objetos con esas claves.
 *
 * @async
 * @returns {Promise<ParseResult>}
 * @throws {Error} Si el archivo no existe o no es accesible.
 */
async function loadMB52() {
    const url = "data/MB52.txt";

    // 1. Obtener el archivo como texto -----------------------------------
    let texto;
    try {
        const respuesta = await fetch(url);
        if (!respuesta.ok) {
            throw new Error(
                `No se pudo leer "${url}" (HTTP ${respuesta.status})`
            );
        }
        texto = await respuesta.text();
    } catch (err) {
        console.error("loadMB52: error al obtener el archivo:", err);
        throw err;
    }

    // 2. Pre-procesar: unir líneas partidas por saltos de línea SAP ────
    //    SAP exporta descripciones largas en dos líneas:
    //      \t\t3457052\t...\tDISPLAY EVD ITALIAN
    //      EVDIS00IT0 2FVEE0007\tUN\t1\t...
    //    La segunda línea NO empieza con tab → es continuación.
    const lineasCrudas = texto.split("\n");
    const lineas = [];
    for (let i = 0; i < lineasCrudas.length; i++) {
        const actual = lineasCrudas[i];
        // Si la línea NO empieza con tab ni espacio, y la anterior sí,
        // probablemente es continuación de una descripción partida.
        if (
            i > 0 &&
            actual.length > 0 &&
            actual[0] !== "\t" &&
            actual[0] !== " " &&
            lineasCrudas[i - 1].length > 0 &&
            (lineasCrudas[i - 1][0] === "\t" || lineasCrudas[i - 1][0] === " ")
        ) {
            // Unir con la línea anterior (remplazar salto de línea por espacio)
            lineas[lineas.length - 1] += " " + actual.trim();
        } else {
            lineas.push(actual);
        }
    }

    // ── DIAGNÓSTICO ───────────────────────────────────────────────
    console.log("--------------------------------");
    console.log("MB52 Parser");
    console.log("--------------------------------");
    console.log(`Cantidad de líneas leídas (crudas): ${lineasCrudas.length}`);
    console.log(`Cantidad de líneas tras unir partidas: ${lineas.length}`);
    // ──────────────────────────────────────────────────────────────

    // 3. Detectar cabecera dinámicamente --------------------------------
    //    Estrategia: buscar la primera línea que, tras split por tabs,
    //    tenga al menos 3 campos NO vacíos y cuyo primer campo NO vacío
    //    sea texto (no numérico). Esto maneja líneas que empiezan con
    //    tabs (campo[0] vacío).
    let headers = [];
    let headerIndex = -1;

    for (let i = 0; i < lineas.length; i++) {
        const campos = lineas[i].split("\t");

        // Encontrar el primer índice con valor no vacío (ignorando tabs iniciales)
        let primerNoVacio = "";
        let primerIndiceValido = -1;
        let camposNoVacios = 0;
        for (let idx = 0; idx < campos.length; idx++) {
            const limpio = campos[idx].trim();
            if (limpio.length > 0) {
                if (primerNoVacio === "") {
                    primerNoVacio = limpio;
                    primerIndiceValido = idx;
                }
                camposNoVacios++;
            }
        }

        if (camposNoVacios >= 3 && !/^\d/.test(primerNoVacio)) {
            // Es la cabecera: calcular offset y aplicarlo con slice.
            // Esto descarta tabs iniciales de forma dinámica (1, 2, N tabs).
            const headerOffset = primerIndiceValido;
            const headersCrudos = campos.slice(headerOffset).map((c) => c.trim());
            headers = headersCrudos;
            headerIndex = i;
            // Guardar offset para aplicarlo también a los registros
            window.__MB52_HEADER_OFFSET = headerOffset;
            break;
        }
    }

    if (headers.length === 0) {
        console.warn("loadMB52: no se detectó fila de encabezados.");
        console.log("--------------------------------");
        return { headers: [], rows: [], dataLines: 0, skipped: lineas.length };
    }

    // ── DIAGNÓSTICO ───────────────────────────────────────────────
    const headerOffset = window.__MB52_HEADER_OFFSET || 0;
    console.log(`Fila detectada como encabezado: línea ${headerIndex + 1}`);
    console.log(`Primer índice válido (headerOffset): ${headerOffset}`);
    console.log(`Encabezados detectados (${headers.length}): ${headers.join(" | ")}`);
    // ──────────────────────────────────────────────────────────────

    // 4. Procesar filas de datos (después de la cabecera) ---------------
    const rows = [];
    let dataLines = 0;
    let skipped = headerIndex + 1; // líneas anteriores + cabecera

    for (let i = headerIndex + 1; i < lineas.length; i++) {
        const camposCrudos = lineas[i].split("\t");
        // Aplicar el mismo offset que a los encabezados para alinear
        const offset = window.__MB52_HEADER_OFFSET || 0;
        const campos = camposCrudos.slice(offset);

        // Contar campos NO vacíos (ignorando tabs iniciales/finales)
        let camposNoVacios = 0;
        let primerNoVacio = "";
        for (const c of campos) {
            const limpio = c.trim();
            if (limpio.length > 0) {
                if (primerNoVacio === "") {
                    primerNoVacio = limpio;
                }
                camposNoVacios++;
            }
        }

        // Saltar líneas sin suficientes campos (vacías, separadores)
        if (camposNoVacios < 3) {
            skipped++;
            continue;
        }

        // Verificar que el primer campo no vacío sea numérico (material)
        if (!/^\d/.test(primerNoVacio)) {
            skipped++;
            continue;
        }

        // Construir objeto con los nombres de columna detectados
        const row = {};
        for (let c = 0; c < headers.length; c++) {
            const nombreCol = headers[c];
            // Si el nombre de columna está vacío (tabs extremos), ignorar
            if (nombreCol === "") {
                continue;
            }
            row[nombreCol] = (campos[c] || "").trim();
        }

        // ── LIMPIEZA: descartar filas sin Material (ej. TOTAL SAP) ──
        const primeraColumna = headers[0];
        if (!row[primeraColumna] || row[primeraColumna].trim() === "") {
            skipped++;
            continue;
        }
        // ───────────────────────────────────────────────────────────

        rows.push(row);
        dataLines++;
    }

    // ── DIAGNÓSTICO ───────────────────────────────────────────────
    console.log(`Cantidad de registros válidos: ${rows.length}`);
    console.log(`Cantidad de registros descartados: ${skipped}`);
    if (rows.length > 0) {
        console.log("Primer registro completo:", JSON.stringify(rows[0], null, 2));
        console.log("Último registro completo:", JSON.stringify(rows[rows.length - 1], null, 2));
    } else {
        console.log("Primer registro completo: N/A");
        console.log("Último registro completo: N/A");
    }
    console.log("--------------------------------");
    // ──────────────────────────────────────────────────────────────

    return { headers, rows, dataLines, skipped };
}
