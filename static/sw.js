// Service worker de marIA: guarda las pantallas y los archivos estáticos para poder abrir el
// sistema cuando no hay internet. Los datos (ventas, productos…) NO se guardan aquí: eso lo
// hace static/js/sinconexion.js en la cola del dispositivo.
const VERSION = 'maria-v2';

// pantallas que se pueden abrir sin conexión
const PANTALLAS = ['/ventas/', '/inventario/', '/finanzas/'];

self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (evento) {
  evento.waitUntil(
    caches.keys().then(function (nombres) {
      return Promise.all(nombres.filter(function (n) { return n !== VERSION; }).map(function (n) { return caches.delete(n); }));
    }).then(function () { return self.clients.claim(); })
  );
});

// la página le pide guardar las pantallas principales (para que funcionen sin internet desde la primera vez)
self.addEventListener('message', function (evento) {
  const datos = evento.data || {};
  if (datos.tipo !== 'guardar' || !Array.isArray(datos.urls)) return;
  evento.waitUntil(
    caches.open(VERSION).then(function (cache) {
      return Promise.all(datos.urls.map(function (url) {
        return fetch(url, { credentials: 'same-origin' }).then(function (respuesta) {
          if (respuesta.ok && !respuesta.redirected) return cache.put(url, respuesta);
        }).catch(function () {});
      }));
    })
  );
});

function esPantalla(url) {
  return PANTALLAS.some(function (ruta) { return url.pathname === ruta; });
}

self.addEventListener('fetch', function (evento) {
  const peticion = evento.request;
  if (peticion.method !== 'GET') return;

  const url = new URL(peticion.url);

  // archivos estáticos y recursos de otros sitios (fuentes, íconos): primero lo guardado, y se actualiza de fondo
  const esEstatico = url.origin === self.location.origin && url.pathname.indexOf('/static/') === 0;
  const esExterno = url.origin !== self.location.origin && ['style', 'script', 'font', 'image'].indexOf(peticion.destination) !== -1;
  if (esEstatico || esExterno) {
    evento.respondWith(
      caches.open(VERSION).then(function (cache) {
        return cache.match(peticion).then(function (guardado) {
          const actualizado = fetch(peticion).then(function (respuesta) {
            if (respuesta && (respuesta.ok || respuesta.type === 'opaque')) cache.put(peticion, respuesta.clone());
            return respuesta;
          }).catch(function () { return guardado; });
          return guardado || actualizado;
        });
      })
    );
    return;
  }

  // pantallas principales: primero el servidor (datos al día) y, si no hay internet, la última copia
  if (url.origin === self.location.origin && peticion.mode === 'navigate' && esPantalla(url)) {
    evento.respondWith(
      fetch(peticion).then(function (respuesta) {
        if (respuesta.ok && !respuesta.redirected) {
          const copia = respuesta.clone();
          caches.open(VERSION).then(function (cache) { cache.put(url.pathname, copia); });
        }
        return respuesta;
      }).catch(function () {
        return caches.match(url.pathname).then(function (guardado) {
          return guardado || new Response(
            '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            + '<body style="font-family:sans-serif;padding:24px"><h2>Sin internet</h2>'
            + '<p>Esta pantalla todavía no está guardada en este dispositivo. Ábrela una vez con internet y después ya podrás usarla sin conexión.</p></body>',
            { headers: { 'Content-Type': 'text/html; charset=utf-8' }, status: 503 }
          );
        });
      })
    );
  }
  // todo lo demás (JSON de la API, el chat…) va directo al servidor
});
