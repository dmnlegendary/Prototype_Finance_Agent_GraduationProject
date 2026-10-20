// Se carga primero el historial y después se calcula el pronóstico con ARIMA.

(function () {
  const tarjeta = document.getElementById('tarjetaPronostico');
  if (!tarjeta) return;

  const estado = document.getElementById('estadoPronostico');
  const barra = document.getElementById('barraPronostico');
  const cuerpo = document.getElementById('cuerpoPronostico');
  const botonRecalcular = document.getElementById('btnRecalcular');
  const botonExplicar = document.getElementById('btnExplicarPronostico');

  let base = null;
  let resultados = [];
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

  function dibujarFila(producto, indice) {
    const fila = cuerpo.children[indice];
    const celdas = fila.children;

    if (!producto.suficiente) {
      texto(celdas[2], 'Datos insuficientes');
      celdas[2].colSpan = 4;
      celdas[2].title = 'Tiene ' + producto.dias_de_historia + ' días de historia y se necesitan ' + base.minimo_de_dias + '.';
      while (celdas.length > 3) fila.removeChild(celdas[3]);
      return;
    }

    const dato = resultados[indice];
    if (dato && dato.disponible) {
      const pronostico = dato.pronostico;
      texto(celdas[2], String(pronostico), 'fin-cifra');
      let cambio = '—';
      let claseCambio = '';
      if (producto.ultima_semana_real > 0) {
        const pct = Math.round((pronostico - producto.ultima_semana_real) / producto.ultima_semana_real * 100);
        cambio = (pct > 0 ? '+' : '') + pct + ' %';
        claseCambio = pct > 0 ? 'fin-sube' : (pct < 0 ? 'fin-baja' : '');
      }
      texto(celdas[3], cambio, claseCambio);
      const nivel = nivelDeConfianza(dato.mae, producto.promedio_semanal);
      texto(celdas[4], nivel, 'fin-confianza fin-confianza-' + nivel.replace(' ', '-'));
      texto(celdas[5], dato.pronostico + ' / ' + (dato.mae === null ? 's/d' : dato.mae));
    } else {
      texto(celdas[2], 's/d');
      texto(celdas[5], 's/d');
    }
  }

  function dibujarTabla() {
    base.productos.forEach(dibujarFila);
  }

  function armarTabla() {
    cuerpo.innerHTML = '';
    base.productos.forEach(function (producto) {
      const fila = document.createElement('tr');
      for (let i = 0; i < 6; i++) fila.appendChild(document.createElement('td'));
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
    periodo.textContent = 'Historial desde la semana del ' + base.inicio_historial + ' hasta la semana del ' + base.ultima_semana +
      ' (' + base.semanas_historial + ' semanas) · Pronóstico para la semana del ' + base.semana_pronostico;
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
    resultados = [];
    avance(0, 2, 'Preparando tus ventas…');

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
      avance(1, 2, 'Historial listo. Calculando el pronóstico ARIMA…');
      const url = tarjeta.dataset.urlModelo.replace('CLAVE', 'arima');
      const respuesta = await pedir(url);
      if (esta !== corrida) return;
      resultados = respuesta.resultados;
      dibujarTabla();
      avance(2, 2, 'Pronóstico ARIMA calculado.');
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
