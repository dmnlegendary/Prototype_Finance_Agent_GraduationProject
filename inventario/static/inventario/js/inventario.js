/*
 * JS de `inventario`.
 *
 * Ya no hay "estados" de demostración ni paneles superpuestos con datos de
 * ejemplo: cada pantalla (alta de producto, editar producto, proveedores,
 * alertas) es una página real de Django, servida por su propia vista.
 *
 * Lo único que sigue siendo interacción del lado del cliente es:
 *   1) Abrir/cerrar el panel del AVI (todavía sin conectar a un LLM real).
 *   2) El cálculo en vivo del margen al capturar costo/precio de un
 *      producto (solo cosmético: el margen real siempre se recalcula en
 *      el servidor a partir de `Producto.margen_porcentaje`).
 */

function openAvi() {
  document.getElementById('aviPanel').classList.add('open');
  document.getElementById('aviOverlay').classList.add('open');
}

function closeAvi() {
  document.getElementById('aviPanel').classList.remove('open');
  document.getElementById('aviOverlay').classList.remove('open');
}

function calcMargen() {
  const costoInput = document.getElementById('id_costo');
  const precioInput = document.getElementById('id_precio_venta');
  const label = document.getElementById('margenLabel');
  const fill = document.getElementById('margenFill');
  if (!costoInput || !precioInput || !label || !fill) return;

  const costo = parseFloat(costoInput.value) || 0;
  const precio = parseFloat(precioInput.value) || 0;
  if (precio > 0) {
    const margen = ((precio - costo) / precio * 100).toFixed(1);
    label.textContent = margen + '%';
    const anchoBarra = Math.min(Math.max(margen, 0), 60);
    fill.style.width = anchoBarra + '%';
    fill.style.background =
      margen < 15 ? 'var(--color-danger)' : margen < 25 ? 'var(--color-warning)' : 'var(--color-success)';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const costoInput = document.getElementById('id_costo');
  const precioInput = document.getElementById('id_precio_venta');
  if (costoInput && precioInput) {
    costoInput.addEventListener('input', calcMargen);
    precioInput.addEventListener('input', calcMargen);
  }
});
