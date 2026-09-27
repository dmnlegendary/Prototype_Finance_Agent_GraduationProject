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
      + '<form method="post" action="/ventas/carrito/agregar/' + producto.id + '/" class="dropdown-item" style="cursor:pointer;" onclick="this.submit()">'
      + '<input type="hidden" name="csrfmiddlewaretoken" value="' + document.querySelector('[name=csrfmiddlewaretoken]').value + '">'
      + '<span>' + producto.icono + ' ' + producto.nombre + ' — $' + producto.precio_venta + '</span>'
      + '<button type="button" class="btn-select">Seleccionar</button>'
      + '</form>';
  });
  caja.innerHTML = html;
  caja.style.display = 'block';
}

function actualizarRelojVenta() {
  const ahora = new Date();
  const fechaEl = document.getElementById('fechaActual');
  const horaEl = document.getElementById('horaActual');
  if (fechaEl) fechaEl.textContent = ahora.toLocaleDateString('es-MX');
  if (horaEl) horaEl.textContent = ahora.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
}

let filaCarritoSeleccionada = null;

function seleccionarFilaCarrito(tr) {
  if (filaCarritoSeleccionada) filaCarritoSeleccionada.classList.remove('selected');
  filaCarritoSeleccionada = tr;
  tr.classList.add('selected');
}

document.addEventListener('keydown', function (event) {
  if (!filaCarritoSeleccionada) return;
  if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;

  if (event.key === '+') {
    event.preventDefault();
    filaCarritoSeleccionada.querySelector('form[action*="/mas/"]').submit();
  } else if (event.key === '-') {
    event.preventDefault();
    filaCarritoSeleccionada.querySelector('form[action*="/menos/"]').submit();
  }
});

document.addEventListener('DOMContentLoaded', function () {
  actualizarRelojVenta();
  setInterval(actualizarRelojVenta, 30000);

  const params = new URLSearchParams(window.location.search);
  const seleccionadoPk = params.get('seleccionado');
  if (seleccionadoPk) {
    const fila = document.querySelector('.cart-table tr[data-pk="' + seleccionadoPk + '"]');
    if (fila) seleccionarFilaCarrito(fila);
    if (window.history.replaceState) {
      params.delete('seleccionado');
      const query = params.toString();
      window.history.replaceState({}, '', window.location.pathname + (query ? '?' + query : ''));
    }
  }

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
