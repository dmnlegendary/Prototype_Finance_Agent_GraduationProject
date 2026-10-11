// JS de inventario: el picker de "modificar producto", el cálculo en vivo
// del margen, y el modal de nueva categoría. Abrir/cerrar AVI y modales
// genéricos vive en static/js/app.js.

function abrirNuevaCategoria(origen) {
  document.getElementById('categoriaOrigen').value = origen;
  openModal('categoria-nueva');
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

// ---- Pantalla de alertas: búsqueda instantánea + filtro por color ----
let nivelElegido = '';

// quita los acentos para que "jabon" encuentre "Jabón"
function sinAcentos(texto) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function filtrarAlertas() {
  const buscador = document.getElementById('buscarAlerta');
  if (!buscador) return;
  const texto = sinAcentos(buscador.value.trim().toLowerCase());
  let visibles = 0;

  document.querySelectorAll('#listaAlertas .alert-item').forEach(function (item) {
    const coincideNombre = sinAcentos(item.dataset.nombre || '').includes(texto);
    const coincideNivel = !nivelElegido || item.dataset.nivel === nivelElegido;
    const mostrar = coincideNombre && coincideNivel;
    item.style.display = mostrar ? 'flex' : 'none';
    if (mostrar) visibles += 1;
  });

  const aviso = document.getElementById('sinResultadosAlertas');
  if (aviso) aviso.style.display = visibles === 0 ? 'block' : 'none';
}

function elegirNivel(boton) {
  nivelElegido = boton.dataset.nivel;
  document.querySelectorAll('.chip-nivel').forEach(function (chip) { chip.classList.remove('activo'); });
  boton.classList.add('activo');
  filtrarAlertas();
}

// ---- Catálogo: búsqueda instantánea (espera a que dejes de escribir) ----
let esperaBusqueda = null;

function buscarEnInventario() {
  clearTimeout(esperaBusqueda);
  esperaBusqueda = setTimeout(function () {
    document.getElementById('formBuscarInventario').submit();
  }, 450);
}

// al cargar, el cursor se queda al final del texto buscado
document.addEventListener('DOMContentLoaded', function () {
  const caja = document.getElementById('buscarInventario');
  if (caja && caja.value) {
    caja.focus();
    caja.setSelectionRange(caja.value.length, caja.value.length);
  }
});

// ---- "Modificar productos": busca en el servidor mientras escribes ----
let esperaModificar = null;

function buscarParaModificar(texto) {
  clearTimeout(esperaModificar);
  const caja = document.getElementById('buscarModificar');
  const lista = document.getElementById('listaModificar');

  if (!texto.trim()) {
    lista.innerHTML = '<p style="font-size:13px;color:var(--text-faint);text-align:center;">Escribe para buscar entre tus productos.</p>';
    return;
  }

  esperaModificar = setTimeout(function () {
    fetch(caja.dataset.url + '?q=' + encodeURIComponent(texto.trim()))
      .then(function (r) { return r.json(); })
      .then(function (datos) {
        lista.innerHTML = '';
        if (!datos.resultados.length) {
          lista.innerHTML = '<p style="font-size:13px;color:var(--text-faint);text-align:center;">No encontré ese producto.</p>';
          return;
        }
        datos.resultados.forEach(function (p) {
          const enlace = document.createElement('a');
          enlace.className = 'provider-card picker-item';
          enlace.style.textDecoration = 'none';
          enlace.href = caja.dataset.urlPanel + '?abrir=' + p.id;
          enlace.innerHTML = ''
            + '<div class="prov-avatar"></div>'
            + '<div class="prov-info"><div class="prov-name"></div><div class="prov-contact"></div></div>'
            + '<i class="bi bi-chevron-right" style="color:var(--text-faint);"></i>';
          // textContent para que un nombre con símbolos raros no rompa la página
          enlace.querySelector('.prov-avatar').textContent = p.icono;
          enlace.querySelector('.prov-name').textContent = p.nombre;
          enlace.querySelector('.prov-contact').textContent = '$' + p.precio_venta + ' · ' + parseFloat(p.stock) + ' pzas';
          lista.appendChild(enlace);
        });
      })
      .catch(function () {
        lista.innerHTML = '<p style="font-size:13px;color:var(--text-faint);text-align:center;">No pude buscar, intenta de nuevo.</p>';
      });
  }, 250);
}
