const stateAviMap = {
    normal:      { msgs: [] },
    alta:        { msgs: ['avi-alta-u','avi-alta'] },
    modificar:   { msgs: ['avi-mod-u','avi-mod'] },
    proveedores: { msgs: ['avi-prov-u','avi-prov'] },
    alertas:     { msgs: ['avi-alert-u','avi-alert'] },
  };
  const allAviMsgs = ['avi-alta','avi-alta-u','avi-mod','avi-mod-u','avi-prov','avi-prov-u','avi-alert','avi-alert-u'];

  function showState(name, btn) {
    // states
    document.querySelectorAll('.state').forEach(s => s.classList.remove('active'));
    document.getElementById('state-' + name).classList.add('active');
    // demo btns
    document.querySelectorAll('.demo-btn').forEach(b => b.classList.remove('active-demo'));
    if (btn) btn.classList.add('active-demo');
    // AVI messages
    allAviMsgs.forEach(id => document.getElementById(id).style.display = 'none');
    (stateAviMap[name]?.msgs || []).forEach(id => document.getElementById(id).style.display = 'flex');
    // open panel
    const panelMap = { alta: 'panel-alta', modificar: 'panel-modificar', proveedores: 'panel-proveedores' };
    if (panelMap[name]) openPanel(panelMap[name]);
    else closePanel();
  }

  function openPanel(panelId) {
    ['panel-alta','panel-modificar','panel-proveedores'].forEach(id => {
      const el = document.getElementById(id);
      el.style.display = 'none';
    });
    const target = document.getElementById(panelId);
    target.style.display = 'flex';
    document.getElementById('panelOverlay').classList.add('open');
  }

  function closePanel() {
    document.getElementById('panelOverlay').classList.remove('open');
  }

  function closePanelIfOutside(e) {
    if (e.target === document.getElementById('panelOverlay')) closePanel();
  }

  function toggleCat(el) { el.classList.toggle('selected'); }

  function selectProv(card) {
    document.querySelectorAll('.provider-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
  }

  function calcMargen() {
    const costo  = parseFloat(document.getElementById('inputCosto').value)  || 0;
    const precio = parseFloat(document.getElementById('inputPrecio').value) || 0;
    if (precio > 0) {
      const m = ((precio - costo) / precio * 100).toFixed(1);
      document.getElementById('margenLabel').textContent = m + '%';
      const fill = Math.min(Math.max(m, 0), 60);
      document.getElementById('margenFill').style.width = fill + '%';
      document.getElementById('margenFill').style.background =
        m < 15 ? 'var(--color-danger)' : m < 25 ? 'var(--color-warning)' : 'var(--color-success)';
    }
  }

  function openAvi()  { document.getElementById('aviPanel').classList.add('open'); document.getElementById('aviOverlay').classList.add('open'); }
  function closeAvi() { document.getElementById('aviPanel').classList.remove('open'); document.getElementById('aviOverlay').classList.remove('open'); }
