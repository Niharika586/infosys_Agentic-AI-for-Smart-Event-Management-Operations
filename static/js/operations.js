/* =================================================================
   RegisterAI — Milestone 2 Operations Script (operations.js)
   Venue Management, Speaker Management, Session Management,
   Smart Scheduler and Session Analytics charts.
================================================================= */

const OPS_CHART_COLORS = ['#6c5ce7', '#00d4ff', '#a855f7', '#ff5da2', '#22c55e', '#f59e0b', '#ef4444', '#14b8a6'];

function opsChartDefaults() {
  if (typeof Chart === 'undefined') return;
  Chart.defaults.color = '#9aa3c0';
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.borderColor = 'rgba(255,255,255,0.08)';
}

/* =================================================================
   VENUE MANAGEMENT — CARDS, SEARCH, FILTERS, DETAILS, BOOKING
================================================================= */
function venueStatusBadge(status) {
  if (status === 'Occupied') return '<span class="badge badge-red">Occupied</span>';
  if (status === 'Reserved') return '<span class="badge badge-yellow">Reserved</span>';
  if (status === 'Maintenance') return '<span class="badge badge-gray">Maintenance</span>';
  return '<span class="badge badge-green">Available</span>';
}

function renderVenueCard(v) {
  const facilities = v.facilities_list || (v.facilities ? v.facilities.split(',').map(f => f.trim()) : []);
  const shown = facilities.slice(0, 5).map(f => `<span class="tag-pill">${f}</span>`).join('');
  const more = facilities.length > 5 ? `<span class="tag-pill">+${facilities.length - 5} more</span>` : '';
  return `
    <div class="glass venue-card" data-id="${v.id}" data-name="${v.name}" data-location="${v.location || ''}"
         data-capacity="${v.capacity}" data-roomtype="${v.room_type || ''}" data-facilities="${(facilities.join(','))}"
         data-status="${v.status}">
      <div class="venue-card-top">
        <h4>${v.name}</h4>
        ${venueStatusBadge(v.availability_status || v.status)}
      </div>
      <p class="venue-card-location"><i class="fa-solid fa-location-dot"></i> ${v.location || 'Location not set'}</p>
      <div class="venue-card-stats">
        <span><i class="fa-solid fa-users"></i> Capacity ${v.capacity}</span>
        <span><i class="fa-solid fa-door-open"></i> ${v.room_type || 'N/A'}</span>
      </div>
      <div class="tag-pills">${shown}${more}</div>
      <p class="venue-card-next"><i class="fa-solid fa-clock"></i> ${v.next_available || ''}</p>
      <div class="venue-card-actions">
        <button class="btn btn-outline btn-xs view-details-btn"><i class="fa-solid fa-eye"></i> View Details</button>
        <button class="btn btn-gradient btn-xs book-venue-btn"><i class="fa-solid fa-calendar-plus"></i> Book Venue</button>
        <button class="icon-action edit-venue-btn" title="Edit"><i class="fa-solid fa-pen"></i></button>
        <button class="icon-action delete-venue-btn" title="Delete"><i class="fa-solid fa-trash"></i></button>
      </div>
    </div>`;
}

function initVenueTable() {
  const grid = document.getElementById('venueCardsGrid');
  if (!grid) return;

  const modal = document.getElementById('venueModal');
  const form = document.getElementById('venueForm');
  const addBtn = document.getElementById('addVenueBtn');
  const closeBtn = document.getElementById('closeVenueModal');
  const modalTitle = document.getElementById('venueModalTitle');

  function openModal(title, venue) {
    modalTitle.textContent = title;
    document.getElementById('venueId').value = venue ? venue.id : '';
    document.getElementById('venueName').value = venue ? venue.name : '';
    document.getElementById('venueLocation').value = venue ? venue.location : '';
    document.getElementById('venueCapacity').value = venue ? venue.capacity : '';
    document.getElementById('venueRoomType').value = venue ? venue.room_type : '';
    document.getElementById('venueStatus').value = venue ? venue.status : 'Available';
    const facilities = venue ? (venue.facilities || '').split(',').map(f => f.trim()) : [];
    form.querySelectorAll('input[name="facilities"]').forEach(cb => { cb.checked = facilities.includes(cb.value); });
    modal.classList.add('show');
  }

  addBtn && addBtn.addEventListener('click', () => openModal('Add Venue', null));
  closeBtn && closeBtn.addEventListener('click', () => modal.classList.remove('show'));
  modal && modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });

  grid.addEventListener('click', function (e) {
    const card = e.target.closest('.venue-card');
    if (!card) return;
    const venueId = card.dataset.id;

    if (e.target.closest('.edit-venue-btn')) {
      openModal('Edit Venue', {
        id: card.dataset.id, name: card.dataset.name, location: card.dataset.location,
        capacity: card.dataset.capacity, room_type: card.dataset.roomtype,
        facilities: card.dataset.facilities, status: card.dataset.status,
      });
    }
    if (e.target.closest('.delete-venue-btn')) {
      if (!confirm('Delete this venue? Sessions assigned to it will be unassigned.')) return;
      fetch(`/api/venues/${venueId}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => { if (data.success) { card.remove(); showQuickToast(data.message, 'success'); } });
    }
    if (e.target.closest('.view-details-btn')) {
      openVenueDetails(venueId);
    }
    if (e.target.closest('.book-venue-btn')) {
      openBookVenue(venueId, card.dataset.name);
    }
  });

  form && form.addEventListener('submit', function (e) {
    e.preventDefault();
    const id = document.getElementById('venueId').value;
    const facilities = Array.from(form.querySelectorAll('input[name="facilities"]:checked')).map(cb => cb.value);
    const payload = {
      name: document.getElementById('venueName').value,
      location: document.getElementById('venueLocation').value,
      capacity: document.getElementById('venueCapacity').value,
      room_type: document.getElementById('venueRoomType').value,
      status: document.getElementById('venueStatus').value,
      facilities,
    };
    const url = id ? `/api/venues/${id}` : '/api/venues';
    fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showQuickToast(data.message, 'success');
          modal.classList.remove('show');
          setTimeout(() => window.location.reload(), 600);
        } else {
          showQuickToast(data.message || 'Could not save venue.', 'error');
        }
      });
  });
}

function openVenueDetails(venueId) {
  const modal = document.getElementById('venueDetailsModal');
  const body = document.getElementById('venueDetailsBody');
  const nameEl = document.getElementById('detailsVenueName');
  body.innerHTML = '<div class="muted center" style="padding:30px;">Loading...</div>';
  modal.classList.add('show');

  fetch(`/api/venues/${venueId}/details`)
    .then(r => r.json())
    .then(data => {
      if (!data.success) { body.innerHTML = `<div class="muted center" style="padding:30px;">${data.message}</div>`; return; }
      const v = data.venue;
      nameEl.textContent = v.name;
      const facilities = (v.facilities_list || []).map(f => `<span class="tag-pill">${f}</span>`).join('');

      function sessionRow(s) {
        return `<div class="slot-chip" style="min-width:auto;">
          <b>${s.session_date} · ${s.start_time}-${s.end_time}</b>
          <span>${s.title} ${s.speaker_name ? '· ' + s.speaker_name : ''} · ${s.status}</span>
        </div>`;
      }
      const upcoming = (data.upcoming_sessions || []).map(sessionRow).join('') || '<div class="slot-empty">No upcoming bookings.</div>';
      const past = (data.past_sessions || []).map(sessionRow).join('') || '<div class="slot-empty">No past bookings.</div>';

      body.innerHTML = `
        <div class="form-grid two" style="margin-bottom:14px;">
          <div><b>Location:</b> ${v.location || '-'}</div>
          <div><b>Capacity:</b> ${v.capacity}</div>
          <div><b>Room Type:</b> ${v.room_type || '-'}</div>
          <div><b>Status:</b> ${venueStatusBadge(v.live_status)}</div>
        </div>
        <div style="margin-bottom:14px;"><b>Facilities:</b><div class="tag-pills" style="margin-top:6px;">${facilities || '—'}</div></div>
        <p style="margin-bottom:16px;color:var(--text-muted);font-size:0.85rem;"><i class="fa-solid fa-clock"></i> ${data.next_available}</p>
        <h4 style="margin-bottom:8px;font-size:0.95rem;"><i class="fa-solid fa-calendar-check"></i> Upcoming Bookings</h4>
        <div class="venue-schedule-slots" style="margin-bottom:16px;">${upcoming}</div>
        <h4 style="margin-bottom:8px;font-size:0.95rem;"><i class="fa-solid fa-clock-rotate-left"></i> Past Bookings</h4>
        <div class="venue-schedule-slots" style="margin-bottom:16px;">${past}</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <a href="/sessions" class="btn btn-outline btn-sm"><i class="fa-solid fa-list-check"></i> View in Session Management</a>
          <a href="/scheduler" class="btn btn-outline btn-sm"><i class="fa-solid fa-calendar-days"></i> View Full Schedule</a>
        </div>`;
    });

  document.getElementById('closeVenueDetailsModal').onclick = () => modal.classList.remove('show');
  modal.onclick = (e) => { if (e.target === modal) modal.classList.remove('show'); };
}

function openBookVenue(venueId, venueName) {
  const modal = document.getElementById('bookVenueModal');
  document.getElementById('bookVenueId').value = venueId;
  document.getElementById('bookVenueName').textContent = venueName;
  document.getElementById('bookVenueError').style.display = 'none';
  document.getElementById('bookVenueForm').reset();
  document.getElementById('bookVenueId').value = venueId;
  modal.classList.add('show');

  document.getElementById('closeBookVenueModal').onclick = () => modal.classList.remove('show');
  modal.onclick = (e) => { if (e.target === modal) modal.classList.remove('show'); };

  const form = document.getElementById('bookVenueForm');
  form.onsubmit = function (e) {
    e.preventDefault();
    const errorBox = document.getElementById('bookVenueError');
    const payload = {
      title: document.getElementById('bookTitle').value,
      session_type: document.getElementById('bookSessionType').value,
      expected_attendees: document.getElementById('bookAttendees').value,
      session_date: document.getElementById('bookDate').value,
      start_time: document.getElementById('bookStart').value,
      end_time: document.getElementById('bookEnd').value,
    };
    fetch(`/api/venues/${venueId}/book`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(r => r.json().then(data => ({ status: r.status, data })))
      .then(({ data }) => {
        if (data.success) {
          showQuickToast(data.message, 'success');
          modal.classList.remove('show');
          setTimeout(() => window.location.reload(), 600);
        } else {
          document.getElementById('bookVenueErrorText').textContent = data.message || 'Could not book venue.';
          errorBox.style.display = 'flex';
        }
      });
  };
}

function initVenueSearch() {
  const grid = document.getElementById('venueCardsGrid');
  if (!grid) return;
  const searchInput = document.getElementById('venueSearchInput');
  const locationFilter = document.getElementById('locationFilter');
  const roomTypeFilter = document.getElementById('roomTypeFilter');
  const sortSelect = document.getElementById('sortSelect');
  const dateFilter = document.getElementById('dateFilter');
  const startTimeFilter = document.getElementById('startTimeFilter');
  const endTimeFilter = document.getElementById('endTimeFilter');
  const attendeesFilter = document.getElementById('attendeesFilter');
  const resultCount = document.getElementById('venueResultCount');
  const emptyState = document.getElementById('venueEmptyState');

  let capacityValue = '0';
  let availabilityValue = 'All';

  function setupChips(containerId, onSelect) {
    const container = document.getElementById(containerId);
    container.querySelectorAll('.filter-chip').forEach(chip => {
      chip.addEventListener('click', function () {
        container.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        onSelect(this.dataset.value);
        runSearch();
      });
    });
  }
  setupChips('capacityChips', v => capacityValue = v);
  setupChips('availabilityChips', v => availabilityValue = v);

  let debounceTimer;
  function debouncedSearch() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runSearch, 300);
  }

  function runSearch() {
    const facilities = Array.from(document.querySelectorAll('input[name="facilityFilter"]:checked')).map(cb => cb.value);
    const params = new URLSearchParams({
      q: searchInput.value || '',
      capacity_min: capacityValue,
      availability: availabilityValue,
      location: locationFilter.value || '',
      room_type: roomTypeFilter.value || '',
      sort: sortSelect.value || 'name',
      date: dateFilter.value || '',
      start_time: startTimeFilter.value || '',
      end_time: endTimeFilter.value || '',
      attendees: attendeesFilter.value || '',
      facilities: facilities.join(','),
    });
    fetch(`/api/venues/search?${params.toString()}`)
      .then(r => r.json())
      .then(venues => {
        resultCount.textContent = `${venues.length} venue(s) found`;
        if (venues.length === 0) {
          grid.innerHTML = '';
          emptyState.style.display = 'block';
        } else {
          emptyState.style.display = 'none';
          grid.innerHTML = venues.map(renderVenueCard).join('');
        }
      });
  }

  searchInput.addEventListener('input', debouncedSearch);
  [locationFilter, roomTypeFilter, sortSelect, dateFilter, startTimeFilter, endTimeFilter, attendeesFilter].forEach(el => {
    el.addEventListener('input', debouncedSearch);
    el.addEventListener('change', debouncedSearch);
  });
  document.querySelectorAll('input[name="facilityFilter"]').forEach(cb => cb.addEventListener('change', debouncedSearch));

  document.getElementById('resetFiltersBtn').addEventListener('click', function () {
    searchInput.value = '';
    locationFilter.value = '';
    roomTypeFilter.value = '';
    sortSelect.value = 'name';
    dateFilter.value = '';
    startTimeFilter.value = '';
    endTimeFilter.value = '';
    attendeesFilter.value = '';
    document.querySelectorAll('input[name="facilityFilter"]').forEach(cb => cb.checked = false);
    document.querySelectorAll('#capacityChips .filter-chip').forEach(c => c.classList.remove('active'));
    document.querySelector('#capacityChips .filter-chip[data-value="0"]').classList.add('active');
    capacityValue = '0';
    document.querySelectorAll('#availabilityChips .filter-chip').forEach(c => c.classList.remove('active'));
    document.querySelector('#availabilityChips .filter-chip[data-value="All"]').classList.add('active');
    availabilityValue = 'All';
    runSearch();
  });
}

/* =================================================================
   SPEAKER MANAGEMENT TABLE
================================================================= */
function initSpeakerTable() {
  const tbody = document.getElementById('speakerBody');
  if (!tbody) return;

  const modal = document.getElementById('speakerModal');
  const form = document.getElementById('speakerForm');
  const addBtn = document.getElementById('addSpeakerBtn');
  const closeBtn = document.getElementById('closeSpeakerModal');
  const modalTitle = document.getElementById('speakerModalTitle');

  function openModal(title, sp) {
    modalTitle.textContent = title;
    document.getElementById('speakerId').value = sp ? sp.id : '';
    document.getElementById('speakerName').value = sp ? sp.name : '';
    document.getElementById('speakerEmail').value = sp ? sp.email : '';
    document.getElementById('speakerPhone').value = sp ? sp.phone : '';
    document.getElementById('speakerOrg').value = sp ? sp.organization : '';
    document.getElementById('speakerDesignation').value = sp ? sp.designation : '';
    document.getElementById('speakerExpertise').value = sp ? sp.expertise : '';
    document.getElementById('speakerBio').value = sp ? sp.bio : '';
    document.getElementById('speakerSessionType').value = sp ? sp.preferred_session_type : '';
    document.getElementById('speakerDates').value = sp ? sp.available_dates : '';
    document.getElementById('speakerSlots').value = sp ? sp.available_slots : '';
    modal.classList.add('show');
  }

  addBtn && addBtn.addEventListener('click', () => openModal('Add Speaker', null));
  closeBtn && closeBtn.addEventListener('click', () => modal.classList.remove('show'));
  modal && modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });

  tbody.addEventListener('click', function (e) {
    const editBtn = e.target.closest('.edit-btn');
    if (editBtn) {
      const row = editBtn.closest('tr');
      openModal('Edit Speaker', {
        id: row.dataset.id, name: row.dataset.name, email: row.dataset.email, phone: row.dataset.phone,
        organization: row.dataset.org, designation: row.dataset.designation, expertise: row.dataset.expertise,
        bio: row.dataset.bio, preferred_session_type: row.dataset.sessiontype,
        available_dates: row.dataset.dates, available_slots: row.dataset.slots,
      });
    }
    const delBtn = e.target.closest('.delete-btn');
    if (delBtn) {
      const row = delBtn.closest('tr');
      if (!confirm('Delete this speaker? Sessions assigned to them will be unassigned.')) return;
      fetch(`/api/speakers/${row.dataset.id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => { if (data.success) { row.remove(); showQuickToast(data.message, 'success'); } });
    }
  });

  form && form.addEventListener('submit', function (e) {
    e.preventDefault();
    const id = document.getElementById('speakerId').value;
    const payload = {
      name: document.getElementById('speakerName').value,
      email: document.getElementById('speakerEmail').value,
      phone: document.getElementById('speakerPhone').value,
      organization: document.getElementById('speakerOrg').value,
      designation: document.getElementById('speakerDesignation').value,
      expertise: document.getElementById('speakerExpertise').value,
      bio: document.getElementById('speakerBio').value,
      preferred_session_type: document.getElementById('speakerSessionType').value,
      available_dates: document.getElementById('speakerDates').value,
      available_slots: document.getElementById('speakerSlots').value,
    };
    const url = id ? `/api/speakers/${id}` : '/api/speakers';
    fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showQuickToast(data.message, 'success');
          modal.classList.remove('show');
          setTimeout(() => window.location.reload(), 600);
        } else {
          showQuickToast(data.message || 'Could not save speaker.', 'error');
        }
      });
  });

  // Search filter
  const search = document.getElementById('speakerSearch');
  if (search) {
    search.addEventListener('input', function () {
      const term = this.value.toLowerCase();
      tbody.querySelectorAll('tr[data-id]').forEach(row => {
        const hay = (row.dataset.name + ' ' + row.dataset.expertise + ' ' + row.dataset.org).toLowerCase();
        row.style.display = hay.includes(term) ? '' : 'none';
      });
    });
  }
}

/* =================================================================
   SESSION MANAGEMENT TABLE
================================================================= */
function initSessionTable() {
  const tbody = document.getElementById('sessionBody');
  if (!tbody) return;

  const modal = document.getElementById('sessionModal');
  const form = document.getElementById('sessionForm');
  const addBtn = document.getElementById('addSessionBtn');
  const closeBtn = document.getElementById('closeSessionModal');
  const modalTitle = document.getElementById('sessionModalTitle');
  const errorBox = document.getElementById('sessionFormError');

  function openModal(title, s) {
    errorBox.style.display = 'none';
    modalTitle.textContent = title;
    document.getElementById('sessionId').value = s ? s.id : '';
    document.getElementById('sessionTitle').value = s ? s.title : '';
    document.getElementById('sessionDescription').value = s ? s.description : '';
    document.getElementById('sessionType').value = s ? s.session_type : '';
    document.getElementById('sessionDate').value = s ? s.session_date : '';
    document.getElementById('sessionStart').value = s ? s.start_time : '';
    document.getElementById('sessionEnd').value = s ? s.end_time : '';
    document.getElementById('sessionAttendees').value = s ? s.expected_attendees : '';
    document.getElementById('sessionVenue').value = s ? (s.venue_id || '') : '';
    document.getElementById('sessionSpeaker').value = s ? (s.speaker_id || '') : '';
    document.getElementById('sessionStatus').value = s ? s.status : 'Scheduled';
    const facilities = s ? (s.required_facilities || '').split(',').map(f => f.trim()) : [];
    form.querySelectorAll('input[name="required_facilities"]').forEach(cb => { cb.checked = facilities.includes(cb.value); });
    modal.classList.add('show');
  }

  addBtn && addBtn.addEventListener('click', () => openModal('Create Session', null));
  closeBtn && closeBtn.addEventListener('click', () => modal.classList.remove('show'));
  modal && modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });

  tbody.addEventListener('click', function (e) {
    const editBtn = e.target.closest('.edit-btn');
    if (editBtn) {
      const row = editBtn.closest('tr');
      openModal('Edit Session', {
        id: row.dataset.id, title: row.dataset.title, description: row.dataset.description,
        session_type: row.dataset.type, session_date: row.dataset.date, start_time: row.dataset.start,
        end_time: row.dataset.end, expected_attendees: row.dataset.attendees, venue_id: row.dataset.venueid,
        speaker_id: row.dataset.speakerid, status: row.dataset.status, required_facilities: row.dataset.facilities,
      });
    }
    const delBtn = e.target.closest('.delete-btn');
    if (delBtn) {
      const row = delBtn.closest('tr');
      if (!confirm('Remove this session? This cannot be undone.')) return;
      fetch(`/api/sessions/${row.dataset.id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => { if (data.success) { row.remove(); showQuickToast(data.message, 'success'); } });
    }
  });

  form && form.addEventListener('submit', function (e) {
    e.preventDefault();
    const id = document.getElementById('sessionId').value;
    const facilities = Array.from(form.querySelectorAll('input[name="required_facilities"]:checked')).map(cb => cb.value);
    const payload = {
      title: document.getElementById('sessionTitle').value,
      description: document.getElementById('sessionDescription').value,
      session_type: document.getElementById('sessionType').value,
      session_date: document.getElementById('sessionDate').value,
      start_time: document.getElementById('sessionStart').value,
      end_time: document.getElementById('sessionEnd').value,
      expected_attendees: document.getElementById('sessionAttendees').value,
      venue_id: document.getElementById('sessionVenue').value,
      speaker_id: document.getElementById('sessionSpeaker').value,
      status: document.getElementById('sessionStatus').value,
      required_facilities: facilities,
    };
    const url = id ? `/api/sessions/${id}` : '/api/sessions';
    fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(r => r.json().then(data => ({ status: r.status, data })))
      .then(({ status, data }) => {
        if (data.success) {
          showQuickToast(data.message, 'success');
          modal.classList.remove('show');
          setTimeout(() => window.location.reload(), 600);
        } else {
          document.getElementById('sessionFormErrorText').textContent = data.message || 'Could not save session.';
          errorBox.style.display = 'flex';
        }
      });
  });

  // Prefill from Venue/Speaker Agent "confirm allocation" redirect
  const params = new URLSearchParams(window.location.search);
  if (params.get('prefill') === '1') {
    openModal('Create Session', {
      id: '', title: params.get('title') || '', description: '',
      session_type: params.get('session_type') || '', session_date: params.get('session_date') || '',
      start_time: params.get('start_time') || '', end_time: params.get('end_time') || '',
      expected_attendees: params.get('attendees') || '', venue_id: params.get('venue_id') || '',
      speaker_id: params.get('speaker_id') || '', status: 'Scheduled', required_facilities: params.get('facilities') || '',
    });
  }
}

/* =================================================================
   SCHEDULER — date navigation
================================================================= */
function initScheduler() {
  const dateInput = document.getElementById('schedulerDate');
  if (!dateInput) return;
  dateInput.addEventListener('change', function () {
    const url = new URL(window.location.href);
    url.searchParams.set('date', this.value);
    window.location.href = url.toString();
  });
}

/* =================================================================
   VENUE / SPEAKER AGENT — checkbox chip toggle styling
================================================================= */
function initAgentForm() {
  document.querySelectorAll('.checkbox-chip input[type="checkbox"]').forEach(cb => {
    const chip = cb.closest('.checkbox-chip');
    const sync = () => chip.style.borderColor = cb.checked ? 'var(--primary)' : '';
    cb.addEventListener('change', sync);
    sync();
  });
}

/* =================================================================
   OPERATIONS ANALYTICS CHARTS
================================================================= */
function initOperationsCharts(data) {
  opsChartDefaults();

  if (document.getElementById('sessionsByTypeChart')) {
    new Chart(document.getElementById('sessionsByTypeChart'), {
      type: 'doughnut',
      data: { labels: data.sessions_by_type.labels, datasets: [{ data: data.sessions_by_type.data, backgroundColor: OPS_CHART_COLORS }] },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  }

  if (document.getElementById('sessionsByDayChart')) {
    new Chart(document.getElementById('sessionsByDayChart'), {
      type: 'bar',
      data: { labels: data.sessions_by_day.labels, datasets: [{ label: 'Sessions', data: data.sessions_by_day.data, backgroundColor: '#6c5ce7', borderRadius: 8, maxBarThickness: 40 }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
    });
  }

  if (document.getElementById('venueUtilChart')) {
    new Chart(document.getElementById('venueUtilChart'), {
      type: 'bar',
      data: { labels: data.venue_utilization.labels, datasets: [{ label: 'Utilization %', data: data.venue_utilization.data, backgroundColor: '#00d4ff', borderRadius: 8, maxBarThickness: 36 }] },
      options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, max: 100 } } }
    });
  }

  if (document.getElementById('speakerAssignChart')) {
    new Chart(document.getElementById('speakerAssignChart'), {
      type: 'bar',
      data: { labels: data.speaker_assignments.labels, datasets: [{ label: 'Sessions Assigned', data: data.speaker_assignments.data, backgroundColor: '#a855f7', borderRadius: 8, maxBarThickness: 36 }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
    });
  }

  if (document.getElementById('conflictStatsChart')) {
    new Chart(document.getElementById('conflictStatsChart'), {
      type: 'pie',
      data: { labels: data.conflict_stats.labels, datasets: [{ data: data.conflict_stats.data, backgroundColor: ['#ef4444', '#f59e0b'] }] },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  }
}
