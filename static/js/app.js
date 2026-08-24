/* Zindagi — frontend SPA logic (vanilla JS, no build step). */

const API = '/api';
const $ = (id) => document.getElementById(id);
const state = {
  token: localStorage.getItem('zindagi_token') || null,
  role: localStorage.getItem('zindagi_role') || null,
  name: localStorage.getItem('zindagi_name') || null,
  me: null,
};

/* ---------- Helpers ---------- */
async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const res = await fetch(API + path, { ...opts, headers });
  if (res.status === 401) {
    logout();
    throw new Error('Session expired — please log in again.');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = typeof detail === 'string' ? detail : (Array.isArray(detail) && detail[0]?.msg) || 'Something went wrong';
    throw new Error(msg);
  }
  return data;
}

function setMsg(el, text, kind = 'err') {
  el.textContent = text;
  el.className = `msg ${kind}`;
}

function show(view) {
  document.querySelectorAll('.view').forEach((v) => v.classList.add('hidden'));
  $(`view-${view}`).classList.remove('hidden');
  window.scrollTo({ top: 0 });
}

function logout() {
  state.token = null; state.role = null; state.name = null;
  localStorage.removeItem('zindagi_token');
  localStorage.removeItem('zindagi_role');
  localStorage.removeItem('zindagi_name');
  renderNav();
  show('landing');
  loadLanding();
}

function renderNav() {
  const nav = $('topnav');
  if (state.token) {
    nav.innerHTML = `
      <span class="nav-user">👋 ${escapeHtml(state.name || '')}</span>
      <button class="nav-link" data-nav="${state.role === 'donor' ? 'donor' : 'requester'}">Dashboard</button>
      <button class="nav-link" id="nav-logout">Log out</button>`;
    $('nav-logout').onclick = logout;
  } else {
    nav.innerHTML = `
      <button class="nav-link" data-nav="login">Log in</button>
      <button class="btn btn-primary btn-sm" data-nav="register">Join</button>`;
  }
  document.querySelectorAll('[data-nav]').forEach((b) => {
    b.onclick = () => navigate(b.dataset.nav);
  });
}

function navigate(view) {
  if ((view === 'donor' || view === 'requester') && !state.token) {
    view = 'login';
  }
  if (view === 'login' || view === 'register') {
    setupAuth(view);
    return;
  }
  if (view === 'donor') loadDonorDashboard();
  if (view === 'requester') loadRequesterDashboard();
  if (view === 'landing') loadLanding();
  show(view === 'donor' ? 'donor' : view === 'requester' ? 'requester' : view);
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function timeAgo(iso) {
  if (!iso) return '—';
  const d = new Date(iso.replace(' ', 'T'));
  const sec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (sec < 60) return 'just now';
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

function urgencyBadge(u) {
  return `<span class="badge badge-${u}">${u}</span>`;
}

function statusBadge(s) {
  return `<span class="badge badge-${s}">${s}</span>`;
}

/* ---------- Landing ---------- */
async function loadLanding() {
  try {
    const [guide, reqs] = await Promise.all([
      api('/blood-groups'),
      api('/requests?status_filter=open'),
    ]);
    const open = reqs.length;
    $('landing-stats').innerHTML = `
      <div class="stat"><b>${open}</b><span>open requests</span></div>
      <div class="stat"><b>8</b><span>blood groups</span></div>
      <div class="stat"><b>${guide.groups.length * 3}</b><span>donor profiles</span></div>`;

    const grid = $('guide-grid');
    grid.innerHTML = guide.groups
      .map((g) => {
        const donors = (guide.compatibility[g] || []).join(' · ');
        return `<div class="guide-cell"><b>${g}</b><span>can receive from:<br/>${donors}</span></div>`;
      })
      .join('');
  } catch (e) {
    $('landing-stats').innerHTML = `<span class="muted">${escapeHtml(e.message)}</span>`;
  }
}

/* ---------- Auth ---------- */
function setupAuth(mode) {
  $('auth-mode').value = mode;
  $('auth-title').textContent = mode === 'register' ? 'Create an account' : 'Welcome back';
  $('auth-sub').textContent = mode === 'register' ? 'Join the donor network' : 'Log in to continue';
  $('auth-submit').textContent = mode === 'register' ? 'Create account' : 'Log in';
  $('auth-switch-text').textContent = mode === 'register' ? 'Already have an account?' : 'New to Zindagi?';
  $('auth-switch-link').textContent = mode === 'register' ? 'Log in' : 'Create account';
  $('auth-switch-link').onclick = (e) => { e.preventDefault(); setupAuth(mode === 'register' ? 'login' : 'register'); };
  $('auth-name').closest('.field').style.display = mode === 'register' ? '' : 'none';
  $('auth-phone').closest('.field').style.display = mode === 'register' ? '' : 'none';
  $('auth-password').closest('.field').querySelector('label').innerHTML = mode === 'register'
    ? 'Password <span class="muted">(min 8 chars)</span>' : 'Password';
  setMsg($('auth-msg'), '', 'ok');
  show('auth');
}

$('auth-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const mode = $('auth-mode').value;
  const body = { email: $('auth-email').value, password: $('auth-password').value };
  if (mode === 'register') {
    body.full_name = $('auth-name').value;
    body.phone = $('auth-phone').value;
    body.role = document.querySelector('input[name="role"]:checked').value;
  }
  try {
    const data = await api('/auth/' + (mode === 'register' ? 'register' : 'login'), { method: 'POST', body: JSON.stringify(body) });
    state.token = data.access_token;
    state.role = data.role;
    state.name = data.full_name;
    localStorage.setItem('zindagi_token', data.access_token);
    localStorage.setItem('zindagi_role', data.role);
    localStorage.setItem('zindagi_name', data.full_name);
    renderNav();
    navigate(state.role === 'donor' ? 'donor' : 'requester');
  } catch (err) {
    setMsg($('auth-msg'), err.message);
  }
});

/* ---------- Donor dashboard ---------- */
async function loadDonorDashboard() {
  show('donor');
  try {
    const [me, prof, reqs] = await Promise.all([
      api('/auth/me'),
      api('/donors/profile'),
      api('/requests?status_filter=open'),
    ]);
    state.me = me;
    $('donor-name').textContent = `${me.full_name} · ${me.email}`;
    $('donor-bg').value = prof.blood_group;
    $('donor-city').value = prof.city;
    $('donor-area').value = prof.area;
    $('donor-by').value = prof.birth_year;
    $('donor-wt').value = prof.weight_kg;
    const v = $('donor-verified');
    if (prof.is_verified) { v.className = 'badge badge-verified'; v.textContent = '✓ Verified'; }
    else { v.className = 'badge badge-muted'; v.textContent = 'Not verified'; }
    const btn = $('btn-availability');
    btn.textContent = prof.is_available ? 'Mark unavailable' : 'Mark available';
    btn.className = 'btn btn-sm ' + (prof.is_available ? 'btn-ghost' : 'btn-green');
    btn.onclick = async () => {
      await api('/donors/availability', { method: 'PATCH', body: JSON.stringify({ is_available: !prof.is_available }) });
      loadDonorDashboard();
    };
    $('donor-requests').innerHTML = reqs.length
      ? reqs.slice(0, 5).map((r) => `
        <div class="list-item">
          <div class="li-main">
            <div class="li-title">${escapeHtml(r.patient_name)} <span class="badge badge-open">${r.blood_group}</span> ${urgencyBadge(r.urgency)}</div>
            <div class="li-sub">${escapeHtml(r.hospital)} · ${escapeHtml(r.city)}, ${escapeHtml(r.area)} · ${timeAgo(r.created_at)}</div>
          </div>
          <button class="btn btn-sm btn-outline" onclick="viewMatches(${r.id})">Matches</button>
        </div>`).join('')
      : '<p class="muted">No open requests right now.</p>';
  } catch (err) {
    setMsg($('donor-msg'), err.message);
  }
}

$('donor-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await api('/donors/profile', {
      method: 'PUT',
      body: JSON.stringify({
        blood_group: $('donor-bg').value,
        city: $('donor-city').value,
        area: $('donor-area').value,
        birth_year: parseInt($('donor-by').value, 10),
        weight_kg: parseInt($('donor-wt').value, 10),
        is_available: true,
      }),
    });
    setMsg($('donor-msg'), 'Profile saved ✓', 'ok');
    loadDonorDashboard();
  } catch (err) {
    setMsg($('donor-msg'), err.message);
  }
});

/* ---------- Requester dashboard ---------- */
async function loadRequesterDashboard() {
  show('requester');
  try {
    const reqs = await api('/requests/my');
    $('my-requests').innerHTML = reqs.length
      ? reqs.map((r) => `
        <div class="list-item">
          <div class="li-main">
            <div class="li-title">${escapeHtml(r.patient_name)} <span class="badge badge-open">${r.blood_group}</span> ${statusBadge(r.status)}</div>
            <div class="li-sub">${escapeHtml(r.hospital)} · ${escapeHtml(r.city)} · ${urgencyBadge(r.urgency)} · expires ${timeAgo(r.expires_at)}</div>
          </div>
          ${r.status === 'open' ? `<button class="btn btn-sm btn-outline" onclick="viewMatches(${r.id})">Find donors</button>` : ''}
        </div>`).join('')
      : '<p class="muted">No requests yet — post your first one above.</p>';
  } catch (err) {
    console.error(err);
  }
}

$('request-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const req = await api('/requests', {
      method: 'POST',
      body: JSON.stringify({
        patient_name: $('req-patient').value,
        blood_group: $('req-bg').value,
        units_needed: parseInt($('req-units').value, 10),
        hospital: $('req-hospital').value,
        city: $('req-city').value,
        area: $('req-area').value,
        urgency: $('req-urgency').value,
        notes: $('req-notes').value || null,
      }),
    });
    setMsg($('request-msg'), `Request posted — #${req.id} ${req.blood_group} at ${req.hospital}`, 'ok');
    e.target.reset();
    loadRequesterDashboard();
    openMatchesModal(req.id);
  } catch (err) {
    setMsg($('request-msg'), err.message);
  }
});

/* ---------- Matches modal ---------- */
async function viewMatches(requestId) {
  try {
    const req = await api(`/requests/${requestId}`);
    openMatchesModal(requestId, req);
  } catch (err) {
    alert(err.message);
  }
}

async function openMatchesModal(requestId, reqMeta) {
  const modal = $('modal');
  modal.classList.remove('hidden');
  $('modal-body').innerHTML = '<p class="muted">Searching for compatible donors…</p>';
  try {
    const matches = await api(`/requests/${requestId}/matches`);
    $('modal-body').innerHTML = `
      <h3>${reqMeta ? `${escapeHtml(reqMeta.patient_name)} — ${reqMeta.blood_group}` : 'Compatible donors'}</h3>
      <p class="muted" style="margin-bottom:14px">${matches.length} compatible donor${matches.length === 1 ? '' : 's'} found${reqMeta ? ` in ${escapeHtml(reqMeta.city)} and nearby` : ''}.</p>
      ${matches.length ? matches.map((m) => `
        <div class="match-row">
          <div>
            <div class="m-name">${escapeHtml(m.name)} <span class="badge badge-open">${m.blood_group}</span> ${m.is_verified ? '<span class="badge badge-verified">✓ verified</span>' : ''}</div>
            <div class="m-sub">📞 ${escapeHtml(m.phone)} · 📍 ${escapeHtml(m.city)}, ${escapeHtml(m.area)} · age ${m.age ?? '?'} · ${m.donation_count} donations</div>
          </div>
          <button class="btn btn-sm btn-primary" onclick="fulfillRequest(${requestId}, ${m.donor_id})">Got blood</button>
        </div>`).join('')
      : '<p class="muted">No eligible donors right now. Try sharing the request with your network.</p>'}`;
  } catch (err) {
    $('modal-body').innerHTML = `<p class="msg err">${escapeHtml(err.message)}</p>`;
  }
}

async function fulfillRequest(requestId, donorId) {
  if (!confirm('Confirm this donor provided the blood?')) return;
  try {
    const req = await api(`/requests/${requestId}/fulfill`, {
      method: 'POST',
      body: JSON.stringify({ donor_id: donorId, units: 1 }),
    });
    alert(`Request fulfilled — ${req.blood_group} confirmed. Thank you for saving a life! 🩸`);
    $('modal').classList.add('hidden');
    loadRequesterDashboard();
  } catch (err) {
    alert(err.message);
  }
}

$('modal-close').onclick = () => $('modal').classList.add('hidden');
$('modal').addEventListener('click', (e) => { if (e.target === $('modal')) $('modal').classList.add('hidden'); });

/* ---------- Init ---------- */
renderNav();
loadLanding();
if (state.token) navigate(state.role === 'donor' ? 'donor' : 'requester');
