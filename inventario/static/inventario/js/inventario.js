// JS de inventario: el picker de "modificar producto", el cálculo en vivo
// del margen, y el modal de nueva categoría. Abrir/cerrar AVI y modales
// genéricos vive en static/js/app.js.

function abrirNuevaCategoria(origen) {
  document.getElementById('categoriaOrigen').value = origen;
  openModal('categoria-nueva');
}

function filtrarPicker(texto) {
  const filtro = texto.trim().toLowerCase();
  document.querySelectorAll('#listaModificar .picker-item').forEach(function (item) {
    const nombre = item.getAttribute('data-nombre') || '';
    item.style.display = nombre.includes(filtro) ? 'flex' : 'none';
  });
}

function calcMargen() {
  const costoInput = document.getElementById('id_alta_costo');
  const precioInput = document.getElementById('id_alta_precio_venta');
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
  const costoInput = document.getElementById('id_alta_costo');
  const precioInput = document.getElementById('id_alta_precio_venta');
  if (costoInput && precioInput) {
    costoInput.addEventListener('input', calcMargen);
    precioInput.addEventListener('input', calcMargen);
  }
});
