/**
 * materialViewer.js — Visor de material del Portal MB52.
 *
 * Responsable de mostrar un modal overlay con la información de un
 * material al hacer clic sobre una fila de la tabla.
 *
 * Diseñado para incorporar fotografías en fases futuras.
 */

const MaterialViewer = (function () {
    "use strict";

    let _overlay = null;
    let _currentRow = null;

    /**
     * Abre el visor con la información de la fila seleccionada.
     *
     * @param {Object} row — Fila del dataset (clave = nombre de columna).
     * @param {string[]} headers — Nombres de columna (para detectar campos).
     */
    function open(row, headers) {
        // Eliminar cualquier overlay anterior (máximo 1)
        document.querySelector(".mv-overlay")?.remove();
        _overlay = null;

        _currentRow = row;
        const materialCode = _safeText(row["Material"]);
        _createOverlay(row, headers, materialCode);
        document.body.appendChild(_overlay);

        // Animación de entrada
        requestAnimationFrame(() => {
            _overlay.classList.add("mv--visible");
        });

        // Cargar fotografía asíncronamente
        _loadMaterialImage(materialCode).then((imgEl) => {
            if (imgEl && _overlay) {
                const photoArea = _overlay.querySelector(".mv-photo-area");
                if (photoArea) {
                    photoArea.innerHTML = "";
                    photoArea.appendChild(imgEl);
                }
            }
        });
    }

    /**
     * Cierra el visor. Elimina el overlay del DOM inmediatamente.
     */
    function close() {
        if (_overlay) {
            _overlay.remove();
            _overlay = null;
        }
        _currentRow = null;
    }

    // ── Construcción del DOM del modal ─────────────────────────────

    function _createOverlay(row, headers) {
        // Contenedor principal (fondo oscuro)
        _overlay = document.createElement("div");
        _overlay.className = "mv-overlay";
        _overlay.addEventListener("click", (e) => {
            if (e.target === _overlay) close();
        });

        // Panel del modal
        const panel = document.createElement("div");
        panel.className = "mv-panel";

        // ── Cabecera ────────────────────────────────────────────
        const header = document.createElement("div");
        header.className = "mv-header";

        const title = document.createElement("h2");
        title.className = "mv-title";
        title.textContent = _safeText(row["Material"]) || "—";

        const closeBtn = document.createElement("button");
        closeBtn.className = "mv-close-btn";
        closeBtn.textContent = "✕";
        closeBtn.addEventListener("click", close);
        header.appendChild(title);
        header.appendChild(closeBtn);

        // ── Descripción ─────────────────────────────────────────
        const desc = document.createElement("p");
        desc.className = "mv-description";
        desc.textContent = _safeText(row["Texto breve material"]) || "—";

        // ── Área de fotografía (placeholder) ─────────────────────
        const photoArea = document.createElement("div");
        photoArea.className = "mv-photo-area";

        const photoPlaceholder = document.createElement("div");
        photoPlaceholder.className = "mv-photo-placeholder";
        photoPlaceholder.innerHTML =
            '<span class="mv-photo-icon">📷</span>' +
            '<span class="mv-photo-text">Sin fotografía disponible</span>';

        photoArea.appendChild(photoPlaceholder);

        // ── Ensamblar ───────────────────────────────────────────
        panel.appendChild(header);
        panel.appendChild(desc);
        panel.appendChild(photoArea);
        _overlay.appendChild(panel);
    }

    /**
     * Devuelve el texto de un valor de forma segura, manejando
     * caracteres de sustitución Unicode.
     *
     * @param {*} val
     * @returns {string}
     */
    function _safeText(val) {
        if (val === undefined || val === null) return "";
        const str = String(val);
        // Reemplazar carácter de sustitución Unicode
        return str.replace(/\uFFFD/g, "°").replace(/�/g, "°");
    }

    /**
     * Intenta cargar la fotografía del material.
     *
     * Busca: images/materials/<codigo>.jpg
     *
     * @param {string} materialCode — Código SAP del material.
     * @returns {Promise<HTMLImageElement|null>}
     */
    function _loadMaterialImage(materialCode) {
        if (!materialCode) return Promise.resolve(null);

        return new Promise((resolve) => {
            const img = document.createElement("img");
            img.className = "mv-photo";
            img.alt = "Fotografía " + materialCode;
            img.src = "images/materials/" + materialCode + ".jpg";

            img.onload = () => resolve(img);
            img.onerror = () => resolve(null);
        });
    }

    // ── API pública ──────────────────────────────────────────────
    return { open, close };
})();
