// Trabajo sin internet.
//
// Cuando se cae la conexión, las ventas, los productos dados de alta y la mercancía que
// llega se guardan en una cola dentro del dispositivo (IndexedDB). Cuando regresa el
// internet, la cola se manda sola al servidor (/sincronizar/). Mientras tanto una barra
// avisa: "se actualizará el sistema una vez que tengamos internet".
//
// Este archivo también guarda la copia del catálogo que usa la caja para vender sin internet
// y registra el service worker (static/sw.js), que guarda las pantallas para poder abrirlas
// sin conexión.
(function () {
  const NOMBRE_BD = 'marIA';
  const VERSION_BD = 1;
  const SEGUNDOS_ENTRE_SONDEOS = 10;

  let caido = false;            // el internet se cayó aunque el navegador crea que hay conexión
  let sincronizando = false;
  let pendientes = 0;           // cuántas operaciones hay en la cola (se mantiene al día)
  let sondeo = null;

  function abrirBD() {
    return new Promise(function (resolver, rechazar) {
      const peticion = indexedDB.open(NOMBRE_BD, VERSION_BD);
      peticion.onupgradeneeded = function () {
        const bd = peticion.result;
        if (!bd.objectStoreNames.contains('cola')) bd.createObjectStore('cola', { keyPath: 'uuid' });
        if (!bd.objectStoreNames.contains('catalogo')) bd.createObjectStore('catalogo');
      };
      peticion.onsuccess = function () { resolver(peticion.result); };
      peticion.onerror = function () { rechazar(peticion.error); };
    });
  }

  // ejecuta `accion(almacen)` dentro de una transacción y regresa su resultado
  function conAlmacen(nombre, modo, accion) {
    return abrirBD().then(function (bd) {
      return new Promise(function (resolver, rechazar) {
        const transaccion = bd.transaction(nombre, modo);
        const almacen = transaccion.objectStore(nombre);
        const peticion = accion(almacen);
        transaccion.oncomplete = function () { resolver(peticion ? peticion.result : undefined); bd.close(); };
        transaccion.onerror = function () { rechazar(transaccion.error); bd.close(); };
      });
    });
  }

  function uuid() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return 'op-' + Date.now() + '-' + Math.random().toString(16).slice(2);
  }

  function leerCookie(nombre) {
    const partes = document.cookie ? document.cookie.split('; ') : [];
    for (let i = 0; i < partes.length; i++) {
      if (partes[i].indexOf(nombre + '=') === 0) return decodeURIComponent(partes[i].slice(nombre.length + 1));
    }
    return '';
  }

  // ------------------------------------------------------------------ la barra de aviso

  function barra() {
    let el = document.getElementById('barraSinConexion');
    if (!el) {
      el = document.createElement('div');
      el.id = 'barraSinConexion';
      el.className = 'barra-sin-conexion';
      document.body.appendChild(el);
    }
    return el;
  }

  function pintarBarra() {
    const el = barra();
    if (!enLinea()) {
      el.className = 'barra-sin-conexion sin-internet';
      el.textContent = 'Sin internet. Puedes seguir vendiendo y dando de alta productos: se actualizará el sistema una vez que tengamos internet.'
        + (pendientes ? ' (' + pendientes + ' pendientes de sincronizar)' : '');
      el.style.display = 'block';
    } else if (pendientes) {
      el.className = 'barra-sin-conexion sincronizando';
      el.textContent = 'Actualizando el sistema con lo que hiciste sin internet… (' + pendientes + ' pendientes)';
      el.style.display = 'block';
    } else {
      el.style.display = 'none';
    }
  }

  function avisarCambio() {
    pintarBarra();
    document.dispatchEvent(new CustomEvent('sinconexion:cambio'));
  }

  // ------------------------------------------------------------------ conexión

  function enLinea() {
    return navigator.onLine !== false && !caido;
  }

  function sondear() {
    fetch('/sincronizar/estado/', { cache: 'no-store', credentials: 'same-origin' })
      .then(function () { volvio(); })
      .catch(function () {});
  }

  function marcarCaido() {
    if (caido) return;
    caido = true;
    pintarBarra();
    if (!sondeo) sondeo = setInterval(sondear, SEGUNDOS_ENTRE_SONDEOS * 1000);
  }

  function volvio() {
    if (!caido && navigator.onLine !== false) return;
    caido = false;
    if (sondeo) { clearInterval(sondeo); sondeo = null; }
    sincronizar().then(avisarCambio);
  }

  // ------------------------------------------------------------------ la cola

  function contar() {
    return conAlmacen('cola', 'readonly', function (a) { return a.count(); }).then(function (n) {
      pendientes = n;
      return n;
    });
  }

  function encolar(tipo, datos) {
    const operacion = { uuid: uuid(), tipo: tipo, datos: datos, creado: Date.now() };
    return conAlmacen('cola', 'readwrite', function (a) { return a.put(operacion); })
      .then(contar)
      .then(function () { pintarBarra(); return operacion.uuid; });
  }

  function todas() {
    return conAlmacen('cola', 'readonly', function (a) { return a.getAll(); }).then(function (lista) {
      return lista.sort(function (a, b) { return a.creado - b.creado; });
    });
  }

  function borrar(uuids) {
    return conAlmacen('cola', 'readwrite', function (a) {
      uuids.forEach(function (id) { a.delete(id); });
      return null;
    });
  }

  function sincronizar() {
    if (sincronizando || !enLinea()) return Promise.resolve();
    sincronizando = true;

    return todas().then(function (operaciones) {
      if (!operaciones.length) return null;
      pintarBarra();

      return fetch('/sincronizar/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': leerCookie('csrftoken') },
        body: JSON.stringify({ operaciones: operaciones }),
      }).then(function (respuesta) {
        if (!respuesta.ok) throw new Error('el servidor no pudo');
        return respuesta.json();
      }).then(function (datos) {
        const terminadas = [];
        (datos.resultados || []).forEach(function (r) {
          if (r.ok || r.definitivo) terminadas.push(r.uuid);
          if (!r.ok && r.definitivo && window.showToast) showToast('No se pudo guardar algo hecho sin internet: ' + r.mensaje, 'alerta');
        });
        return borrar(terminadas).then(function () {
          if (terminadas.length && window.showToast) {
            showToast('Listo: se actualizó el sistema con lo que hiciste sin internet.', 'success');
          }
        });
      });
    }).catch(function () {
      // sin conexión de verdad: se vuelve a intentar con el sondeo
      marcarCaido();
    }).then(function () {
      sincronizando = false;
      return contar().then(avisarCambio);
    });
  }

  // ------------------------------------------------------------------ copia del catálogo

  function guardarCatalogo(productos) {
    return conAlmacen('catalogo', 'readwrite', function (a) { return a.put(productos, 'productos'); }).catch(function () {});
  }

  function leerCatalogo() {
    return conAlmacen('catalogo', 'readonly', function (a) { return a.get('productos'); }).catch(function () { return []; });
  }

  // ------------------------------------------------------------------ al cerrar sesión

  // Los datos guardados en el dispositivo son de esta tienda: si se cierra sesión se borran,
  // pero antes se avisa si queda algo sin mandar.
  function confirmarSalida() {
    if (pendientes > 0) {
      return confirm('Hay ' + pendientes + ' operaciones hechas sin internet que todavía no se actualizan en el sistema. '
        + 'Si cierras sesión ahora se perderán. ¿Quieres cerrar sesión de todos modos?');
    }
    try { indexedDB.deleteDatabase(NOMBRE_BD); } catch (e) {}
    if (window.caches) caches.keys().then(function (nombres) { nombres.forEach(function (n) { caches.delete(n); }); });
    return true;
  }

  // ------------------------------------------------------------------ service worker

  function registrarServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).then(function () {
      return navigator.serviceWorker.ready;
    }).then(function (registro) {
      // se le pide guardar las pantallas principales para poder abrirlas sin internet
      let hoy = '';
      try { hoy = sessionStorage.getItem('pantallas_guardadas') || ''; } catch (e) {}
      if (registro.active && hoy !== 'si') {
        registro.active.postMessage({ tipo: 'guardar', urls: ['/ventas/', '/inventario/'] });
        try { sessionStorage.setItem('pantallas_guardadas', 'si'); } catch (e) {}
      }
    }).catch(function () {});
  }

  window.Sinconexion = {
    enLinea: enLinea,
    marcarCaido: marcarCaido,
    encolar: encolar,
    sincronizar: sincronizar,
    guardarCatalogo: guardarCatalogo,
    leerCatalogo: leerCatalogo,
    confirmarSalida: confirmarSalida,
    pendientes: function () { return pendientes; },
  };

  window.addEventListener('online', volvio);
  window.addEventListener('offline', function () { pintarBarra(); document.dispatchEvent(new CustomEvent('sinconexion:cambio')); });

  document.addEventListener('DOMContentLoaded', function () {
    contar().then(function () {
      pintarBarra();
      if (enLinea() && pendientes) sincronizar();
    }).catch(function () {});
    registrarServiceWorker();
    // por si algo quedó en la cola y no hubo un evento de "online"
    setInterval(function () { if (enLinea() && pendientes) sincronizar(); }, 30000);
  });
})();
