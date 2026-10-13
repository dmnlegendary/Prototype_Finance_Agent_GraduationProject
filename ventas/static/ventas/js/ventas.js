// Punto de venta. Habla con el servidor por JSON (sin recargar la página) y, cuando se
// pierde el internet, sigue funcionando con una copia del catálogo guardada en el
// dispositivo: las ventas se guardan en una cola y se mandan cuando regresa la conexión
// (ver static/js/sinconexion.js).

const POS = {
  carrito: 1,          // el carrito en el que trabaja esta pantalla (1 o 2)
  estado: null,        // el carrito tal como lo regresó el servidor (o el local si no hay internet)
  sinInternet: false,  // true mientras se trabaja con el carrito local
  local: { 1: nuevoLocal(), 2: nuevoLocal() },
  catalogo: [],        // copia del catálogo (para buscar sin internet)
  resultados: [],      // lo que muestra el buscador
  resaltado: -1,
  pendienteResurtir: null,
  productoGranel: null,
};

function nuevoLocal() {
  return { renglones: [], copiadoDelServidor: false };
}

function raiz() { return document.getElementById('posRaiz'); }
function rutaDe(atributo, id) { return raiz().dataset[atributo].replace('/0/', '/' + id + '/'); }
function csrf() { return document.querySelector('#formCsrfPos input[name=csrfmiddlewaretoken]').value; }
function avisar(texto, tipo) { showToast(texto, tipo || 'info'); }

// ------------------------------------------------------------------ comunicación con el servidor

async function llamar(ruta, metodo, cuerpo) {
  let respuesta;
  try {
    respuesta = await fetch(ruta, {
      method: metodo || 'GET',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
      credentials: 'same-origin',
    });
  } catch (e) {
    const error = new Error('sin conexión');
    error.red = true;
    throw error;
  }
  let datos = {};
  try { datos = await respuesta.json(); } catch (e) { datos = { sesion: true }; }
  return { estado: respuesta.status, ok: respuesta.ok && !datos.sesion, datos: datos };
}

// ------------------------------------------------------------------ dibujar el carrito


function pintar(estado) {
  POS.estado = estado;
  const cuerpo = document.getElementById('cuerpoCarrito');
  cuerpo.innerHTML = '';

  document.getElementById('folioActual').textContent = estado.folio ? '#' + String(estado.folio).padStart(4, '0') : 'sin folio (sin internet)';
  document.getElementById('totalCarrito').textContent = Number(estado.total).toFixed(2);

  const vacio = !estado.renglones.length;
  ['btnCobrar', 'btnCancelar'].forEach(function (id) {
    const boton = document.getElementById(id);
    boton.disabled = vacio;
    boton.style.opacity = vacio ? '.4' : '';
    boton.style.cursor = vacio ? 'not-allowed' : '';
  });

  if (vacio) {
    const fila = document.createElement('tr');
    fila.innerHTML = '<td colspan="5" style="text-align:center;color:var(--text-faint);padding:24px;"><i class="bi bi-cart3"></i> Carrito vacío. Busca un producto o escanea su código.</td>';
    cuerpo.appendChild(fila);
  }

  estado.renglones.forEach(function (r) {
    const fila = document.createElement('tr');
    fila.dataset.id = r.id;

    const celdaNombre = document.createElement('td');
    celdaNombre.textContent = r.icono + ' ' + r.nombre;
    fila.appendChild(celdaNombre);

    // la cantidad se puede escribir; en productos a granel se escribe en gramos
    const celdaCantidad = document.createElement('td');
    const caja = document.createElement('div');
    caja.className = 'qty';
    const menos = document.createElement('button');
    menos.type = 'button';
    menos.className = 'btn-qty-menos';
    menos.innerHTML = '&minus;';
    const entrada = document.createElement('input');
    entrada.type = 'number';
    entrada.className = 'qty-input';
    entrada.min = '0';
    entrada.step = r.a_granel ? '1' : '1';
    entrada.value = r.a_granel ? Math.round(parseFloat(r.cantidad) * 1000) : String(parseFloat(r.cantidad));
    entrada.title = r.a_granel ? 'Gramos' : 'Piezas';
    const mas = document.createElement('button');
    mas.type = 'button';
    mas.className = 'btn-qty-mas';
    mas.textContent = '+';
    caja.appendChild(menos);
    caja.appendChild(entrada);
    if (r.a_granel) {
      const unidad = document.createElement('span');
      unidad.className = 'qty-unidad';
      unidad.textContent = 'g';
      caja.appendChild(unidad);
    }
    caja.appendChild(mas);
    celdaCantidad.appendChild(caja);
    fila.appendChild(celdaCantidad);

    const paso = r.a_granel ? 100 : 1;
    const valorActual = function () { return parseFloat(entrada.value) || 0; };
    menos.addEventListener('click', function () { cambiarCantidad(r, Math.max(valorActual() - paso, 0)); });
    mas.addEventListener('click', function () { cambiarCantidad(r, valorActual() + paso); });
    entrada.addEventListener('change', function () { cambiarCantidad(r, valorActual()); });
    entrada.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); entrada.blur(); } });
    entrada.addEventListener('focus', function () { entrada.select(); });

    const celdaPrecio = document.createElement('td');
    celdaPrecio.className = 'right';
    celdaPrecio.textContent = '$' + Number(r.precio_unitario).toFixed(2) + (r.a_granel ? '/kg' : '');
    fila.appendChild(celdaPrecio);

    const celdaSubtotal = document.createElement('td');
    celdaSubtotal.className = 'right';
    celdaSubtotal.textContent = '$' + Number(r.subtotal).toFixed(2);
    fila.appendChild(celdaSubtotal);

    const celdaQuitar = document.createElement('td');
    const quitarBoton = document.createElement('button');
    quitarBoton.type = 'button';
    quitarBoton.className = 'btn-eliminar-item';
    quitarBoton.title = 'Quitar del carrito';
    quitarBoton.innerHTML = '<i class="bi bi-trash3"></i>';
    quitarBoton.addEventListener('click', function () {
      if (confirm('¿Quitar ' + r.nombre + ' del carrito?')) quitar(r);
    });
    celdaQuitar.appendChild(quitarBoton);
    fila.appendChild(celdaQuitar);

    cuerpo.appendChild(fila);
  });

  // pestañas de los carritos: cuál está activo y cuántos productos tiene cada uno
  document.querySelectorAll('.carrito-tab').forEach(function (tab) {
    tab.classList.toggle('activo', Number(tab.dataset.carrito) === POS.carrito);
  });
  const contadores = estado.contadores || {};
  Object.keys(contadores).forEach(function (n) {
    const el = document.getElementById('contadorCarrito' + n);
    if (el) el.textContent = contadores[n];
  });
}

// ------------------------------------------------------------------ carrito en el servidor

async function cargarCarrito(n) {
  if (modoSinInternet()) { pintar(estadoLocal()); return; }
  try {
    const r = await llamar(rutaDe('urlCarrito', n));
    if (r.datos.ok) { pintar(r.datos); }
  } catch (e) {
    caidaDeRed();
  }
}

function elegirCarrito(n) {
  POS.carrito = n;
  window.carritoActivo = n;
  try { localStorage.setItem('carrito_activo', String(n)); } catch (e) {}
  cargarCarrito(n);
  document.getElementById('buscarProducto').focus();
}

// Ejecuta una acción en el servidor y la pinta; si pasa algo, lo maneja.
// `reintento` es lo que se vuelve a ejecutar si el usuario agrega existencias.
async function accion(ruta, metodo, cuerpo, reintento) {
  if (modoSinInternet()) return false;
  try {
    const r = await llamar(ruta, metodo, cuerpo);
    if (r.datos.sesion) { avisar('Tu sesión terminó. Vuelve a iniciar sesión.', 'alerta'); return false; }
    if (r.ok && r.datos.ok) { pintar(r.datos); return r.datos; }
    if (r.estado === 409 && r.datos.error === 'sin_existencias') { pedirResurtir(r.datos, reintento); return false; }
    avisar(r.datos.mensaje || 'No se pudo completar la acción.', 'alerta');
    return false;
  } catch (e) {
    if (e.red) { caidaDeRed(); return false; }
    throw e;
  }
}

function agregar(productoId, cantidad) {
  if (modoSinInternet()) return agregarLocal(productoId, cantidad);
  const reintento = function () { return agregar(productoId, cantidad); };
  return accion(rutaDe('urlAgregar', POS.carrito), 'POST', { producto_id: productoId, cantidad: cantidad }, reintento);
}

function cambiarCantidad(renglon, cantidad) {
  if (modoSinInternet()) return cambiarCantidadLocal(renglon, cantidad);
  const reintento = function () { return cambiarCantidad(renglon, cantidad); };
  return accion(rutaDe('urlCantidad', renglon.id), 'POST', { cantidad: renglon.a_granel ? cantidad / 1000 : cantidad }, reintento)
    .then(function (resultado) { if (!resultado) cargarCarrito(POS.carrito); return resultado; });
}

function quitar(renglon) {
  if (modoSinInternet()) return quitarLocal(renglon);
  return accion(rutaDe('urlQuitar', renglon.id), 'POST', {});
}

async function cancelarVenta() {
  if (!POS.estado || !POS.estado.renglones.length) return;
  if (!confirm('¿Cancelar esta venta?')) return;
  if (modoSinInternet()) { POS.local[POS.carrito] = nuevoLocal(); pintar(estadoLocal()); return; }
  await accion(rutaDe('urlCancelar', POS.carrito), 'POST', {});
}

async function cobrarVenta() {
  if (!POS.estado || !POS.estado.renglones.length) return;
  if (modoSinInternet()) return cobrarLocal();

  try {
    const r = await llamar(rutaDe('urlCobrar', POS.carrito), 'POST', {});
    if (r.ok && r.datos.ok) {
      pintar(r.datos);
      mostrarTicket(r.datos.ticket, false);
      (r.datos.avisos || []).forEach(function (a) { avisar(a.texto, 'alerta'); });
      refrescarCatalogo();
    } else if (r.estado === 409 && r.datos.error === 'sin_existencias') {
      pedirResurtir(r.datos, cobrarVenta);
    } else {
      avisar(r.datos.mensaje || 'No se pudo cobrar.', 'alerta');
    }
  } catch (e) {
    if (e.red) { caidaDeRed(); } else { throw e; }
  }
}

// ------------------------------------------------------------------ ticket

function mostrarTicket(t, pendiente) {
  const caja = document.getElementById('ticketContenido');
  caja.innerHTML = '';

  const titulo = document.createElement('div');
  titulo.className = 'receipt-title';
  titulo.appendChild(document.createTextNode(t.tienda));
  titulo.appendChild(document.createElement('br'));
  const detalle = document.createElement('span');
  detalle.style.cssText = 'font-weight:400;font-size:12px;color:var(--text-muted)';
  const folio = t.folio ? ' · Folio #' + String(t.folio).padStart(4, '0') : ' · Folio pendiente';
  detalle.textContent = (t.ubicacion ? t.ubicacion + ' · ' : '') + t.fecha + ' · ' + t.hora + folio;
  titulo.appendChild(detalle);
  caja.appendChild(titulo);

  t.renglones.forEach(function (r) {
    const fila = document.createElement('div');
    fila.className = 'receipt-row';
    const izquierda = document.createElement('span');
    izquierda.textContent = r.nombre + ' x' + r.cantidad + ' ' + r.unidad;
    const derecha = document.createElement('span');
    derecha.textContent = '$' + Number(r.subtotal).toFixed(2);
    fila.appendChild(izquierda);
    fila.appendChild(derecha);
    caja.appendChild(fila);
  });

  const total = document.createElement('div');
  total.className = 'receipt-total';
  total.innerHTML = '<span>Total</span><span>$' + Number(t.total).toFixed(2) + '</span>';
  caja.appendChild(total);

  if (pendiente) {
    const nota = document.createElement('p');
    nota.style.cssText = 'font-size:12px;color:var(--alerta-900);margin:10px 0 0;';
    nota.textContent = 'Venta guardada sin internet. Se actualizará el sistema una vez que haya conexión.';
    caja.appendChild(nota);
  }
  openModal('ticket');
}

// ------------------------------------------------------------------ búsqueda, Enter y código de barras

let esperaBusqueda = null;

function esCodigo(texto) { return /^\d{6,}$/.test(texto); }

function pintarResultados(q) {
  const caja = document.getElementById('resultadosBusqueda');
  caja.innerHTML = '';
  POS.resaltado = POS.resultados.length ? 0 : -1;

  if (!POS.resultados.length) {
    const vacio = document.createElement('div');
    vacio.className = 'dropdown-item';
    vacio.innerHTML = '<span></span>';
    vacio.firstChild.textContent = 'Sin resultados para "' + q + '".';
    caja.appendChild(vacio);
    caja.style.display = 'block';
    return;
  }

  POS.resultados.forEach(function (p, i) {
    const item = document.createElement('div');
    item.className = 'dropdown-item' + (i === 0 ? ' resaltado' : '');
    item.style.cursor = 'pointer';
    const texto = document.createElement('span');
    texto.textContent = p.icono + ' ' + p.nombre + ' — $' + Number(p.precio_venta).toFixed(2) + (p.a_granel ? ' /kg' : '')
      + (Number(p.stock) <= 0 ? '  (sin existencias)' : '');
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'btn-select';
    boton.textContent = 'Seleccionar';
    item.appendChild(texto);
    item.appendChild(boton);
    item.addEventListener('click', function () { elegirResultado(p); });
    caja.appendChild(item);
  });
  caja.style.display = 'block';
}

async function buscar(q) {
  if (modoSinInternet()) {
    POS.resultados = buscarLocal(q);
    pintarResultados(q);
    return;
  }
  try {
    const r = await llamar(raiz().dataset.urlBuscar + '?q=' + encodeURIComponent(q));
    POS.resultados = r.datos.resultados || [];
    pintarResultados(q);
  } catch (e) {
    if (e.red) {
      caidaDeRed();
      POS.resultados = buscarLocal(q);
      pintarResultados(q);
    }
  }
}

function cerrarResultados() {
  document.getElementById('resultadosBusqueda').style.display = 'none';
  POS.resultados = [];
  POS.resaltado = -1;
}

function elegirResultado(p) {
  const entrada = document.getElementById('buscarProducto');
  entrada.value = '';
  cerrarResultados();
  entrada.focus();
  if (p.a_granel) { abrirGranel(p); return; }
  agregar(p.id, 1);
}

async function buscarPorCodigo(codigo) {
  let producto = null;
  if (modoSinInternet()) {
    producto = POS.catalogo.find(function (p) { return p.codigo && p.codigo === codigo; }) || null;
  } else {
    try {
      const r = await llamar(raiz().dataset.urlCodigo + '?c=' + encodeURIComponent(codigo));
      producto = r.datos.encontrado ? r.datos.producto : null;
    } catch (e) {
      if (e.red) {
        caidaDeRed();
        producto = POS.catalogo.find(function (p) { return p.codigo && p.codigo === codigo; }) || null;
      }
    }
  }

  const entrada = document.getElementById('buscarProducto');
  entrada.value = '';
  cerrarResultados();
  if (producto) { elegirResultado(producto); return; }

  document.getElementById('codigoDesconocido').textContent = codigo;
  const enlace = document.getElementById('enlaceAltaCodigo');
  enlace.href = raiz().dataset.urlAlta + '?nuevo_codigo=' + encodeURIComponent(codigo);
  openModal('codigo');
}

async function alPresionarEnter() {
  const entrada = document.getElementById('buscarProducto');
  const valor = entrada.value.trim();
  if (!valor) return;
  clearTimeout(esperaBusqueda);

  // un lector de códigos "escribe" el código y da Enter
  if (esCodigo(valor)) { buscarPorCodigo(valor); return; }

  if (!POS.resultados.length) await buscar(valor);
  if (POS.resultados.length) {
    elegirResultado(POS.resultados[Math.max(POS.resaltado, 0)]);
  } else {
    avisar('No encontré ese producto. Puedes cobrarlo con "No encontrado".', 'info');
  }
}

function moverResaltado(delta) {
  if (!POS.resultados.length) return;
  POS.resaltado = (POS.resaltado + delta + POS.resultados.length) % POS.resultados.length;
  document.querySelectorAll('#resultadosBusqueda .dropdown-item').forEach(function (el, i) {
    el.classList.toggle('resaltado', i === POS.resaltado);
  });
}

// ------------------------------------------------------------------ producto a granel

function abrirGranel(producto) {
  POS.productoGranel = producto;
  document.getElementById('granelNombre').textContent = producto.nombre + ' ($' + Number(producto.precio_venta).toFixed(2) + '/kg)';
  document.getElementById('granelGramos').value = '250';
  openModal('granel');
  const caja = document.getElementById('granelGramos');
  caja.focus();
  caja.select();
}

function ponerGramos(gramos) { document.getElementById('granelGramos').value = gramos; }

function confirmarGranel(evento) {
  evento.preventDefault();
  const gramos = parseFloat(document.getElementById('granelGramos').value);
  if (!gramos || gramos <= 0) return false;
  closeModal('granel');
  agregar(POS.productoGranel.id, gramos / 1000);
  document.getElementById('buscarProducto').focus();
  return false;
}

// ------------------------------------------------------------------ regla de oro: sin existencias

function pedirResurtir(datos, reintento) {
  POS.pendienteResurtir = { datos: datos, reintento: reintento };
  const p = datos.producto;
  document.getElementById('sinExistenciasTexto').textContent = datos.mensaje.replace(' ¿Quieres agregar más al inventario?', '');
  document.getElementById('sinExistenciasUnidad').textContent = p.a_granel ? 'kilos' : 'piezas';
  document.getElementById('sinExistenciasCantidad').value = '';
  document.getElementById('sinExistenciasCosto').value = p.costo && Number(p.costo) > 0 ? p.costo : '';
  document.getElementById('sinExistenciasError').style.display = 'none';
  openModal('sin-existencias');
  document.getElementById('sinExistenciasCantidad').focus();
}

function cerrarSinExistencias() {
  POS.pendienteResurtir = null;
  closeModal('sin-existencias');
  cargarCarrito(POS.carrito);
}

async function guardarSinExistencias(evento) {
  evento.preventDefault();
  const pendiente = POS.pendienteResurtir;
  if (!pendiente) return false;
  const error = document.getElementById('sinExistenciasError');
  const cantidad = document.getElementById('sinExistenciasCantidad').value;
  const costo = document.getElementById('sinExistenciasCosto').value;
  const productoId = pendiente.datos.producto.id;

  if (modoSinInternet()) {
    resurtirLocal(productoId, cantidad, costo);
  } else {
    try {
      const r = await llamar(rutaDe('urlResurtir', productoId), 'POST', { cantidad: cantidad, costo: costo });
      if (!r.ok || !r.datos.ok) {
        error.textContent = r.datos.mensaje || 'No se pudo agregar la mercancía.';
        error.style.display = 'block';
        return false;
      }
    } catch (e) {
      if (e.red) {
        caidaDeRed();
        resurtirLocal(productoId, cantidad, costo);
      } else {
        throw e;
      }
    }
  }

  POS.pendienteResurtir = null;
  closeModal('sin-existencias');
  avisar('Agregué la mercancía al inventario. Sigamos con la venta.', 'success');
  refrescarCatalogo();
  if (pendiente.reintento) await pendiente.reintento();
  return false;
}

// ------------------------------------------------------------------ producto no encontrado

function abrirNoEncontrado() {
  const caja = document.getElementById('recientesNoEncontrado');
  caja.innerHTML = '';
  let recientes = [];
  try { recientes = JSON.parse(document.getElementById('recientesNoEncontrados').textContent); } catch (e) {}
  recientes.forEach(function (r) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'chip-reciente';
    chip.textContent = r.nombre + ' · $' + Number(r.precio).toFixed(2);
    chip.addEventListener('click', function () {
      document.getElementById('noEncontradoNombre').value = r.nombre;
      document.getElementById('noEncontradoPrecio').value = r.precio;
      document.getElementById('modal-no-encontrado').querySelector('form').requestSubmit();
    });
    caja.appendChild(chip);
  });
  document.getElementById('noEncontradoNombre').value = '';
  document.getElementById('noEncontradoPrecio').value = '';
  openModal('no-encontrado');
  document.getElementById('noEncontradoNombre').focus();
}

async function guardarNoEncontrado(evento) {
  evento.preventDefault();
  const nombre = document.getElementById('noEncontradoNombre').value.trim();
  const precio = parseFloat(document.getElementById('noEncontradoPrecio').value);
  if (!nombre || !(precio > 0)) return false;
  closeModal('no-encontrado');

  if (modoSinInternet()) {
    noEncontradoLocal(nombre, precio);
  } else {
    const resultado = await accion(rutaDe('urlNoEncontrado', POS.carrito), 'POST', { nombre: nombre, precio: precio });
    if (resultado) {
      // se recuerda para tenerlo a la mano la próxima vez
      const lista = document.getElementById('recientesNoEncontrados');
      let recientes = [];
      try { recientes = JSON.parse(lista.textContent); } catch (e) {}
      recientes = recientes.filter(function (r) { return r.nombre.toLowerCase() !== nombre.toLowerCase(); });
      recientes.unshift({ nombre: nombre, precio: precio.toFixed(2) });
      lista.textContent = JSON.stringify(recientes.slice(0, 8));
    }
  }
  document.getElementById('buscarProducto').focus();
  return false;
}

// ------------------------------------------------------------------ sin internet

function modoSinInternet() {
  return POS.sinInternet || (window.Sinconexion && !window.Sinconexion.enLinea());
}

function estadoLocal() {
  const local = POS.local[POS.carrito];
  let total = 0;
  const renglones = local.renglones.map(function (r) {
    const subtotal = Math.round(r.cantidad * r.precio_unitario * 100) / 100;
    total += subtotal;
    return {
      id: r.id, producto_id: r.producto_id, nombre: r.nombre, icono: r.icono, a_granel: r.a_granel,
      unidad: r.a_granel ? 'kg' : 'pzas', cantidad: String(r.cantidad), precio_unitario: String(r.precio_unitario),
      subtotal: subtotal.toFixed(2), disponible: r.disponible,
    };
  });
  const contadores = {};
  Object.keys(POS.local).forEach(function (n) { contadores[n] = POS.local[n].renglones.length; });
  return { carrito: POS.carrito, folio: null, total: total.toFixed(2), renglones: renglones, contadores: contadores };
}

function caidaDeRed() {
  if (POS.sinInternet) return;
  POS.sinInternet = true;
  if (window.Sinconexion) window.Sinconexion.marcarCaido();
  // lo que se veía en el carrito se conserva para poder terminar la venta
  if (POS.estado) {
    POS.local[POS.carrito] = {
      copiadoDelServidor: true,
      renglones: POS.estado.renglones.map(function (r) {
        return {
          id: 'p' + r.producto_id, producto_id: r.producto_id, nombre: r.nombre, icono: r.icono, a_granel: r.a_granel,
          cantidad: parseFloat(r.cantidad), precio_unitario: parseFloat(r.precio_unitario), disponible: r.disponible,
        };
      }),
    };
  }
  avisar('Se perdió la conexión. Puedes seguir vendiendo: se actualizará el sistema una vez que haya internet.', 'alerta');
  pintar(estadoLocal());
}

function intentarVolverAEnLinea() {
  if (!POS.sinInternet) return;
  if (window.Sinconexion && !window.Sinconexion.enLinea()) return;
  const hayLocal = Object.keys(POS.local).some(function (n) { return POS.local[n].renglones.length; });
  if (hayLocal) return;  // primero se termina la venta que se estaba haciendo
  POS.sinInternet = false;
  cargarCarrito(POS.carrito);
  refrescarCatalogo();
}

function producto(id) {
  return POS.catalogo.find(function (p) { return Number(p.id) === Number(id); });
}

function enCarritosLocales(productoId) {
  let total = 0;
  Object.keys(POS.local).forEach(function (n) {
    POS.local[n].renglones.forEach(function (r) { if (r.producto_id === productoId) total += r.cantidad; });
  });
  return total;
}

function agregarLocal(productoId, cantidad) {
  const p = producto(productoId);
  if (!p) { avisar('Ese producto no está en la copia de este dispositivo.', 'alerta'); return false; }
  const local = POS.local[POS.carrito];
  const existente = local.renglones.find(function (r) { return r.producto_id === productoId; });
  const nueva = (existente ? existente.cantidad : 0) + Number(cantidad);
  const disponible = Number(p.stock) - (enCarritosLocales(productoId) - (existente ? existente.cantidad : 0));

  if (nueva > disponible + 1e-9) {
    const falta = {
      error: 'sin_existencias',
      mensaje: disponible <= 0 ? 'No hay existencias de "' + p.nombre + '".' : 'De "' + p.nombre + '" solo hay ' + disponible + ' y pides ' + nueva + '.',
      producto: { id: p.id, nombre: p.nombre, a_granel: p.a_granel, costo: '' },
    };
    pedirResurtir(falta, function () { return agregarLocal(productoId, cantidad); });
    return false;
  }
  if (existente) {
    existente.cantidad = Math.round(nueva * 1000) / 1000;
  } else {
    local.renglones.push({
      id: 'p' + productoId, producto_id: productoId, nombre: p.nombre, icono: p.icono, a_granel: p.a_granel,
      cantidad: Math.round(Number(cantidad) * 1000) / 1000, precio_unitario: Number(p.precio_venta), disponible: String(p.stock),
    });
  }
  pintar(estadoLocal());
  return true;
}

function cambiarCantidadLocal(renglon, cantidad) {
  const local = POS.local[POS.carrito];
  const r = local.renglones.find(function (x) { return x.id === renglon.id; });
  if (!r) return false;
  const nueva = renglon.a_granel ? cantidad / 1000 : cantidad;
  if (nueva <= 0) { quitarLocal(renglon); return true; }
  if (!r.a_granel && nueva !== Math.floor(nueva)) { avisar('Este producto es por pieza: usa un número entero.', 'alerta'); pintar(estadoLocal()); return false; }

  const p = r.producto_id ? producto(r.producto_id) : null;
  if (p) {
    const disponible = Number(p.stock) - (enCarritosLocales(r.producto_id) - r.cantidad);
    if (nueva > disponible + 1e-9) {
      pedirResurtir({
        error: 'sin_existencias', mensaje: 'De "' + p.nombre + '" solo hay ' + disponible + ' y pides ' + nueva + '.',
        producto: { id: p.id, nombre: p.nombre, a_granel: p.a_granel, costo: '' },
      }, function () { return cambiarCantidadLocal(renglon, cantidad); });
      pintar(estadoLocal());
      return false;
    }
  }
  r.cantidad = Math.round(nueva * 1000) / 1000;
  pintar(estadoLocal());
  return true;
}

function quitarLocal(renglon) {
  const local = POS.local[POS.carrito];
  local.renglones = local.renglones.filter(function (x) { return x.id !== renglon.id; });
  pintar(estadoLocal());
}

function noEncontradoLocal(nombre, precio) {
  const local = POS.local[POS.carrito];
  const id = 'ne-' + nombre.toLowerCase();
  const existente = local.renglones.find(function (r) { return r.id === id; });
  if (existente) {
    existente.cantidad += 1;
  } else {
    local.renglones.push({
      id: id, producto_id: null, no_encontrado: true, nombre: nombre, icono: '📦', a_granel: false,
      cantidad: 1, precio_unitario: precio, disponible: null,
    });
  }
  pintar(estadoLocal());
}

function resurtirLocal(productoId, cantidad, costo) {
  const p = producto(productoId);
  if (p) { p.stock = Number(p.stock) + Number(cantidad); guardarCatalogoLocal(); }
  window.Sinconexion.encolar('resurtir', { producto_id: Number(productoId), cantidad: cantidad, costo: costo });
}

async function cobrarLocal() {
  const local = POS.local[POS.carrito];
  if (!local.renglones.length) return;
  const ahora = new Date();
  const estado = estadoLocal();

  await window.Sinconexion.encolar('venta', {
    carrito: POS.carrito,
    fecha: ahora.toISOString(),
    limpiar_carrito: local.copiadoDelServidor,
    renglones: local.renglones.map(function (r) {
      return r.no_encontrado
        ? { no_encontrado: true, nombre: r.nombre, cantidad: r.cantidad, precio_unitario: r.precio_unitario }
        : { producto_id: r.producto_id, cantidad: r.cantidad, precio_unitario: r.precio_unitario };
    }),
  });

  // se descuenta de la copia local del catálogo para que las siguientes ventas vean las existencias reales
  local.renglones.forEach(function (r) {
    const p = r.producto_id ? producto(r.producto_id) : null;
    if (p) p.stock = Math.max(Number(p.stock) - r.cantidad, 0);
  });
  guardarCatalogoLocal();

  mostrarTicket({
    folio: null, tienda: document.querySelector('.user-dropdown-negocio') ? document.querySelector('.user-dropdown-negocio').textContent : '',
    ubicacion: '', fecha: ahora.toLocaleDateString('es-MX'), hora: ahora.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' }),
    total: estado.total,
    renglones: estado.renglones.map(function (r) {
      return { nombre: r.nombre, cantidad: r.cantidad, unidad: r.unidad, subtotal: r.subtotal };
    }),
  }, true);

  POS.local[POS.carrito] = nuevoLocal();
  pintar(estadoLocal());
  intentarVolverAEnLinea();
}

// ---- búsqueda en la copia del catálogo (misma idea que el servidor: sin acentos, sin orden, con errores de dedo)

function sinAcentos(texto) {
  return String(texto).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

function distancia(a, b) {
  const fila = Array.from({ length: b.length + 1 }, function (_, i) { return i; });
  for (let i = 1; i <= a.length; i++) {
    let anterior = fila[0];
    fila[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const guardado = fila[j];
      fila[j] = Math.min(fila[j] + 1, fila[j - 1] + 1, anterior + (a[i - 1] === b[j - 1] ? 0 : 1));
      anterior = guardado;
    }
  }
  return fila[b.length];
}

function buscarLocal(q) {
  const palabras = sinAcentos(q).split(/\s+/).filter(Boolean);
  if (!palabras.length) return [];

  let encontrados = POS.catalogo.filter(function (p) {
    const nombre = sinAcentos(p.nombre);
    return palabras.every(function (w) { return nombre.includes(w); });
  });

  if (!encontrados.length) {
    // errores de dedo: cada palabra buscada debe parecerse (1 letra de diferencia) a alguna palabra del nombre
    encontrados = POS.catalogo.filter(function (p) {
      const partes = sinAcentos(p.nombre).split(/[\s-]+/);
      return palabras.every(function (w) {
        return partes.some(function (parte) {
          if (parte.includes(w)) return true;
          return w.length >= 4 && Math.abs(parte.length - w.length) <= 2 && distancia(w, parte.slice(0, w.length + 1)) <= 1;
        });
      });
    });
  }
  return encontrados.slice(0, 8);
}

// ---- catálogo guardado en el dispositivo

async function refrescarCatalogo() {
  if (!window.Sinconexion) return;
  if (!modoSinInternet()) {
    try {
      const r = await llamar(raiz().dataset.urlCatalogo);
      if (r.datos.productos) {
        POS.catalogo = r.datos.productos;
        window.Sinconexion.guardarCatalogo(POS.catalogo);
      }
    } catch (e) {}
  } else if (!POS.catalogo.length) {
    POS.catalogo = (await window.Sinconexion.leerCatalogo()) || [];
  }
}

function guardarCatalogoLocal() {
  if (window.Sinconexion) window.Sinconexion.guardarCatalogo(POS.catalogo);
}

// ------------------------------------------------------------------ arranque

function actualizarRelojVenta() {
  const ahora = new Date();
  const fechaEl = document.getElementById('fechaActual');
  const horaEl = document.getElementById('horaActual');
  if (fechaEl) fechaEl.textContent = ahora.toLocaleDateString('es-MX');
  if (horaEl) horaEl.textContent = ahora.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
}

document.addEventListener('DOMContentLoaded', async function () {
  actualizarRelojVenta();
  setInterval(actualizarRelojVenta, 30000);

  const inicial = JSON.parse(document.getElementById('estadoInicial').textContent);
  let preferido = inicial.carrito;
  try { preferido = parseInt(localStorage.getItem('carrito_activo') || inicial.carrito, 10) || inicial.carrito; } catch (e) {}
  POS.carrito = preferido;
  window.carritoActivo = POS.carrito;

  if (preferido === inicial.carrito) { pintar(inicial); } else { cargarCarrito(preferido); }

  // para el chat: si la IA cambia el carrito, se vuelve a pedir al servidor
  window.refrescarPOS = function () { cargarCarrito(POS.carrito); };

  await refrescarCatalogo();
  document.addEventListener('sinconexion:cambio', intentarVolverAEnLinea);
  if (modoSinInternet()) { POS.sinInternet = true; pintar(estadoLocal()); }

  const entrada = document.getElementById('buscarProducto');
  entrada.focus();

  entrada.addEventListener('input', function () {
    const q = entrada.value.trim();
    clearTimeout(esperaBusqueda);
    if (!q || esCodigo(q)) { cerrarResultados(); return; }
    esperaBusqueda = setTimeout(function () { buscar(q); }, 200);
  });

  entrada.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); alPresionarEnter(); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); moverResaltado(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); moverResaltado(-1); }
    else if (e.key === 'Escape') { cerrarResultados(); }
  });

  document.addEventListener('click', function (event) {
    if (!event.target.closest('.search-wrapper')) cerrarResultados();
  });
});
