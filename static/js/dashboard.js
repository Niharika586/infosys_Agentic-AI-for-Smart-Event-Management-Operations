/* =================================================================
   RegisterAI — Dashboard Script (dashboard.js)
================================================================= */

const CHART_COLORS = ['#6c5ce7', '#00d4ff', '#a855f7', '#ff5da2', '#22c55e', '#f59e0b', '#ef4444', '#14b8a6'];

function chartDefaults() {
  if (typeof Chart === 'undefined') return;
  Chart.defaults.color = '#9aa3c0';
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.borderColor = 'rgba(255,255,255,0.08)';
}

/* ---------------- Dashboard Page Charts ---------------- */
function initDashboardCharts(data) {
  chartDefaults();

  new Chart(document.getElementById('barChart'), {
    type: 'bar',
    data: {
      labels: data.departments.labels,
      datasets: [{
        label: 'Registrations',
        data: data.departments.data,
        backgroundColor: '#6c5ce7',
        borderRadius: 8,
        maxBarThickness: 42,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
    }
  });

  new Chart(document.getElementById('pieChart'), {
    type: 'pie',
    data: {
      labels: data.gender.labels,
      datasets: [{ data: data.gender.data, backgroundColor: CHART_COLORS }]
    },
    options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
  });

  new Chart(document.getElementById('lineChart'), {
    type: 'line',
    data: {
      labels: data.trend.labels,
      datasets: [{
        label: 'Registrations',
        data: data.trend.data,
        borderColor: '#00d4ff',
        backgroundColor: 'rgba(0,212,255,0.15)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: '#00d4ff',
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
    }
  });
}

/* ---------------- Analytics Page Charts ---------------- */
function initAnalyticsCharts(data) {
  chartDefaults();

  new Chart(document.getElementById('categoryPieChart'), {
    type: 'doughnut',
    data: {
      labels: data.categories.labels,
      datasets: [{ data: data.categories.data, backgroundColor: CHART_COLORS }]
    },
    options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
  });

  new Chart(document.getElementById('categoryBarChart'), {
    type: 'bar',
    data: {
      labels: data.categories.labels,
      datasets: [{ label: 'Registrations', data: data.categories.data, backgroundColor: CHART_COLORS, borderRadius: 8, maxBarThickness: 36 }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
    }
  });

  new Chart(document.getElementById('citiesChart'), {
    type: 'bar',
    data: {
      labels: data.cities.labels,
      datasets: [{ label: 'Attendees', data: data.cities.data, backgroundColor: '#00d4ff', borderRadius: 8, maxBarThickness: 36 }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } } }
    }
  });

  new Chart(document.getElementById('trendChart2'), {
    type: 'line',
    data: {
      labels: data.trend.labels,
      datasets: [{
        label: 'Registrations', data: data.trend.data, borderColor: '#a855f7',
        backgroundColor: 'rgba(168,85,247,0.15)', fill: true, tension: 0.4, pointBackgroundColor: '#a855f7',
      }]
    },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
  });
}

/* =================================================================
   Attendee Management Table — search, filter, sort, edit, delete
================================================================= */
function initAttendeeTable() {
  const search = document.getElementById('searchInput');
  const filterCategory = document.getElementById('filterCategory');
  const filterDept = document.getElementById('filterDept');
  const sortBy = document.getElementById('sortBy');
  const tbody = document.getElementById('attendeeBody');
  if (!tbody) return;

  function applyFilters() {
    const term = (search.value || '').toLowerCase();
    const cat = filterCategory.value;
    const dept = filterDept.value;
    const rows = Array.from(tbody.querySelectorAll('tr[data-id]'));

    rows.forEach(row => {
      const matchesSearch = !term ||
        row.dataset.name.includes(term) || row.dataset.email.includes(term) ||
        row.dataset.college.includes(term) || row.dataset.city.includes(term);
      const matchesCategory = !cat || row.dataset.category === cat;
      const matchesDept = !dept || row.dataset.dept === dept;
      row.style.display = (matchesSearch && matchesCategory && matchesDept) ? '' : 'none';
    });

    sortRows();
  }

  function sortRows() {
    const rows = Array.from(tbody.querySelectorAll('tr[data-id]'));
    const mode = sortBy.value;

    rows.sort((a, b) => {
      if (mode === 'name_asc') return a.dataset.name.localeCompare(b.dataset.name);
      if (mode === 'name_desc') return b.dataset.name.localeCompare(a.dataset.name);
      if (mode === 'created_at_asc') return a.dataset.created.localeCompare(b.dataset.created);
      return b.dataset.created.localeCompare(a.dataset.created); // created_at_desc default
    });

    rows.forEach(r => tbody.appendChild(r));
  }

  [search, filterCategory, filterDept].forEach(el => el && el.addEventListener('input', applyFilters));
  sortBy && sortBy.addEventListener('change', applyFilters);

  // Delete
  tbody.addEventListener('click', function (e) {
    const delBtn = e.target.closest('.delete-btn');
    if (delBtn) {
      const row = delBtn.closest('tr');
      const id = row.dataset.id;
      if (!confirm('Are you sure you want to delete this attendee? This action cannot be undone.')) return;

      fetch(`/api/attendees/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
          if (data.success) { row.remove(); showQuickToast(data.message, 'success'); }
        });
    }

    const editBtn = e.target.closest('.edit-btn');
    if (editBtn) openEditModal(editBtn.closest('tr'));
  });

  // Edit modal
  const modal = document.getElementById('editModal');
  const closeModal = document.getElementById('closeModal');
  const editForm = document.getElementById('editForm');

  function openEditModal(row) {
    document.getElementById('editId').value = row.dataset.id;
    document.getElementById('editName').value = row.children[2].textContent.trim();
    document.getElementById('editEmail').value = row.children[3].textContent.trim();
    document.getElementById('editPhone').value = row.children[4].textContent.trim();
    document.getElementById('editCollege').value = row.children[5].textContent.trim();
    document.getElementById('editDepartment').value = row.children[6].textContent.trim();
    document.getElementById('editCity').value = row.dataset.city;
    modal.classList.add('show');
  }

  closeModal && closeModal.addEventListener('click', () => modal.classList.remove('show'));
  modal && modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });

  editForm && editForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const id = document.getElementById('editId').value;
    const payload = {
      name: document.getElementById('editName').value,
      email: document.getElementById('editEmail').value,
      phone: document.getElementById('editPhone').value,
      college: document.getElementById('editCollege').value,
      department: document.getElementById('editDepartment').value,
      city: document.getElementById('editCity').value,
    };

    fetch(`/api/attendees/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          modal.classList.remove('show');
          showQuickToast(data.message, 'success');
          setTimeout(() => window.location.reload(), 700);
        } else {
          showQuickToast(data.message || 'Update failed.', 'error');
        }
      });
  });
}

function showQuickToast(message, type) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation'}"></i><span>${message}</span><button class="toast-close" onclick="this.parentElement.remove()">&times;</button>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4500);
}

/* =================================================================
   QR Check-in Page
================================================================= */
let __html5QrScanner = null;

function initCheckin() {
  const btn = document.getElementById('checkinBtn');
  const input = document.getElementById('checkinCode');
  const resultBox = document.getElementById('checkinResult');
  const qrSelect = document.getElementById('qrUserSelect');
  const qrDisplay = document.getElementById('qrDisplay');
  const scanBtn = document.getElementById('startScanBtn');
  const stopBtn = document.getElementById('stopScanBtn');

  if (btn) {
    btn.addEventListener('click', () => doCheckin(input.value.trim()));
    input.addEventListener('keypress', (e) => { if (e.key === 'Enter') doCheckin(input.value.trim()); });
  }

  function renderResult(data) {
    if (!data.success) {
      resultBox.innerHTML = `<p class="fail"><i class="fa-solid fa-circle-xmark"></i> ${data.message}</p>`;
      return;
    }
    const u = data.user || {};
    resultBox.innerHTML = `
      <p class="ok"><i class="fa-solid fa-circle-check"></i> ${data.message}</p>
      <div class="checkin-detail-card">
        <div><span>Name</span><b>${u.name || '-'}</b></div>
        <div><span>Registration ID</span><b>${u.registration_id || '-'}</b></div>
        <div><span>Participant Category</span><b>${u.participant_category || '-'}</b></div>
        <div><span>Check-in Time</span><b>${u.check_in_time || '-'}</b></div>
        <div><span>Status</span><b class="ok">Present</b></div>
      </div>`;
    input.value = '';
    document.getElementById('checkedInCount').textContent = data.checked_in_count;
    document.getElementById('totalCount').textContent = data.total;
    const pct = data.total ? ((data.checked_in_count / data.total) * 100).toFixed(1) : 0;
    document.getElementById('checkinProgress').style.width = pct + '%';
    document.getElementById('checkinPercent').textContent = pct + '%';
  }

  function doCheckin(code) {
    if (!code) return;
    fetch('/api/checkin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    })
      .then(r => r.json())
      .then(renderResult)
      .catch(() => {
        resultBox.innerHTML = `<p class="fail"><i class="fa-solid fa-circle-xmark"></i> Something went wrong. Please try again.</p>`;
      });
  }

  if (qrSelect) {
    qrSelect.addEventListener('change', function () {
      if (!this.value) { qrDisplay.innerHTML = ''; return; }
      qrDisplay.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="font-size:2rem;color:var(--accent);"></i>';
      fetch(`/api/qrcode/${this.value}`)
        .then(r => r.json())
        .then(data => {
          if (data.qr_base64) {
            qrDisplay.innerHTML = `<img src="${data.qr_base64}" alt="QR Code" width="200" height="200">
              <a href="/api/qrcode/${qrSelect.value}/download" class="btn btn-outline btn-sm" style="margin-left:12px;"><i class="fa-solid fa-download"></i> Download</a>`;
          } else {
            qrDisplay.innerHTML = '<p class="muted">QR generation unavailable.</p>';
          }
        });
    });
  }

  /* ---- Live camera QR scanning (html5-qrcode) ---- */
  if (scanBtn) {
    scanBtn.addEventListener('click', function () {
      if (typeof Html5Qrcode === 'undefined') {
        resultBox.innerHTML = `<p class="fail"><i class="fa-solid fa-circle-xmark"></i> Camera scanner library failed to load.</p>`;
        return;
      }
      scanBtn.style.display = 'none';
      stopBtn.style.display = '';
      __html5QrScanner = new Html5Qrcode('qrReader');
      __html5QrScanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 220, height: 220 } },
        (decodedText) => {
          doCheckin(decodedText);
        },
        () => {}
      ).catch(() => {
        resultBox.innerHTML = `<p class="fail"><i class="fa-solid fa-circle-xmark"></i> Unable to access camera. Check browser permissions.</p>`;
        scanBtn.style.display = '';
        stopBtn.style.display = 'none';
      });
    });
  }

  if (stopBtn) {
    stopBtn.addEventListener('click', function () {
      if (__html5QrScanner) {
        __html5QrScanner.stop().then(() => __html5QrScanner.clear()).catch(() => {});
      }
      stopBtn.style.display = 'none';
      scanBtn.style.display = '';
    });
  }
}

/* =================================================================
   Mini Calendar Widget
================================================================= */
function renderMiniCalendar() {
  const el = document.getElementById('miniCalendar');
  if (!el) return;

  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const today = now.getDate();

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const dayNames = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  let html = dayNames.map(d => `<div class="cal-day-name">${d}</div>`).join('');

  for (let i = 0; i < firstDay; i++) html += `<div class="cal-cell"></div>`;
  for (let d = 1; d <= daysInMonth; d++) {
    html += `<div class="cal-cell ${d === today ? 'cal-today' : ''}">${d}</div>`;
  }

  el.innerHTML = html;
}
