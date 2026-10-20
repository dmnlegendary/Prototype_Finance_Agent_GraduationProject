// Listas largas (categorías, proveedores, íconos…): al principio se ven pocas opciones y el resto
// sale con el botón "Mostrar más". Una lista se marca con data-colapsable (y data-limite="3" para
// cambiar cuántas se ven). Lo que ya está elegido siempre se queda a la vista, y un elemento con
// data-siempre (por ejemplo el botón "Nueva") nunca se esconde.

function opcionesDeLaLista(lista) {
  return Array.from(lista.children).filter(function (el) {
    return el.tagName !== 'INPUT' && !el.hasAttribute('data-siempre');
  });
}

function estaElegida(opcion) {
  return opcion.classList.contains('activo') || !!opcion.querySelector('input:checked');
}

function botonDeLaLista(lista) {
  let boton = lista.nextElementSibling;
  if (boton && boton.classList.contains('btn-mostrar-mas')) return boton;
  boton = document.createElement('button');
  boton.type = 'button';
  boton.className = 'btn-mostrar-mas';
  boton.addEventListener('click', function () {
    lista.dataset.expandido = lista.dataset.expandido === '1' ? '0' : '1';
    actualizarColapsable(lista);
  });
  lista.insertAdjacentElement('afterend', boton);
  return boton;
}

function actualizarColapsable(lista) {
  const limite = parseInt(lista.dataset.limite || '3', 10);
  const expandido = lista.dataset.expandido === '1';
  const opciones = opcionesDeLaLista(lista);
  let escondidas = 0;

  opciones.forEach(function (opcion, i) {
    const visible = expandido || i < limite || estaElegida(opcion);
    opcion.classList.toggle('colapsado-oculto', !visible);
    if (!visible) escondidas++;
  });

  const boton = botonDeLaLista(lista);
  boton.style.display = opciones.length > limite ? '' : 'none';
  boton.textContent = expandido ? 'Mostrar menos' : 'Mostrar más (' + escondidas + ')';
}

// vuelve a calcular todas las listas de una zona (por ejemplo, después de llenar el formulario de edición)
function actualizarColapsables(raiz) {
  (raiz || document).querySelectorAll('[data-colapsable]').forEach(actualizarColapsable);
}

document.addEventListener('DOMContentLoaded', function () {
  actualizarColapsables(document);
  // al elegir una opción, la lista se acomoda sola (la elegida se queda visible)
  document.addEventListener('change', function (evento) {
    const lista = evento.target.closest ? evento.target.closest('[data-colapsable]') : null;
    if (lista) actualizarColapsable(lista);
  });
});
