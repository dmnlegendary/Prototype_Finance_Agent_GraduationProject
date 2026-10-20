// JS de inventario: modal de edición único, "Ver más" por lotes, resurtir, importar,
// búsqueda instantánea y la pantalla de alertas. Abrir/cerrar AVI y modales
// genéricos vive en static/js/app.js.

function tokenCsrf() {
  const campo = document.querySelector('input[name=csrfmiddlewaretoken]');
  return campo ? campo.value : '';
}

function abrirNuevaCategoria(origen) {
  document.getElementById('categoriaOrigen').value = origen;
  openModal('categoria-nueva');
}

// ---- Margen en vivo (alta de producto) ----
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

// ---- Producto "a granel": cambia los textos a kilos ----
function actualizarUnidades(formulario) {
  const casilla = formulario.querySelector('input[name=a_granel]');
  const granel = casilla && casilla.checked;
  formulario.querySelectorAll('.txt-unidad').forEach(function (el) { el.textContent = granel ? '(kilos)' : '(piezas)'; });
  formulario.querySelectorAll('.txt-por-kilo').forEach(function (el) { el.textContent = granel ? 'por kilo ' : ''; });
}

document.addEventListener('DOMContentLoaded', function () {
  const costoInput = document.getElementById('id_alta_costo');
  const precioInput = document.getElementById('id_alta_precio_venta');
  document.querySelectorAll('.selector-icono').forEach(marcarIcono);
  if (costoInput && precioInput) {
    costoInput.addEventListener('input', calcMargen);
    precioInput.addEventListener('input', calcMargen);
  }

  document.querySelectorAll('form input[name=a_granel]').forEach(function (casilla) {
    const formulario = casilla.closest('form');
    casilla.addEventListener('change', function () { actualizarUnidades(formulario); });
    actualizarUnidades(formulario);
  });

  // al cargar, el cursor se queda al final del texto buscado
  const caja = document.getElementById('buscarInventario');
  if (caja && caja.value) {
    caja.focus();
    caja.setSelectionRange(caja.value.length, caja.value.length);
  }
});

// ---- Catálogo: búsqueda instantánea (espera a que dejes de escribir) ----
let esperaBusqueda = null;

function buscarEnInventario() {
  clearTimeout(esperaBusqueda);
  esperaBusqueda = setTimeout(function () {
    document.getElementById('formBuscarInventario').submit();
  }, 450);
}

// ---- Catálogo: "Ver más" (pide el siguiente lote de renglones) ----
function verMasProductos() {
  const boton = document.getElementById('verMasProductos');
  const cuerpo = document.getElementById('filasProductos');
  boton.disabled = true;
  boton.textContent = 'Cargando…';

  const url = boton.dataset.url + '?page=' + boton.dataset.siguiente + (boton.dataset.query ? '&' + boton.dataset.query : '');
  fetch(url)
    .then(function (r) { return r.json(); })
    .then(function (datos) {
      cuerpo.insertAdjacentHTML('beforeend', datos.html);
      boton.dataset.siguiente = datos.siguiente;
      const mostrados = cuerpo.querySelectorAll('tr:not(#filaVacia)').length;
      document.getElementById('resumenProductos').textContent = 'Mostrando ' + mostrados + ' de ' + boton.dataset.total + ' productos';
      if (!datos.hay_mas) document.getElementById('verMasProductosWrap').style.display = 'none';
    })
    .catch(function () {
      showToast('No pude cargar más productos. Revisa tu conexión.', 'info');
    })
    .finally(function () {
      boton.disabled = false;
      boton.textContent = 'Ver más';
    });
}

// ---- Ícono del producto: se elige de una lista y queda en un campo oculto ----
function marcarIcono(selector) {
  const campo = selector.querySelector('input');
  selector.querySelectorAll('.icono-opcion').forEach(function (boton) {
    boton.classList.toggle('activo', !!campo.value && boton.dataset.icono === campo.value);
  });
  // el ícono elegido siempre se queda a la vista aunque la lista esté recogida
  if (typeof actualizarColapsable === 'function') actualizarColapsable(selector);
}

function elegirIcono(boton) {
  const selector = boton.closest('.selector-icono');
  const campo = selector.querySelector('input');
  // tocar el que ya estaba elegido lo quita (el sistema pone uno según el nombre)
  campo.value = campo.value === boton.dataset.icono ? '' : boton.dataset.icono;
  marcarIcono(selector);
}

// ---- Editar producto: un solo formulario que se llena con los datos del producto ----
function abrirEdicion(pk, conErrores) {
  const form = document.getElementById('formEditar');
  form.action = form.dataset.urlModelo.replace('/0/', '/' + pk + '/');

  if (conErrores) {
    // el servidor ya regresó el formulario con lo que el usuario escribió y sus errores
    actualizarUnidades(form);
    form.querySelectorAll('.selector-icono').forEach(marcarIcono);
    actualizarColapsables(form);
    openModal('editar');
    return;
  }

  fetch(form.dataset.urlDatos.replace('/0/', '/' + pk + '/'))
    .then(function (r) { return r.json(); })
    .then(function (p) {
      ['nombre', 'descripcion', 'icono', 'costo', 'precio_venta', 'cantidad_actual', 'cantidad_minima', 'stock_ideal', 'codigo_barras']
        .forEach(function (campo) {
          const el = document.getElementById('id_editar_' + campo);
          if (el) el.value = p[campo] === null ? '' : p[campo];
        });
      form.querySelector('input[name=a_granel]').checked = p.a_granel;
      form.querySelectorAll('.selector-icono').forEach(marcarIcono);
      form.querySelectorAll('input[name=categoria]').forEach(function (radio) {
        radio.checked = String(radio.value) === String(p.categoria);
      });
      form.querySelectorAll('input[name=proveedor]').forEach(function (radio) {
        radio.checked = String(radio.value) === String(p.proveedor === null ? '' : p.proveedor);
      });
      form.querySelector('input[name=motivo]').value = '';
      document.getElementById('tituloEditar').textContent = p.pendiente_validacion ? 'Completar producto' : 'Editar producto';
      actualizarColapsables(form);
      actualizarUnidades(form);
      openModal('editar');
    })
    .catch(function () {
      showToast('No pude abrir el producto. Revisa tu conexión.', 'info');
    });
}

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
          const tarjeta = document.createElement('div');
          tarjeta.className = 'provider-card picker-item';
          tarjeta.style.cursor = 'pointer';
          tarjeta.innerHTML = ''
            + '<div class="prov-avatar"></div>'
            + '<div class="prov-info"><div class="prov-name"></div><div class="prov-contact"></div></div>'
            + '<i class="bi bi-chevron-right" style="color:var(--text-faint);"></i>';
          // textContent para que un nombre con símbolos raros no rompa la página
          tarjeta.querySelector('.prov-avatar').textContent = p.icono;
          tarjeta.querySelector('.prov-name').textContent = p.nombre;
          tarjeta.querySelector('.prov-contact').textContent = '$' + p.precio_venta + ' · ' + p.stock + ' ' + p.unidad;
          tarjeta.addEventListener('click', function () {
            closeModal('modificar-picker');
            abrirEdicion(p.id);
          });
          lista.appendChild(tarjeta);
        });
      })
      .catch(function () {
        lista.innerHTML = '<p style="font-size:13px;color:var(--text-faint);text-align:center;">No pude buscar, intenta de nuevo.</p>';
      });
  }, 250);
}

// ---- Resurtir: llegó mercancía (se registra como compra) ----
function abrirResurtir(boton) {
  const form = document.getElementById('formResurtir');
  const granel = boton.dataset.granel === '1';
  form.dataset.pk = boton.dataset.pk;
  form.dataset.granel = granel ? '1' : '0';
  document.getElementById('resurtirNombre').textContent = boton.dataset.nombre;
  document.getElementById('resurtirUnidad').textContent = granel ? 'kilos' : 'piezas';
  document.getElementById('resurtirCantidad').value = '';
  document.getElementById('resurtirCosto').value = boton.dataset.costo;
  document.getElementById('resurtirPrecio').value = boton.dataset.precio;
  document.getElementById('resurtirError').style.display = 'none';
  openModal('resurtir');
  document.getElementById('resurtirCantidad').focus();
}

function guardarResurtir(evento) {
  evento.preventDefault();
  const form = document.getElementById('formResurtir');
  const error = document.getElementById('resurtirError');
  const cantidad = document.getElementById('resurtirCantidad').value;
  const costo = document.getElementById('resurtirCosto').value;
  const precio = document.getElementById('resurtirPrecio').value;

  // el precio de venta nunca puede quedar por debajo de lo que cuesta (también se revisa en el servidor)
  if (costo && precio && Number(precio) < Number(costo)) {
    error.textContent = 'El precio de venta ($' + Number(precio).toFixed(2) + ') no puede ser menor al precio de compra ($' + Number(costo).toFixed(2) + '). Súbelo o revisa el costo.';
    error.style.display = 'block';
    return false;
  }

  if (window.Sinconexion && !window.Sinconexion.enLinea()) {
    window.Sinconexion.encolar('resurtir', { producto_id: Number(form.dataset.pk), cantidad: cantidad, costo: costo, precio_venta: precio })
      .then(function () {
        closeModal('resurtir');
        showToast('Sin internet: la mercancía se guardó en este dispositivo y se actualizará cuando regrese la conexión.', 'info');
      });
    return false;
  }

  fetch(form.dataset.urlModelo.replace('/0/', '/' + form.dataset.pk + '/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': tokenCsrf() },
    body: JSON.stringify({ cantidad: cantidad, costo: costo, precio_venta: precio }),
  })
    .then(function (r) { return r.json().then(function (datos) { return { ok: r.ok, datos: datos }; }); })
    .then(function (resultado) {
      if (!resultado.ok) {
        error.textContent = resultado.datos.mensaje || 'No se pudo agregar la mercancía.';
        error.style.display = 'block';
        return;
      }
      guardarAvisoPendiente(resultado.datos.mensaje);
      window.location.reload();
    })
    .catch(function () {
      error.textContent = 'No pude conectarme. Intenta de nuevo.';
      error.style.display = 'block';
    });
  return false;
}

// ---- Alta de producto sin internet: se guarda en el dispositivo y se manda después ----
document.addEventListener('submit', function (evento) {
  const form = evento.target.closest('form[data-formulario-alta]');
  if (!form || !window.Sinconexion || window.Sinconexion.enLinea()) return;

  evento.preventDefault();
  const datos = {};
  new FormData(form).forEach(function (valor, clave) { if (clave !== 'csrfmiddlewaretoken') datos[clave] = valor; });
  datos.a_granel = form.querySelector('input[name=a_granel]').checked;
  if (!datos.nombre || !datos.costo || !datos.precio_venta) {
    showToast('Escribe al menos el nombre, el precio de compra y el de venta.', 'info');
    return;
  }
  window.Sinconexion.encolar('alta_producto', datos).then(function () {
    form.reset();
    closeModal('alta');
    showToast('Sin internet: el producto se guardó en este dispositivo y se actualizará el sistema cuando regrese la conexión.', 'info');
  });
});

// ---- Pantalla de alertas: búsqueda instantánea, filtro por color y "Ver más" ----
let nivelElegido = '';
let paginaAlertas = 2;
let esperaAlertas = null;

function pedirAlertas(reiniciar) {
  const lista = document.getElementById('listaAlertas');
  const q = document.getElementById('buscarAlerta').value.trim();
  const pagina = reiniciar ? 1 : paginaAlertas;
  const url = lista.dataset.url + '?q=' + encodeURIComponent(q) + '&nivel=' + nivelElegido + '&page=' + pagina;

  fetch(url)
    .then(function (r) { return r.json(); })
    .then(function (datos) {
      if (reiniciar) lista.innerHTML = datos.html; else lista.insertAdjacentHTML('beforeend', datos.html);
      paginaAlertas = datos.siguiente;
      document.getElementById('verMasAlertasWrap').style.display = datos.hay_mas ? 'block' : 'none';
      document.getElementById('sinResultadosAlertas').style.display = datos.total === 0 ? 'block' : 'none';
    })
    .catch(function () {
      showToast('No pude cargar las alertas. Revisa tu conexión.', 'info');
    });
}

function buscarAlertas() {
  clearTimeout(esperaAlertas);
  esperaAlertas = setTimeout(function () { pedirAlertas(true); }, 250);
}

function elegirNivel(boton) {
  nivelElegido = boton.dataset.nivel;
  document.querySelectorAll('.chip-nivel').forEach(function (chip) { chip.classList.remove('activo'); });
  boton.classList.add('activo');
  pedirAlertas(true);
}

function verMasAlertas() {
  pedirAlertas(false);
}
