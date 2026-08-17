/*
 * JS de `ventas`.
 *
 * El carrito, la búsqueda, el cobro y el ticket ahora son páginas y
 * formularios reales de Django (ver ventas/views.py) — ya no hay
 * "estados" de demostración que este archivo tuviera que mostrar/ocultar,
 * ni un toast/drawer con un ticket de ejemplo fijo.
 *
 * Lo único que sigue siendo interacción del lado del cliente es abrir y
 * cerrar el panel del AVI (todavía sin conectar a un LLM real).
 */

function openAvi() {
  document.getElementById('aviPanel').classList.add('open');
  document.getElementById('aviOverlay').classList.add('open');
}

function closeAvi() {
  document.getElementById('aviPanel').classList.remove('open');
  document.getElementById('aviOverlay').classList.remove('open');
}
