function showState(n, btn) {
    document.querySelectorAll('.state').forEach(s => s.classList.remove('active'));
    document.getElementById('state' + n).classList.add('active');
    document.querySelectorAll('.demo-btn').forEach(b => b.classList.remove('active-demo'));
    btn.classList.add('active-demo');

    document.getElementById('userMsg').style.display    = n >= 3 ? 'flex' : 'none';
    document.getElementById('botConfirm').style.display = n >= 3 ? 'flex' : 'none';
    document.getElementById('ticketMsg').style.display  = n === 4 ? 'flex' : 'none';

    const toast = document.getElementById('ticketToast');
    if (n === 4) {
      toast.style.display = 'flex';
    } else {
      toast.style.display = 'none';
      closeDrawer();
    }
  }

  function openDrawer()  { document.getElementById('ticketDrawer').classList.add('open'); }
  function closeDrawer() { document.getElementById('ticketDrawer').classList.remove('open'); }
  function closeToast()  { document.getElementById('ticketToast').style.display = 'none'; }

  function openAvi() {
    document.getElementById('aviPanel').classList.add('open');
    document.getElementById('aviOverlay').classList.add('open');
  }
  function closeAvi() {
    document.getElementById('aviPanel').classList.remove('open');
    document.getElementById('aviOverlay').classList.remove('open');
  }
