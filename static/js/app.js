document.addEventListener('click', function (event) {
  const el = event.target.closest('[data-sin-loader]');
  if (el) {
    try { sessionStorage.setItem('omitir_loader', '1'); } catch (e) {}
  }
});

function toggleUserMenu(event) {
  event.stopPropagation();
  document.getElementById('userDropdown').classList.toggle('open');
}

document.addEventListener('click', function (event) {
  const dropdown = document.getElementById('userDropdown');
  if (dropdown && !event.target.closest('.user-menu')) {
    dropdown.classList.remove('open');
  }
});

function openAvi() {
  document.getElementById('aviPanel').classList.add('open');
  document.getElementById('aviOverlay').classList.add('open');
}

function closeAvi() {
  document.getElementById('aviPanel').classList.remove('open');
  document.getElementById('aviOverlay').classList.remove('open');
}

function openModal(id) {
  const modal = document.getElementById('modal-' + id);
  if (modal) modal.classList.add('open');
}

function closeModal(id) {
  const modal = document.getElementById('modal-' + id);
  if (modal) modal.classList.remove('open');
}

function toggleAviMinimize() {
  const panel = document.getElementById('aviPanel');
  if (!panel) return;
  panel.classList.toggle('minimized');
  localStorage.setItem('avi_minimizado', panel.classList.contains('minimized') ? '1' : '0');
}

function toggleAviExpand() {
  const panel = document.getElementById('aviPanel');
  if (panel) panel.classList.toggle('expanded');
}

function csrfAvi() {
  const campo = document.querySelector('#aviForm input[name=csrfmiddlewaretoken]');
  return campo ? campo.value : '';
}

// Los modelos suelen contestar con markdown (**negritas**, "* viñetas"); aquí se
// muestra como texto limpio.
function limpiarTextoIA(texto) {
  return String(texto || '')
    .replace(/\*\*/g, '')
    .replace(/^\s*[*-]\s+/gm, '• ');
}

function agregarBurbujaAvi(rol, texto) {
  const chat = document.getElementById('aviChat');
  const burbuja = document.createElement('div');
  burbuja.className = 'bubble ' + (rol === 'usuario' ? 'user' : 'bot');
  burbuja.textContent = rol === 'usuario' ? texto : limpiarTextoIA(texto);
  chat.appendChild(burbuja);
  return burbuja;
}

// La conversación vive en el servidor (últimas 24 horas): al cambiar de pantalla
// se vuelve a cargar aquí y el chat no se borra.
function cargarHistorialAvi() {
  const chat = document.getElementById('aviChat');
  if (!chat) return;

  fetch('/avi/historial/')
    .then(function (r) { return r.json(); })
    .then(function (datos) {
      if (!datos.mensajes || !datos.mensajes.length) return;
      chat.innerHTML = '';
      datos.mensajes.forEach(function (m) { agregarBurbujaAvi(m.rol, m.texto); });
      chat.scrollTop = chat.scrollHeight;
    })
    .catch(function () {});
}

function limpiarChatAvi() {
  const chat = document.getElementById('aviChat');
  if (!chat) return;
  if (!confirm('¿Borrar toda la conversación con el asistente?')) return;

  fetch('/avi/limpiar/', { method: 'POST', headers: { 'X-CSRFToken': csrfAvi() } })
    .finally(function () {
      chat.innerHTML = '';
      const saludo = document.createElement('div');
      saludo.className = 'bubble bot';
      saludo.textContent = chat.dataset.saludo || 'Chat vaciado. ¿En qué puedo ayudarte?';
      chat.appendChild(saludo);
    });
}

document.addEventListener('DOMContentLoaded', cargarHistorialAvi);

document.addEventListener('DOMContentLoaded', function () {
  const panel = document.getElementById('aviPanel');
  if (panel && localStorage.getItem('avi_minimizado') === '1') {
    panel.classList.add('minimized');
  }

  let avatarGuardado = null;
  try { avatarGuardado = localStorage.getItem('avatar_elegido'); } catch (e) {}
  if (avatarGuardado) {
    document.querySelectorAll('.avatar').forEach(function (el) { el.textContent = avatarGuardado; });
  }
});

function elegirAvatar(emoji) {
  try { localStorage.setItem('avatar_elegido', emoji); } catch (e) {}
  document.querySelectorAll('.avatar').forEach(function (el) { el.textContent = emoji; });
}

function aiLoaderHTML(texto) {
  return ''
    + '<div class="ai-loader-wrapper">'
    + '<div class="ai-core-glow"></div>'
    + '<svg class="ai-svg-loader" viewBox="0 0 280 240" fill="none" xmlns="http://www.w3.org/2000/svg">'
    + '<defs>'
    + '<linearGradient id="aiRibbonGradient" x1="0%" y1="0%" x2="100%" y2="100%">'
    + '<stop offset="0%" stop-color="#f43f5e" /><stop offset="30%" stop-color="#d946ef" />'
    + '<stop offset="70%" stop-color="#8b5cf6" /><stop offset="100%" stop-color="#3b0764" />'
    + '</linearGradient>'
    + '<linearGradient id="aiLaserGradient" x1="0%" y1="0%" x2="100%" y2="0%">'
    + '<stop offset="0%" stop-color="#00f2fe" /><stop offset="100%" stop-color="#2563eb" />'
    + '</linearGradient>'
    + '</defs>'
    + '<path class="m-path" d="M 45,175 C 32,110 42,75 75,75 C 100,75 112,115 135,115 C 158,115 152,28 198,28 C 238,28 232,140 226,210" '
    + 'stroke="url(#aiRibbonGradient)" stroke-width="26" stroke-linecap="round" stroke-linejoin="round" />'
    + '<rect class="blue-laser" x="175" y="78" width="30" height="12" rx="6" fill="url(#aiLaserGradient)" />'
    + '</svg>'
    + '<div class="ai-loader-text">' + (texto || 'Cargando…') + '</div>'
    + '</div>';
}

function enviarMensajeAvi(event) {
  event.preventDefault();
  const input = document.getElementById('aviTexto');
  const chat = document.getElementById('aviChat');
  const texto = input.value.trim();
  if (!texto) return false;

  const burbujaUsuario = document.createElement('div');
  burbujaUsuario.className = 'bubble user';
  burbujaUsuario.textContent = texto;
  chat.appendChild(burbujaUsuario);

  const burbujaCargando = document.createElement('div');
  burbujaCargando.className = 'bubble bot';
  burbujaCargando.innerHTML = aiLoaderHTML('Pensando…');
  chat.appendChild(burbujaCargando);
  chat.scrollTop = chat.scrollHeight;

  input.value = '';

  const csrftoken = document.querySelector('#aviForm input[name=csrfmiddlewaretoken]').value;

  // si la respuesta tarda más de 100 segundos (el límite de Cloudflare) se corta y se avisa, en vez de dejar el "Pensando…" para siempre
  const control = new AbortController();
  const limite = setTimeout(function () { control.abort(); }, 100000);

  fetch('/avi/chat/', {
    method: 'POST',
    signal: control.signal,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken,
    },
    body: JSON.stringify({
      mensaje: texto,
      // en qué pantalla está y en qué carrito trabaja: la IA solo recibe las herramientas de esa pantalla
      pantalla: (document.querySelector('.app-shell') || {dataset: {}}).dataset.modulo || null,
      carrito: window.carritoActivo || 1,
    }),
  })
    .then(function (respuesta) { return respuesta.json(); })
    .then(function (datos) {
      burbujaCargando.textContent = limpiarTextoIA(datos.respuesta);
      if (datos.refrescar) refrescarVistaActual();
    })
    .catch(function (error) {
      burbujaCargando.textContent = error && error.name === 'AbortError'
        ? 'La IA tardó demasiado en contestar. Intenta de nuevo.'
        : 'No pude conectarme con el asistente. Intenta de nuevo.';
    })
    .finally(function () {
      clearTimeout(limite);
      chat.scrollTop = chat.scrollHeight;
    });

  return false;
}

function refrescarVistaActual() {
  // el punto de venta se dibuja con JS: se vuelve a pedir la caja al servidor
  if (window.refrescarPOS) { window.refrescarPOS(); return; }
  // trae la página actual y solo reemplaza el contenido del módulo (carrito,
  // catálogo, gastos…) sin tocar el panel del chat ni perder la conversación
  fetch(window.location.pathname + window.location.search)
    .then(function (r) { return r.text(); })
    .then(function (html) {
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const nuevoMain = doc.querySelector('.app-main');
      const actual = document.querySelector('.app-main');
      if (nuevoMain && actual) actual.innerHTML = nuevoMain.innerHTML;
    })
    .catch(function () {});
}

function dineroMx(valor) {
  return Number(valor || 0).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
}

// Abre el modal de la IA, pide el texto al servidor y lo muestra.
// conNumeros = true agrega las tres cifras de ayer (ventas, ganancia y gastos).
function mostrarModalAvi(titulo, url, textoCargando, textoError, conNumeros) {
  const cuerpo = document.getElementById('resumenAviCuerpo');
  if (!cuerpo) return;

  document.getElementById('resumenAviTitulo').innerHTML = '<i class="bi bi-stars"></i> ' + titulo;
  cuerpo.innerHTML = aiLoaderHTML(textoCargando);
  openModal('resumen-avi');

  fetch(url)
    .then(function (r) { return r.json(); })
    .then(function (datos) {
      cuerpo.innerHTML = '';

      if (conNumeros && datos.total_ventas !== undefined) {
        const numeros = document.createElement('div');
        numeros.className = 'resumen-numeros';
        numeros.innerHTML = ''
          + '<div><span>Vendiste</span><strong>' + dineroMx(datos.total_ventas) + '</strong></div>'
          + '<div class="ganancia"><span>Ganaste</span><strong>' + dineroMx(datos.ganancia) + '</strong></div>'
          + '<div class="gastos"><span>Gastaste</span><strong>' + dineroMx(datos.total_gastos) + '</strong></div>';
        cuerpo.appendChild(numeros);
      }

      // textContent (no innerHTML) para que nada de lo que conteste la IA se ejecute como código
      const texto = document.createElement('p');
      texto.className = 'resumen-texto';
      texto.textContent = String(datos.respuesta || '').replace(/\*\*/g, '');
      cuerpo.appendChild(texto);
    })
    .catch(function () {
      cuerpo.textContent = textoError;
    });
}

// Resumen de "cómo te fue ayer" al iniciar sesión
function mostrarResumenAvi() {
  mostrarModalAvi(
    'Así te fue ayer',
    '/avi/resumen/',
    'Revisando cómo te fue ayer…',
    'No pude generar tu resumen de ayer. Intenta de nuevo.',
    true
  );
}

// Explicación del dashboard ('dashboard') o de los reportes financieros ('reportes')
function explicarConAvi(tipo, parametros) {
  const consulta = parametros ? '?' + new URLSearchParams(parametros).toString() : '';
  mostrarModalAvi(
    tipo === 'reportes' ? 'Tus reportes, explicados' : (tipo === 'pronostico' ? 'Tu pronóstico, explicado' : 'Tu negocio, explicado'),
    '/avi/explicar/' + tipo + '/' + consulta,
    tipo === 'pronostico' ? 'Revisando tu pronóstico…' : 'Revisando tus números…',
    'No pude explicarte tus números. Intenta de nuevo.',
    false
  );
}

// Dictado como un micrófono de radio: se empieza a escuchar al presionar el botón y se deja de
// escuchar al soltarlo. Mientras se mantiene presionado el texto va apareciendo en el chat.
// Usa el reconocimiento de voz del navegador, que existe en Chrome y Edge (no en Firefox) y
// necesita internet y permiso para el micrófono.
const MIC = { reconocimiento: null, sostenido: false, inicio: 0, base: '', permiso: false, error: '', idioma: 'es-MX' };

function reconocimientoDelNavegador() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function mensajeDeErrorDeVoz(codigo) {
  if (codigo === 'not-allowed' || codigo === 'service-not-allowed') {
    return 'El navegador no tiene permiso para usar el micrófono. Permítelo en el candado de la barra de direcciones y vuelve a intentar.';
  }
  if (codigo === 'audio-capture') return 'No encontré un micrófono conectado.';
  if (codigo === 'network') return 'El dictado necesita internet: el navegador manda el audio a un servicio de reconocimiento de voz.';
  if (codigo === 'no-speech') return 'No escuché nada. Mantén presionado el micrófono mientras hablas.';
  return 'No pude dictar (' + codigo + ').';
}

function estadoDelMicrofono(escuchando) {
  const boton = document.querySelector('.avi-mic-btn');
  const input = document.getElementById('aviTexto');
  if (boton) boton.classList.toggle('escuchando', escuchando);
  if (input) {
    if (escuchando) { input.dataset.marcador = input.placeholder; input.placeholder = 'Escuchando… suelta el micrófono al terminar'; }
    else if (input.dataset.marcador) { input.placeholder = input.dataset.marcador; delete input.dataset.marcador; }
  }
}

// la primera vez se pide el permiso con una pregunta aparte: si el aviso del navegador saliera justo
// al empezar a dictar, le quitaría el clic al botón y el dictado se cortaría solo
function pedirPermisoDelMicrofono() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { MIC.permiso = true; return Promise.resolve(true); }
  return navigator.mediaDevices.getUserMedia({ audio: true }).then(function (flujo) {
    flujo.getTracks().forEach(function (pista) { pista.stop(); });
    MIC.permiso = true;
    showToast('Micrófono listo. Ahora mantén presionado el botón y habla.', 'success');
    return true;
  }).catch(function (error) {
    const sinMicrofono = error && (error.name === 'NotFoundError' || error.name === 'OverconstrainedError');
    showToast(mensajeDeErrorDeVoz(sinMicrofono ? 'audio-capture' : 'not-allowed'), 'alerta');
    return false;
  });
}

function empezarADictar() {
  const input = document.getElementById('aviTexto');
  const Reconocimiento = reconocimientoDelNavegador();
  MIC.inicio = Date.now();
  MIC.error = '';
  MIC.base = input.value.trim() ? input.value.trim() + ' ' : '';

  const reconocimiento = new Reconocimiento();
  reconocimiento.lang = MIC.idioma;
  reconocimiento.continuous = true;      // no se corta solo cuando haces una pausa
  reconocimiento.interimResults = true;  // se va viendo lo que entiende mientras hablas
  reconocimiento.maxAlternatives = 1;

  reconocimiento.onstart = function () { estadoDelMicrofono(true); };
  reconocimiento.onresult = function (evento) {
    let texto = '';
    for (let i = 0; i < evento.results.length; i++) texto += evento.results[i][0].transcript;
    input.value = MIC.base + texto.trim();
  };
  reconocimiento.onerror = function (evento) { MIC.error = evento.error || 'desconocido'; };
  reconocimiento.onend = function () {
    estadoDelMicrofono(false);
    MIC.reconocimiento = null;
    input.focus();
    if (MIC.error === 'language-not-supported' && MIC.idioma !== 'es') {
      MIC.idioma = 'es';  // algunos navegadores solo traen "es" a secas
      if (MIC.sostenido) empezarADictar();
    } else if (MIC.error && MIC.error !== 'aborted') {
      showToast(mensajeDeErrorDeVoz(MIC.error), 'alerta');
    } else if (MIC.sostenido && Date.now() - MIC.inicio < 1500) {
      showToast('El navegador cortó el dictado. Intenta de nuevo.', 'info');
    }
  };

  MIC.reconocimiento = reconocimiento;
  try { reconocimiento.start(); } catch (e) { MIC.reconocimiento = null; showToast(mensajeDeErrorDeVoz('desconocido'), 'alerta'); }
}

function alPresionarMicrofono() {
  if (MIC.sostenido) return;
  MIC.sostenido = true;
  MIC.inicio = Date.now();
  if (!reconocimientoDelNavegador()) {
    showToast('Este navegador no permite dictar por voz. Usa Google Chrome o Microsoft Edge.', 'info');
    return;
  }
  if (!MIC.permiso) {
    pedirPermisoDelMicrofono();
    return;
  }
  empezarADictar();
}

function alSoltarMicrofono() {
  if (!MIC.sostenido) return;
  const duracion = Date.now() - MIC.inicio;
  MIC.sostenido = false;
  if (!MIC.reconocimiento) return;
  if (duracion < 400) showToast('Mantén presionado el micrófono mientras hablas y suéltalo al terminar.', 'info');
  MIC.reconocimiento.stop();  // al parar, el navegador entrega lo último que entendió
}

document.addEventListener('DOMContentLoaded', function () {
  const boton = document.querySelector('.avi-mic-btn');
  if (!boton) return;

  if (!reconocimientoDelNavegador()) {
    boton.classList.add('sin-soporte');
    boton.title = 'Este navegador no permite dictar por voz. Usa Google Chrome o Microsoft Edge.';
  }

  // si el permiso ya estaba dado no hace falta preguntarlo otra vez
  try {
    navigator.permissions.query({ name: 'microphone' }).then(function (estado) {
      if (estado.state === 'granted') MIC.permiso = true;
    }).catch(function () {});
  } catch (e) {}

  boton.addEventListener('pointerdown', function (evento) {
    if (evento.pointerType === 'mouse' && evento.button !== 0) return;
    evento.preventDefault();
    // el soltar se escucha en toda la ventana, así no se pierde si el dedo o el ratón se salen del botón
    const soltar = function () {
      window.removeEventListener('pointerup', soltar);
      window.removeEventListener('pointercancel', soltar);
      alSoltarMicrofono();
    };
    window.addEventListener('pointerup', soltar);
    window.addEventListener('pointercancel', soltar);
    alPresionarMicrofono();
  });
  boton.addEventListener('contextmenu', function (evento) { evento.preventDefault(); });  // el toque largo no abre menú
  window.addEventListener('blur', alSoltarMicrofono);  // si la ventana pierde el foco, se deja de escuchar
  // con teclado: mantener la barra espaciadora
  boton.addEventListener('keydown', function (evento) {
    if (evento.key === ' ' && !evento.repeat) { evento.preventDefault(); alPresionarMicrofono(); }
  });
  boton.addEventListener('keyup', function (evento) {
    if (evento.key === ' ') alSoltarMicrofono();
  });
});

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('form[data-validar]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      const invalido = form.querySelector(':invalid');
      if (invalido) {
        event.preventDefault();
        const grupo = invalido.closest('.form-group');
        const etiqueta = grupo ? grupo.querySelector('label') : null;
        const nombreCampo = etiqueta ? etiqueta.textContent.replace('*', '').trim() : 'un campo obligatorio';
        showToast('Falta llenar: ' + nombreCampo, 'info');
        invalido.focus();
      }
    });
  });
});

// Aviso de reabastecimiento: una sola vez por sesión del navegador (y otra vez si suben las rojas)
document.addEventListener('DOMContentLoaded', function () {
  const shell = document.querySelector('.app-shell');
  if (!shell) return;
  const rojas = parseInt(shell.dataset.alertasRojo || '0', 10);
  if (!rojas) return;

  let avisadas = '0';
  try { avisadas = sessionStorage.getItem('alertas_rojas_avisadas') || '0'; } catch (e) {}
  if (rojas <= parseInt(avisadas, 10)) return;

  try { sessionStorage.setItem('alertas_rojas_avisadas', String(rojas)); } catch (e) {}
  const texto = rojas === 1 ? '1 producto llegó a su mínimo' : rojas + ' productos llegaron a su mínimo';
  showToast('🔴 ' + texto + '. <a href="' + shell.dataset.urlAlertas + '">Ver qué resurtir</a>', 'alerta');
});

function showToast(mensaje, tipo) {
  let stack = document.querySelector('.toast-stack');
  if (!stack) {
    stack = document.createElement('div');
    stack.className = 'toast-stack';
    document.body.appendChild(stack);
  }
  const toast = document.createElement('div');
  toast.className = 'toast ' + (tipo || 'info');
  toast.innerHTML = '<i class="bi bi-exclamation-circle-fill"></i><span>' + mensaje + '</span>';
  stack.appendChild(toast);
  setTimeout(function () { toast.remove(); }, tipo === 'alerta' ? 9000 : 4000);
}

// Ayuda: filtra las preguntas frecuentes mientras escribes (sin importar acentos)
function filtrarAyuda(texto) {
  const buscado = texto.trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  let visibles = 0;

  document.querySelectorAll('#modal-ayuda .faq-item').forEach(function (item) {
    const contenido = item.textContent.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    const coincide = !buscado || contenido.includes(buscado);
    item.style.display = coincide ? '' : 'none';
    // si se está buscando, se abren las que coinciden para ver la respuesta
    item.open = Boolean(buscado) && coincide;
    if (coincide) visibles += 1;
  });

  // se esconden los títulos de grupo que se quedaron sin preguntas
  document.querySelectorAll('#modal-ayuda [data-grupo]').forEach(function (grupo) {
    const hayVisibles = [...grupo.querySelectorAll('.faq-item')].some(function (i) { return i.style.display !== 'none'; });
    grupo.style.display = hayVisibles ? '' : 'none';
  });

  document.getElementById('ayudaSinResultados').style.display = visibles === 0 ? 'block' : 'none';
}

// Un aviso que se quiere mostrar DESPUÉS de recargar la página (por ejemplo "Agregué la mercancía…")
function guardarAvisoPendiente(texto) {
  try { sessionStorage.setItem('aviso_pendiente', texto); } catch (e) {}
}

document.addEventListener('DOMContentLoaded', function () {
  let aviso = null;
  try {
    aviso = sessionStorage.getItem('aviso_pendiente');
    sessionStorage.removeItem('aviso_pendiente');
  } catch (e) {}
  if (aviso) showToast(aviso, 'success');
});

// Primera vez que entra: primero la guía de los colores y después el video de bienvenida (RF-S05)
function abrirVideoBienvenida() {
  const video = document.getElementById('videoBienvenida');
  if (!video) return;
  video.src = video.dataset.src;
  openModal('video-bienvenida');
}

document.addEventListener('DOMContentLoaded', function () {
  if (document.getElementById('modal-guia-colores')) openModal('guia-colores');
  else abrirVideoBienvenida();
});

function cerrarGuiaColores() {
  closeModal('guia-colores');
  const formulario = document.getElementById('formGuiaVista');
  if (formulario) {
    fetch(formulario.action, {
      method: 'POST',
      headers: { 'X-CSRFToken': formulario.querySelector('input[name=csrfmiddlewaretoken]').value },
    }).catch(function () {});
  }
  abrirVideoBienvenida();
}

function cerrarVideoBienvenida() {
  const video = document.getElementById('videoBienvenida');
  if (video) video.src = '';  // así el video deja de sonar
  closeModal('video-bienvenida');
  const formulario = document.getElementById('formVideoVisto');
  if (formulario) {
    fetch(formulario.action, {
      method: 'POST',
      headers: { 'X-CSRFToken': formulario.querySelector('input[name=csrfmiddlewaretoken]').value },
    }).catch(function () {});
  }
}
