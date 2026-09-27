// JS de inventario: abrir/cerrar el panel del AVI (aún sin LLM conectado)
// y el cálculo en vivo del margen al capturar costo/precio.

function openAvi() {
  document.getElementById('aviPanel').classList.add('open');
  document.getElementById('aviOverlay').classList.add('open');
}

function closeAvi() {
  document.getElementById('aviPanel').classList.remove('open');
  document.getElementById('aviOverlay').classList.remove('open');
}

function openModal(id) {
  const modal = document.getElementById('modal-' + id);
  if (modal) modal.classList.add('open');
}

function closeModal(id) {
  const modal = document.getElementById('modal-' + id);
  if (modal) modal.classList.remove('open');
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
