// Gráficas del agente financiero. Se dibujan con SVG a partir de los datos reales que manda el
// servidor (un bloque json_script por gráfica), siempre en rosa, que es el color de este módulo.
// Cada gráfica chica tiene un botón con un ojo que la abre en grande dentro de una ventana.
//
// Forma de los datos:
//   { titulo, tipo: 'barras' | 'linea', formato: 'dinero' | 'porcentaje' | 'numero',
//     etiquetas: [...], series: [{ nombre, valores: [...] }], referencia: { valor, texto } | null }

const COLORES_GRAFICA = ['var(--fin-600)', 'var(--fin-300)'];

function escaparTexto(texto) {
  return String(texto).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function darFormato(tipo, n) {
  if (tipo === 'dinero') return '$' + Number(n).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (tipo === 'porcentaje') return Number(n).toLocaleString('es-MX', { maximumFractionDigits: 1 }) + '%';
  return Number(n).toLocaleString('es-MX', { maximumFractionDigits: 2 });
}

// para los ejes: $1.5 mil en vez de $1,500.00
function formatoCorto(tipo, n) {
  const absoluto = Math.abs(n);
  let texto;
  if (absoluto >= 1000000) texto = (n / 1000000).toLocaleString('es-MX', { maximumFractionDigits: 1 }) + ' M';
  else if (absoluto >= 10000) texto = (n / 1000).toLocaleString('es-MX', { maximumFractionDigits: 0 }) + ' mil';
  else if (absoluto >= 1000) texto = (n / 1000).toLocaleString('es-MX', { maximumFractionDigits: 1 }) + ' mil';
  else texto = n.toLocaleString('es-MX', { maximumFractionDigits: tipo === 'porcentaje' ? 0 : 2 });
  if (tipo === 'dinero') return '$' + texto;
  if (tipo === 'porcentaje') return texto + '%';
  return texto;
}

// un paso "redondo" para el eje (1, 2, 5, 10, 20, 50…)
function pasoRedondo(maximo, marcas) {
  const crudo = maximo / marcas;
  const potencia = Math.pow(10, Math.floor(Math.log10(crudo)));
  const fraccion = crudo / potencia;
  const bonito = fraccion <= 1 ? 1 : fraccion <= 2 ? 2 : fraccion <= 5 ? 5 : 10;
  return bonito * potencia;
}

function dibujarGrafica(contenedor, cfg, grande) {
  const ancho = Math.max(contenedor.clientWidth, 160);
  const alto = grande ? Math.min(Math.max(Math.round(ancho * 0.5), 260), 420) : parseInt(contenedor.dataset.alto || '84', 10);
  const m = grande ? { i: 66, d: 18, s: 18, b: 38 } : { i: 6, d: 6, s: 8, b: 18 };
  const series = cfg.series || [];
  const n = (cfg.etiquetas || []).length;
  const todos = [];
  series.forEach(function (s) { s.valores.forEach(function (v) { todos.push(v); }); });
  if (cfg.referencia) todos.push(cfg.referencia.valor);

  const hayDatos = n > 0 && todos.some(function (v) { return v !== 0; });
  if (!hayDatos) {
    contenedor.innerHTML = '<div class="fin-grafica-vacia" style="height:' + alto + 'px;">Todavía no hay datos para dibujar esta gráfica.</div>';
    return;
  }

  // escala del eje vertical
  const marcas = grande ? 5 : 3;
  let maximo = Math.max(0, Math.max.apply(null, todos));
  let minimo = Math.min(0, Math.min.apply(null, todos));
  const paso = pasoRedondo((maximo - minimo) || 1, marcas);
  const tope = maximo > 0 ? Math.ceil(maximo / paso) * paso : 0;
  const fondo = minimo < 0 ? Math.floor(minimo / paso) * paso : 0;
  const x0 = m.i, x1 = ancho - m.d, y0 = m.s, y1 = alto - m.b;
  const posY = function (v) { return y0 + (tope - v) / ((tope - fondo) || 1) * (y1 - y0); };
  const banda = (x1 - x0) / n;
  const centro = function (i) { return x0 + banda * (i + 0.5); };

  let svg = '';
  // cuadrícula y números del eje
  for (let v = fondo; v <= tope + paso / 2; v += paso) {
    const y = posY(v);
    if (grande) {
      svg += '<line x1="' + x0 + '" x2="' + x1 + '" y1="' + y + '" y2="' + y + '" class="fin-g-rejilla' + (v === 0 ? ' cero' : '') + '"/>';
      svg += '<text x="' + (x0 - 8) + '" y="' + (y + 4) + '" text-anchor="end" class="fin-g-texto">' + escaparTexto(formatoCorto(cfg.formato, v)) + '</text>';
    } else if (v === 0 || v === fondo) {
      svg += '<line x1="' + x0 + '" x2="' + x1 + '" y1="' + y + '" y2="' + y + '" class="fin-g-rejilla cero"/>';
    }
  }

  // barras o línea
  if (cfg.tipo === 'linea') {
    series.forEach(function (serie, k) {
      const color = COLORES_GRAFICA[k % COLORES_GRAFICA.length];
      const puntos = serie.valores.map(function (v, i) { return centro(i).toFixed(1) + ',' + posY(v).toFixed(1); });
      if (series.length === 1) {
        svg += '<polygon points="' + centro(0).toFixed(1) + ',' + posY(0).toFixed(1) + ' ' + puntos.join(' ') + ' ' + centro(n - 1).toFixed(1) + ',' + posY(0).toFixed(1) + '" class="fin-g-area"/>';
      }
      svg += '<polyline points="' + puntos.join(' ') + '" fill="none" style="stroke:' + color + ';" stroke-width="' + (grande ? 3 : 2.5) + '" stroke-linejoin="round" stroke-linecap="round"/>';
      if (n <= 31) {
        serie.valores.forEach(function (v, i) {
          svg += '<circle cx="' + centro(i).toFixed(1) + '" cy="' + posY(v).toFixed(1) + '" r="' + (grande ? 4.5 : 3) + '" style="fill:' + color + ';" class="fin-g-punto"><title>' +
            escaparTexto(cfg.etiquetas[i] + ' · ' + serie.nombre + ': ' + darFormato(cfg.formato, v)) + '</title></circle>';
        });
      }
    });
  } else {
    const k = series.length;
    const anchoBarra = Math.min((banda * 0.72) / k, grande ? 54 : 26);
    const anchoGrupo = anchoBarra * k + (k - 1) * 2;
    series.forEach(function (serie, s) {
      const color = COLORES_GRAFICA[s % COLORES_GRAFICA.length];
      serie.valores.forEach(function (v, i) {
        const x = centro(i) - anchoGrupo / 2 + s * (anchoBarra + 2);
        const y = Math.min(posY(v), posY(0));
        const alturaBarra = Math.max(Math.abs(posY(v) - posY(0)), v !== 0 ? 2 : 0);
        svg += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + anchoBarra.toFixed(1) + '" height="' + alturaBarra.toFixed(1) +
          '" rx="' + (grande ? 4 : 2) + '" style="fill:' + color + ';" class="fin-g-barra"><title>' +
          escaparTexto(cfg.etiquetas[i] + ' · ' + serie.nombre + ': ' + darFormato(cfg.formato, v)) + '</title></rect>';
        if (grande && n * k <= 14 && v !== 0) {
          svg += '<text x="' + (x + anchoBarra / 2).toFixed(1) + '" y="' + (v >= 0 ? y - 5 : y + alturaBarra + 12).toFixed(1) +
            '" text-anchor="middle" class="fin-g-valor">' + escaparTexto(formatoCorto(cfg.formato, v)) + '</text>';
        }
      });
    });
  }

  // línea de referencia (por ejemplo, el punto de equilibrio)
  if (cfg.referencia) {
    const y = posY(cfg.referencia.valor);
    svg += '<line x1="' + x0 + '" x2="' + x1 + '" y1="' + y + '" y2="' + y + '" class="fin-g-referencia"><title>' +
      escaparTexto(cfg.referencia.texto + ': ' + darFormato(cfg.formato, cfg.referencia.valor)) + '</title></line>';
    if (grande) {
      svg += '<text x="' + (x1 - 4) + '" y="' + (y - 6) + '" text-anchor="end" class="fin-g-texto ref">' + escaparTexto(cfg.referencia.texto) + '</text>';
    }
  }

  // etiquetas del eje horizontal: solo las que caben sin encimarse
  const largo = Math.max.apply(null, cfg.etiquetas.map(function (e) { return String(e).length; }));
  const anchoEtiqueta = largo * (grande ? 6.6 : 5.4) + (grande ? 10 : 6);
  const salto = Math.max(1, Math.ceil(anchoEtiqueta / banda));
  cfg.etiquetas.forEach(function (etiqueta, i) {
    if (i % salto !== 0) return;
    svg += '<text x="' + centro(i).toFixed(1) + '" y="' + (alto - (grande ? 14 : 4)) + '" text-anchor="middle" class="fin-g-texto">' + escaparTexto(etiqueta) + '</text>';
  });

  let leyenda = '';
  if (series.length > 1 || cfg.referencia) {
    leyenda = '<div class="fin-leyenda">';
    series.forEach(function (serie, k) {
      leyenda += '<span><i style="background:' + COLORES_GRAFICA[k % COLORES_GRAFICA.length] + ';"></i>' + escaparTexto(serie.nombre) + '</span>';
    });
    if (cfg.referencia) leyenda += '<span><i class="ref"></i>' + escaparTexto(cfg.referencia.texto) + '</span>';
    leyenda += '</div>';
  }

  contenedor.innerHTML =
    '<svg viewBox="0 0 ' + ancho + ' ' + alto + '" width="' + ancho + '" height="' + alto + '" role="img" aria-label="' + escaparTexto(cfg.titulo) + '">' + svg + '</svg>' + leyenda;
}

// tabla con los mismos números, debajo de la gráfica grande (también sirve para leerla con precisión)
function tablaDeLaGrafica(cfg) {
  if (!cfg.etiquetas.length || cfg.etiquetas.length > 12) return '';
  let html = '<table class="fin-table fin-tabla-grafica"><thead><tr><th></th>';
  cfg.series.forEach(function (s) { html += '<th style="text-align:right;">' + escaparTexto(s.nombre) + '</th>'; });
  html += '</tr></thead><tbody>';
  cfg.etiquetas.forEach(function (etiqueta, i) {
    html += '<tr><td>' + escaparTexto(etiqueta) + '</td>';
    cfg.series.forEach(function (s) { html += '<td style="text-align:right;">' + escaparTexto(darFormato(cfg.formato, s.valores[i])) + '</td>'; });
    html += '</tr>';
  });
  return html + '</tbody></table>';
}

function datosDeLaGrafica(id) {
  const bloque = document.getElementById(id);
  if (!bloque) return null;
  try { return JSON.parse(bloque.textContent); } catch (e) { return null; }
}

let graficaAmpliada = null;

function ampliarGrafica(id) {
  const cfg = datosDeLaGrafica(id);
  if (!cfg) return;
  graficaAmpliada = cfg;
  document.getElementById('tituloGraficaGrande').textContent = cfg.titulo;
  openModal('grafica-grande');
  // se dibuja cuando la ventana ya está abierta, para medir bien el ancho disponible
  requestAnimationFrame(function () { pintarGraficaGrande(); });
}

function pintarGraficaGrande() {
  const caja = document.getElementById('graficaGrande');
  if (!caja || !graficaAmpliada) return;
  dibujarGrafica(caja, graficaAmpliada, true);
  document.getElementById('tablaGraficaGrande').innerHTML = tablaDeLaGrafica(graficaAmpliada);
}

document.addEventListener('DOMContentLoaded', function () {
  const observador = typeof ResizeObserver === 'function' ? new ResizeObserver(function (entradas) {
    entradas.forEach(function (entrada) {
      const el = entrada.target;
      if (el.id === 'graficaGrande') { pintarGraficaGrande(); return; }
      if (el._anchoDibujado !== el.clientWidth && el._cfg) { el._anchoDibujado = el.clientWidth; dibujarGrafica(el, el._cfg, false); }
    });
  }) : null;

  document.querySelectorAll('[data-grafica]').forEach(function (el) {
    const cfg = datosDeLaGrafica(el.dataset.grafica);
    if (!cfg) return;
    el._cfg = cfg;
    el._anchoDibujado = el.clientWidth;
    dibujarGrafica(el, cfg, false);
    if (observador) observador.observe(el);
  });
  const grande = document.getElementById('graficaGrande');
  if (grande && observador) observador.observe(grande);

  // el ojo de cada gráfica la abre en grande (sin seguir el enlace de la tarjeta donde esté)
  document.addEventListener('click', function (evento) {
    const boton = evento.target.closest('[data-ampliar]');
    if (!boton) return;
    evento.preventDefault();
    evento.stopPropagation();
    ampliarGrafica(boton.dataset.ampliar);
  });
});
