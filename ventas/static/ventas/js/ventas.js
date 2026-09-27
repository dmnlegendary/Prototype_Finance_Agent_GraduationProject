// JS de ventas: solo abre/cierra el panel del AVI (aún sin LLM conectado).
// El carrito, cobro y ticket son formularios normales de Django.

function openAvi() {
  document.getElementById('aviPanel').classList.add('open');
  document.getElementById('aviOverlay').classList.add('open');
}

function closeAvi() {
  document.getElementById('aviPanel').classList.remove('open');
  document.getElementById('aviOverlay').classList.remove('open');
}
