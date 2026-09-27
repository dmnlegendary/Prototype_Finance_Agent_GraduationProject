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

function limpiarChatAvi() {
  const chat = document.getElementById('aviChat');
  if (chat) chat.innerHTML = '<div class="bubble bot">Chat vaciado. ¿En qué puedo ayudarte?</div>';
}

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
  const modeloSelect = document.getElementById('aviModelo');
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

  fetch('/avi/chat/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken,
    },
    body: JSON.stringify({ mensaje: texto, modelo: modeloSelect ? modeloSelect.value : 'chatgpt' }),
  })
    .then(function (respuesta) { return respuesta.json(); })
    .then(function (datos) {
      burbujaCargando.textContent = datos.respuesta;
    })
    .catch(function () {
      burbujaCargando.textContent = 'No pude conectarme con el asistente. Intenta de nuevo.';
    })
    .finally(function () {
      chat.scrollTop = chat.scrollHeight;
    });

  return false;
}

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
  setTimeout(function () { toast.remove(); }, 4000);
}
