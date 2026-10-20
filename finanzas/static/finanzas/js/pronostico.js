// Pronóstico progresivo: se pide un modelo a la vez y la tabla se va llenando.
// Primero sale la regresión lineal (la más rápida) como resultado preliminar,
// y después se refina con Holt-Winters y ARIMA hasta tener el resultado final.

(function () {
  const tarjeta = document.getElementById('tarjetaPronostico');
  if (!tarjeta) return;

  const ORDEN = ['lineal', 'holt_winters', 'arima'];  // del más rápido al más lento
  const NOMBRES = { lineal: 'regresión lineal', holt_winters: 'Holt-Winters', arima: 'ARIMA' };
  const COLUMNAS = { arima: 6, lineal: 7, holt_winters: 8 };

  const estado = document.getElementById('estadoPronostico');
  const barra = document.getElementById('barraPronostico');
  const cuerpo = document.getElementById('cuerpoPronostico');
  const botonRecalcular = document.getElementById('btnRecalcular');
  const botonExplicar = document.getElementById('btnExplicarPronostico');

  let base = null;
  let resultados = {};   // clave del modelo -> lista de resultados por producto
  let corrida = 0;       // para ignorar respuestas de un cálculo viejo

  function texto(celda, valor, clase) {
    celda.textContent = valor;
    if (clase) celda.className = clase;
    return celda;
  }

  function pedir(url) {
    return fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } }).then(function (r) {
      if (!r.ok) throw new Error('Respuesta ' + r.status);
      return r.json();
    });
  }

  function nivelDeConfianza(mae, promedio) {
    if (mae === null || mae === undefined || !promedio) return 'sin datos';
    const relativo = mae / promedio;
    if (relativo <= base.umbrales.alta) return 'alta';
    if (relativo <= base.umbrales.media) return 'media';
    return 'baja';
  }

  // el modelo con menor error de cada producto, con lo que ya se haya calculado
  function mejorHastaAhora(indice) {
    let mejor = null;
    ORDEN.forEach(function (clave) {
      const lista = resultados[clave];
      if (!lista) return;
      const dato = lista[indice];
      if (dato && dato.disponible && dato.mae !== null && (!mejor || dato.mae < mejor.dato.mae)) {
        mejor = { clave: clave, dato: dato };
      }
    });
    if (!mejor) {
      // si todavía no hay error de prueba pero sí un pronóstico, se muestra ese
      ORDEN.forEach(function (clave) {
        const lista = resultados[clave];
        if (!mejor && lista && lista[indice] && lista[indice].disponible) mejor = { clave: clave, dato: lista[indice] };
      });
    }
    return mejor;
  }

  function dibujarFila(producto, indice) {
    const fila = cuerpo.children[indice];
    const celdas = fila.children;

    if (!producto.suficiente) {
      texto(celdas[2], 'Datos insuficientes');
      celdas[2].colSpan = 7;
      celdas[2].title = 'Tiene ' + producto.dias_de_historia + ' días de historia y se necesitan ' + base.minimo_de_dias + '.';
      while (celdas.length > 3) fila.removeChild(celdas[3]);
      return;
    }

    const mejor = mejorHastaAhora(indice);
    if (mejor) {
      const pronostico = mejor.dato.pronostico;
      texto(celdas[2], String(pronostico), 'fin-cifra');
      let cambio = '—';
      let claseCambio = '';
      if (producto.ultima_semana_real > 0) {
        const pct = Math.round((pronostico - producto.ultima_semana_real) / producto.ultima_semana_real * 100);
        cambio = (pct > 0 ? '+' : '') + pct + ' %';
        claseCambio = pct > 0 ? 'fin-sube' : (pct < 0 ? 'fin-baja' : '');
      }
      texto(celdas[3], cambio, claseCambio);
      const nivel = nivelDeConfianza(mejor.dato.mae, producto.promedio_semanal);
      texto(celdas[4], nivel, 'fin-confianza fin-confianza-' + nivel.replace(' ', '-'));
      texto(celdas[5], NOMBRES[mejor.clave] ? NOMBRES[mejor.clave] : mejor.clave);
    }

    Object.keys(COLUMNAS).forEach(function (clave) {
      const celda = celdas[COLUMNAS[clave]];
      const lista = resultados[clave];
      if (!lista) { texto(celda, '…'); return; }
      const dato = lista[indice];
      if (dato && dato.disponible) {
        texto(celda, dato.pronostico + ' / ' + (dato.mae === null ? 's/d' : dato.mae));
      } else {
        texto(celda, 's/d');
      }
    });
  }

  function dibujarTabla() {
    base.productos.forEach(dibujarFila);
  }

  function armarTabla() {
    cuerpo.innerHTML = '';
    base.productos.forEach(function (producto) {
      const fila = document.createElement('tr');
      for (let i = 0; i < 9; i++) fila.appendChild(document.createElement('td'));
      const nombre = fila.children[0];
      nombre.textContent = producto.nombre + (producto.atipico_corregido ? ' *' : '');
      nombre.style.fontWeight = '700';
      texto(fila.children[1], String(producto.ultima_semana_real));
      texto(fila.children[2], '…');
      cuerpo.appendChild(fila);
    });
    document.getElementById('tablaPronostico').style.display = '';
    document.getElementById('notaPronostico').style.display = '';
    const periodo = document.getElementById('periodoPronostico');
    periodo.textContent = 'Historial hasta la semana del ' + base.ultima_semana + ' · Pronóstico para la semana del ' + base.semana_pronostico;
    periodo.style.display = '';
    document.getElementById('minimoDias').textContent = base.minimo_de_dias;
  }

  function avance(paso, total, mensaje) {
    estado.textContent = mensaje;
    barra.style.width = Math.round(paso / total * 100) + '%';
  }

  async function calcular() {
    const esta = ++corrida;
    botonRecalcular.disabled = true;
    botonExplicar.disabled = true;
    resultados = {};
    avance(0, ORDEN.length + 1, 'Preparando tus ventas…');

    try {
      base = await pedir(tarjeta.dataset.urlBase);
      if (esta !== corrida) return;
      if (base.estado === 'sin_ventas') {
        document.getElementById('vacioPronostico').style.display = '';
        document.getElementById('tablaPronostico').style.display = 'none';
        avance(1, 1, 'Todavía no hay ventas para pronosticar.');
        return;
      }
      document.getElementById('vacioPronostico').style.display = 'none';
      armarTabla();
      avance(1, ORDEN.length + 1, 'Listo, ya tengo tus ventas. Calculando el primer resultado…');

      for (let i = 0; i < ORDEN.length; i++) {
        const clave = ORDEN[i];
        const url = tarjeta.dataset.urlModelo.replace('CLAVE', clave);
        const respuesta = await pedir(url);
        if (esta !== corrida) return;
        resultados[clave] = respuesta.resultados;
        dibujarTabla();
        const faltan = ORDEN.length - i - 1;
        if (i === 0) {
          avance(i + 2, ORDEN.length + 1,
            'Resultado preliminar con ' + NOMBRES[clave] + '. Lo estoy refinando con ' + faltan + ' método' + (faltan === 1 ? '' : 's') + ' más…');
        } else if (faltan > 0) {
          avance(i + 2, ORDEN.length + 1, 'Ya probé ' + NOMBRES[clave] + '. Faltan ' + faltan + ' método' + (faltan === 1 ? '' : 's') + '…');
        }
      }
      avance(1, 1, 'Resultado final: se compararon los tres métodos y se eligió el de menor error de cada producto.');
      botonExplicar.disabled = false;
    } catch (error) {
      if (esta === corrida) {
        avance(0, 1, 'No pude calcular el pronóstico. Revisa tu conexión e inténtalo otra vez.');
      }
    } finally {
      if (esta === corrida) botonRecalcular.disabled = false;
    }
  }

  botonRecalcular.addEventListener('click', calcular);
  calcular();
})();
