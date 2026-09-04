/* =================================================================
   RegisterAI — Milestone 3 Script (milestone3.js)
   Sponsorship Agent/Directory/Outreach/Follow-Ups/Performance and
   Incident Agent/Management/Alerts.
================================================================= */

function m3ChartDefaults() {
  if (typeof Chart === 'undefined') return;
  Chart.defaults.color = '#9aa3c0';
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.borderColor = 'rgba(255,255,255,0.08)';
}
const M3_COLORS = ['#6c5ce7', '#00d4ff', '#a855f7', '#ff5da2', '#22c55e', '#f59e0b', '#ef4444', '#14b8a6', '#3b82f6', '#94a3b8'];

/* =================================================================
   SPONSOR MANAGEMENT — ADD/EDIT/DELETE/EVALUATE
================================================================= */
function initSponsorTable() {
  const grid = document.getElementById('sponsorCardsGrid');
  if (!grid) return;

  const modal = document.getElementById('sponsorModal');
  const form = document.getElementById('sponsorForm');
  const addBtn = document.getElementById('addSponsorBtn');
  const closeBtn = document.getElementById('closeSponsorModal');
  const modalTitle = document.getElementById('sponsorModalTitle');

  function openModal(title, sponsor) {
    modalTitle.textContent = title;
    const fields = ['id','company_name','industry','website','location','target_audience','keywords',
      'sponsorship_category','budget_potential','estimated_budget','contact_person','contact_email',
      'contact_phone','status','notes'];
    fields.forEach(f => {
      const el = document.getElementById('sponsor_' + f);
      if (el) el.value = sponsor ? (sponsor[f] ?? '') : (f === 'status' ? 'Discovered' : (f === 'budget_potential' ? 'Medium' : ''));
    });
    modal.classList.add('show');
  }

  addBtn && addBtn.addEventListener('click', () => openModal('Add Potential Sponsor', null));
  closeBtn && closeBtn.addEventListener('click', () => modal.classList.remove('show'));
  modal && modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });

  grid.addEventListener('click', function (e) {
    const card = e.target.closest('.sponsor-card');
    if (!card) return;
    const sponsorId = card.dataset.id;

    if (e.target.closest('.edit-sponsor-btn')) {
      fetch(`/api/sponsors/${sponsorId}`).then(r => r.json()).then(data => {
        if (data.success) openModal('Edit Sponsor', data.sponsor);
      });
    }
    if (e.target.closest('.delete-sponsor-btn')) {
      if (!confirm('Delete this sponsor? All communication history will be removed too.')) return;
      fetch(`/api/sponsors/${sponsorId}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => { if (data.success) { card.remove(); showQuickToast(data.message, 'success'); } });
    }
    if (e.target.closest('.evaluate-sponsor-btn')) {
      fetch(`/api/sponsors/${sponsorId}/evaluate`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            showQuickToast(`Suitability score: ${data.score}% — ${data.match_category}`, 'success');
            setTimeout(() => window.location.reload(), 900);
          }
        });
    }
  });

  form && form.addEventListener('submit', function (e) {
    e.preventDefault();
    const id = document.getElementById('sponsor_id').value;
    const fields = ['company_name','industry','website','location','target_audience','keywords',
      'sponsorship_category','budget_potential','estimated_budget','contact_person','contact_email',
      'contact_phone','status','notes'];
    const payload = {};
    fields.forEach(f => { payload[f] = document.getElementById('sponsor_' + f).value; });
    const url = id ? `/api/sponsors/${id}` : '/api/sponsors';
    fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showQuickToast(data.message, 'success');
          modal.classList.remove('show');
          setTimeout(() => window.location.reload(), 600);
        } else {
          showQuickToast(data.message || 'Could not save sponsor.', 'error');
        }
      });
  });
}

/* =================================================================
   SPONSOR PROFILE — RECORD COMMUNICATION / FOLLOW-UP / OPPORTUNITY
================================================================= */
function initSponsorProfile(sponsorId) {
  const interactionForm = document.getElementById('interactionForm');
  interactionForm && interactionForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const payload = {
      interaction_type: document.getElementById('int_type').value,
      communication_method: document.getElementById('int_method').value,
      subject: document.getElementById('int_subject').value,
      message: document.getElementById('int_message').value,
      sponsor_response: document.getElementById('int_response').value,
      next_action: document.getElementById('int_next_action').value,
      follow_up_date: document.getElementById('int_followup_date').value,
      new_status: document.getElementById('int_new_status').value,
    };
    fetch(`/api/sponsors/${sponsorId}/interactions`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(r => r.json()).then(data => {
      if (data.success) { showQuickToast(data.message, 'success'); setTimeout(() => window.location.reload(), 600); }
      else showQuickToast(data.message || 'Could not record communication.', 'error');
    });
  });

  const followupForm = document.getElementById('followupForm');
  followupForm && followupForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const payload = { due_date: document.getElementById('fu_date').value, reason: document.getElementById('fu_reason').value };
    fetch(`/api/sponsors/${sponsorId}/followups`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(r => r.json()).then(data => {
      if (data.success) { showQuickToast(data.message, 'success'); setTimeout(() => window.location.reload(), 600); }
    });
  });

  const oppForm = document.getElementById('opportunityForm');
  oppForm && oppForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const payload = {
      package: document.getElementById('opp_package').value,
      benefits: document.getElementById('opp_benefits').value,
      amount_requested: document.getElementById('opp_requested').value,
      amount_committed: document.getElementById('opp_committed').value,
      amount_received: document.getElementById('opp_received').value,
      status: document.getElementById('opp_status').value,
      confirmed_date: document.getElementById('opp_confirmed_date').value,
    };
    fetch(`/api/sponsors/${sponsorId}/opportunity`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(r => r.json()).then(data => {
      if (data.success) { showQuickToast(data.message, 'success'); setTimeout(() => window.location.reload(), 600); }
    });
  });
}

/* =================================================================
   SPONSOR OUTREACH — MESSAGE GENERATOR
================================================================= */
function initSponsorOutreach() {
  const sponsorSelect = document.getElementById('outreachSponsorSelect');
  if (!sponsorSelect) return;
  const infoBox = document.getElementById('outreachSponsorInfo');
  const generateBtn = document.getElementById('generateMessageBtn');
  const preview = document.getElementById('messagePreview');
  const copyBtn = document.getElementById('copyMessageBtn');
  const saveDraftBtn = document.getElementById('saveDraftBtn');
  const recordSentBtn = document.getElementById('recordSentBtn');

  function currentSponsor() {
    const opt = sponsorSelect.options[sponsorSelect.selectedIndex];
    return opt ? opt.dataset : null;
  }

  function refreshInfo() {
    const s = currentSponsor();
    if (!s || !sponsorSelect.value) { infoBox.innerHTML = ''; return; }
    infoBox.innerHTML = `<b>${s.company}</b> · ${s.industry || 'N/A'} · Suitability ${s.score || 0}%<br>
      Contact: ${s.contact || 'Not set'} ${s.email ? '· ' + s.email : ''}`;
    document.getElementById('out_contact_person').value = s.contact || '';
  }
  sponsorSelect.addEventListener('change', refreshInfo);
  refreshInfo();

  generateBtn && generateBtn.addEventListener('click', function () {
    const sponsorId = sponsorSelect.value;
    if (!sponsorId) { showQuickToast('Select a sponsor first.', 'error'); return; }
    const payload = {
      contact_person: document.getElementById('out_contact_person').value,
      package: document.getElementById('out_package').value,
      amount: document.getElementById('out_amount').value,
      benefits: document.getElementById('out_benefits').value,
    };
    fetch(`/api/sponsors/${sponsorId}/generate-message`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(r => r.json()).then(data => {
      if (data.success) { preview.value = data.message_text; showQuickToast('Message generated.', 'success'); }
    });
  });

  copyBtn && copyBtn.addEventListener('click', function () {
    preview.select();
    navigator.clipboard && navigator.clipboard.writeText(preview.value).then(() => showQuickToast('Message copied to clipboard.', 'success'));
  });

  function recordOutreach(status) {
    const sponsorId = sponsorSelect.value;
    if (!sponsorId) { showQuickToast('Select a sponsor first.', 'error'); return; }
    if (!preview.value.trim()) { showQuickToast('Generate or write a message first.', 'error'); return; }
    const payload = {
      interaction_type: 'Outreach',
      communication_method: document.getElementById('out_method').value,
      subject: document.getElementById('out_subject').value || 'Sponsorship Outreach',
      message: preview.value,
      follow_up_date: document.getElementById('out_followup_date').value,
      next_action: 'Await sponsor response',
      new_status: status,
    };
    fetch(`/api/sponsors/${sponsorId}/interactions`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(r => r.json()).then(data => {
      if (data.success) {
        showQuickToast('Outreach recorded. Remember to actually send it through your chosen channel.', 'success');
        setTimeout(() => window.location.href = `/sponsors/${sponsorId}`, 900);
      }
    });
  }

  saveDraftBtn && saveDraftBtn.addEventListener('click', () => showQuickToast('Draft kept in the message box — copy it whenever you\'re ready to send.', 'success'));
  recordSentBtn && recordSentBtn.addEventListener('click', () => recordOutreach('Contacted'));
}

/* =================================================================
   FOLLOW-UP MANAGEMENT
================================================================= */
function initFollowupActions() {
  document.querySelectorAll('.complete-followup-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      const id = this.dataset.id;
      fetch(`/api/followups/${id}/complete`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            showQuickToast(data.message, 'success');
            const item = this.closest('.followup-item');
            item && item.remove();
          }
        });
    });
  });
}

/* =================================================================
   INCIDENT DETAIL — ADD UPDATE / ASSIGN / RESOLVE
================================================================= */
function initIncidentDetail(incidentId) {
  const form = document.getElementById('incidentUpdateForm');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const payload = {
      update_text: document.getElementById('upd_text').value,
      status_change: document.getElementById('upd_status').value,
      assigned_to: document.getElementById('upd_assigned').value,
      resolution: document.getElementById('upd_resolution').value,
    };
    fetch(`/api/incidents/${incidentId}/update`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(r => r.json()).then(data => {
      if (data.success) { showQuickToast(data.message, 'success'); setTimeout(() => window.location.reload(), 600); }
      else showQuickToast(data.message || 'Could not update incident.', 'error');
    });
  });
}

function initIncidentList() {
  const grid = document.getElementById('incidentCardsGrid');
  if (!grid) return;
  grid.addEventListener('click', function (e) {
    const btn = e.target.closest('.delete-incident-btn');
    if (!btn) return;
    const card = btn.closest('.incident-card');
    const id = card.dataset.id;
    if (!confirm('Delete this incident record?')) return;
    fetch(`/api/incidents/${id}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => { if (data.success) { card.remove(); showQuickToast(data.message, 'success'); } });
  });
}

/* =================================================================
   INCIDENT AGENT — LIVE PRIORITY SUGGESTION ON REPORT FORM
================================================================= */
const CATEGORY_PRIORITY_HINT = {
  Security: 'Critical', Technical: 'High', Venue: 'High', Speaker: 'Medium', Session: 'Medium',
  Sponsorship: 'Low', Registration: 'Medium', Attendance: 'Low', Operational: 'Medium',
  Participant: 'Medium', Other: 'Low',
};
function initIncidentReportForm() {
  const categorySelect = document.getElementById('reportCategory');
  const prioritySelect = document.getElementById('reportPriority');
  if (!categorySelect || !prioritySelect) return;
  categorySelect.addEventListener('change', function () {
    const hint = CATEGORY_PRIORITY_HINT[this.value];
    if (hint && !prioritySelect.dataset.touched) prioritySelect.value = hint;
  });
  prioritySelect.addEventListener('change', function () { this.dataset.touched = '1'; });
}

/* =================================================================
   ALERTS PAGE — READ / DISMISS
================================================================= */
function initAlertsPage() {
  const list = document.getElementById('alertsList');
  if (!list) return;
  list.addEventListener('click', function (e) {
    const card = e.target.closest('.alert-card');
    if (!card) return;
    const id = card.dataset.id;
    if (e.target.closest('.mark-read-btn')) {
      fetch(`/api/alerts/${id}/read`, { method: 'POST' }).then(() => card.classList.add('is-read'));
    }
    if (e.target.closest('.dismiss-alert-btn')) {
      fetch(`/api/alerts/${id}/dismiss`, { method: 'POST' })
        .then(r => r.json())
        .then(data => { if (data.success) { card.remove(); showQuickToast(data.message, 'success'); } });
    }
  });
  const markAllBtn = document.getElementById('markAllReadBtn');
  markAllBtn && markAllBtn.addEventListener('click', function () {
    fetch('/api/alerts/mark-all-read', { method: 'POST' })
      .then(r => r.json())
      .then(data => { if (data.success) { document.querySelectorAll('.alert-card').forEach(c => c.classList.add('is-read')); showQuickToast(data.message, 'success'); } });
  });
}

/* =================================================================
   PERFORMANCE / DASHBOARD CHARTS
================================================================= */
function initSponsorPerformanceCharts(data) {
  m3ChartDefaults();
  const mk = (id, type, chartData, opts) => {
    const el = document.getElementById(id);
    if (!el || typeof Chart === 'undefined') return;
    new Chart(el, { type, data: {
      labels: chartData.labels,
      datasets: [{ data: chartData.data, backgroundColor: M3_COLORS, borderRadius: type === 'bar' ? 6 : 0 }],
    }, options: Object.assign({ plugins: { legend: { display: type !== 'bar' } } }, opts || {}) });
  };
  mk('sponsorStatusChart', 'doughnut', data.status_distribution);
  mk('sponsorIndustryChart', 'bar', data.by_industry, { plugins: { legend: { display: false } } });
  mk('sponsorResponseChart', 'doughnut', data.response_rate);
  mk('sponsorAmountChart', 'bar', data.amount_by_status, { plugins: { legend: { display: false } } });
}

function initIncidentCharts(data) {
  m3ChartDefaults();
  const mk = (id, type, chartData) => {
    const el = document.getElementById(id);
    if (!el || typeof Chart === 'undefined') return;
    new Chart(el, { type, data: {
      labels: chartData.labels,
      datasets: [{ data: chartData.data, backgroundColor: M3_COLORS, borderRadius: type === 'bar' ? 6 : 0 }],
    }, options: { plugins: { legend: { display: type !== 'bar' } } } });
  };
  mk('incidentCategoryChart', 'doughnut', data.by_category);
  mk('incidentPriorityChart', 'bar', data.by_priority);
}
