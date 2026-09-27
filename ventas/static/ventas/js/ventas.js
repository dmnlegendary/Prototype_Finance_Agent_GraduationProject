// Búsqueda instantánea de productos: se dispara sola mientras el usuario
// escribe (con un pequeño debounce), sin click ni Enter.
let buscarTimeout = null;

function renderResultadosBusqueda(datos) {
  const caja = document.getElementById('resultadosBusqueda');
  if (!datos.resultados || datos.resultados.length === 0) {
    caja.innerHTML = '<div class="dropdown-item"><span>Sin resultados para "' + datos.q + '".</span></div>';
    caja.style.display = 'block';
    return;
  }

  let html = '';
  datos.resultados.forEach(function (producto) {
    html += ''
      + '<form method="post" action="/ventas/carrito/agregar/' + producto.id + '/" class="dropdown-item">'
      + '<input type="hidden" name="csrfmiddlewaretoken" value="' + document.querySelector('[name=csrfmiddlewaretoken]').value + '">'
      + '<span>' + producto.icono + ' ' + producto.nombre + ' — $' + producto.precio_venta + '</span>'
      + '<button type="submit" class="btn-select">Seleccionar</button>'
      + '</form>';
  });
  caja.innerHTML = html;
  caja.style.display = 'block';
}

document.addEventListener('DOMContentLoaded', function () {
  const input = document.getElementById('buscarProducto');
  const caja = document.getElementById('resultadosBusqueda');
  if (!input) return;

  input.addEventListener('input', function () {
    const q = input.value.trim();
    clearTimeout(buscarTimeout);

    if (!q) {
      caja.style.display = 'none';
      caja.innerHTML = '';
      return;
    }

    buscarTimeout = setTimeout(function () {
      fetch('/ventas/buscar/?q=' + encodeURIComponent(q))
        .then(function (respuesta) { return respuesta.json(); })
        .then(renderResultadosBusqueda);
    }, 250);
  });

  document.addEventListener('click', function (event) {
    if (!event.target.closest('.search-wrapper')) {
      caja.style.display = 'none';
    }
  });
});
