/**
 * RideNow - Main JavaScript
 * Theme toggle, sidebar, map, fare estimation, booking flow
 */

// ── Theme Manager ──────────────────────────────────────────────────────────────
const ThemeManager = {
    KEY: 'ridenow-theme',
  
    init() {
      const saved = localStorage.getItem(this.KEY) || 'light';
      this.apply(saved);
      document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
        btn.addEventListener('click', () => this.toggle());
      });
    },
  
    apply(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem(this.KEY, theme);
      document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
        btn.innerHTML = theme === 'dark'
          ? '<i class="bi bi-sun-fill"></i>'
          : '<i class="bi bi-moon-fill"></i>';
      });
    },
  
    toggle() {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      this.apply(current === 'dark' ? 'light' : 'dark');
    }
  };
  
  // ── Sidebar Manager ────────────────────────────────────────────────────────────
  const Sidebar = {
    init() {
      const toggle = document.querySelector('.sidebar-toggle');
      const sidebar = document.querySelector('.sidebar');
      const overlay = document.querySelector('.sidebar-overlay');
      if (!toggle || !sidebar) return;
  
      toggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        overlay?.classList.toggle('show');
      });
  
      overlay?.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
      });
    }
  };
  
  // ── Alert Auto-dismiss ─────────────────────────────────────────────────────────
  function initAlerts() {
    document.querySelectorAll('.alert-dismissible').forEach(alert => {
      setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        setTimeout(() => alert.remove(), 300);
      }, 4000);
    });
  }
  
  // ── Vehicle Type Selector ──────────────────────────────────────────────────────
  function initVehicleCards() {
    document.querySelectorAll('.vehicle-card').forEach(card => {
      card.addEventListener('click', function () {
        document.querySelectorAll('.vehicle-card').forEach(c => c.classList.remove('selected'));
        this.classList.add('selected');
        const type = this.dataset.type;
        const fare = this.dataset.fare;
        const distEl = document.getElementById('distance_km');
        const dist = distEl ? distEl.value : 0;
  
        // Update hidden inputs
        document.getElementById('vehicle_type_input').value = type;
        document.getElementById('estimated_fare_input').value = fare;
  
        // Update fare display
        const fareDisplay = document.getElementById('selected-fare');
        if (fareDisplay) fareDisplay.textContent = `₹${parseFloat(fare).toFixed(2)}`;
  
        document.getElementById('book-btn')?.removeAttribute('disabled');
      });
    });
  }
  
  // ── Fare Estimation ────────────────────────────────────────────────────────────
  const FareEstimator = {
    async estimate(pickupLat, pickupLng, dropLat, dropLng) {
      try {
        const res = await fetch('/api/estimate-fare', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pickup_lat: pickupLat, pickup_lng: pickupLng,
            drop_lat: dropLat, drop_lng: dropLng
          })
        });
        return await res.json();
      } catch (e) {
        console.error('Fare estimate error:', e);
        return null;
      }
    },
  
    updateCards(estimates) {
      if (!estimates) return;
      Object.entries(estimates).forEach(([type, data]) => {
        const card = document.querySelector(`.vehicle-card[data-type="${type}"]`);
        if (!card) return;
        card.dataset.fare = data.fare;
        card.querySelector('.vehicle-price').textContent = `₹${data.fare}`;
        card.querySelector('.vehicle-eta').textContent = data.eta;
      });
  
      const distDisplay = document.getElementById('distance-display');
      const firstKey = Object.keys(estimates)[0];
      if (distDisplay && firstKey) {
        distDisplay.textContent = `${estimates[firstKey].distance} km`;
        const distInput = document.getElementById('distance_km');
        if (distInput) distInput.value = estimates[firstKey].distance;
      }
    }
  };
  
  // ── Promo Code ────────────────────────────────────────────────────────────────
  async function applyPromo() {
    const code = document.getElementById('promo-input')?.value.trim();
    const fare = parseFloat(document.getElementById('estimated_fare_input')?.value || 0);
    if (!code) return;
  
    const btn = document.getElementById('promo-btn');
    if (btn) btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
  
    try {
      const res = await fetch('/api/validate-promo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, fare })
      });
      const data = await res.json();
  
      const msgEl = document.getElementById('promo-message');
      if (data.success) {
        msgEl.className = 'mt-2 text-success small fw-bold';
        msgEl.textContent = data.message;
        document.getElementById('promo_code_input').value = code;
        document.getElementById('estimated_fare_input').value = data.final_fare;
        document.getElementById('selected-fare').textContent = `₹${data.final_fare}`;
        const discountEl = document.getElementById('discount-display');
        if (discountEl) discountEl.textContent = `-₹${data.discount}`;
      } else {
        msgEl.className = 'mt-2 text-danger small fw-bold';
        msgEl.textContent = data.message;
      }
    } catch (e) {
      console.error(e);
    } finally {
      if (btn) btn.innerHTML = 'Apply';
    }
  }
  
  // ── Ride Status Polling ───────────────────────────────────────────────────────
  function initRidePolling(rideId) {
    if (!rideId) return;
  
    const poll = async () => {
      try {
        const res = await fetch(`/api/ride-status/${rideId}`);
        const data = await res.json();
        updateRideStatus(data);
        if (!['completed', 'cancelled'].includes(data.status)) {
          setTimeout(poll, 5000);
        }
      } catch (e) {
        setTimeout(poll, 8000);
      }
    };
  
    setTimeout(poll, 3000);
  }
  
  function updateRideStatus(data) {
    const statusBadge = document.getElementById('status-badge');
    const statusText = document.getElementById('status-text');
    const statusLabels = {
      pending: 'Searching for driver...',
      accepted: 'Driver is on the way!',
      in_progress: 'Ride in progress',
      completed: 'Ride completed!',
      cancelled: 'Ride cancelled',
    };
  
    if (statusBadge) {
      statusBadge.className = `badge badge-${data.status}`;
      statusBadge.textContent = data.status.replace('_', ' ').toUpperCase();
    }
    if (statusText) statusText.textContent = statusLabels[data.status] || data.status;
  
    // Update step states
    const steps = ['pending', 'accepted', 'in_progress', 'completed'];
    const currentIdx = steps.indexOf(data.status);
    steps.forEach((step, idx) => {
      const el = document.querySelector(`.status-step[data-step="${step}"]`);
      if (!el) return;
      el.classList.remove('done', 'active');
      if (idx < currentIdx) el.classList.add('done');
      else if (idx === currentIdx) el.classList.add('active');
    });
  
    // Update driver info
    if (data.driver) {
      const driverCard = document.getElementById('driver-info');
      if (driverCard) {
        driverCard.style.display = 'block';
        document.getElementById('driver-name').textContent = data.driver.name;
        document.getElementById('driver-vehicle').textContent = data.driver.vehicle;
        document.getElementById('driver-plate').textContent = data.driver.vehicle_number;
        document.getElementById('driver-rating').textContent = '⭐ ' + data.driver.rating;
      }
    }
  }
  
  // ── Map (Google Maps or demo) ──────────────────────────────────────────────────
  let map, pickupMarker, dropMarker, directionsRenderer;
  
  function initMap() {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;
  
    // Check if Google Maps is available
    if (typeof google === 'undefined') {
      // Demo map with a nice gradient placeholder
      mapEl.innerHTML = `
        <div class="map-placeholder">
          <i class="bi bi-map" style="font-size:3rem;color:#6c63ff;opacity:0.5"></i>
          <div style="font-weight:600;font-size:1rem">Interactive Map</div>
          <div style="font-size:0.85rem;color:#888">Add your Google Maps API key to enable live maps</div>
          <div style="margin-top:16px;display:flex;gap:20px">
            <div style="text-align:center">
              <div style="font-size:2rem">📍</div>
              <div style="font-size:0.78rem;color:#6c63ff;font-weight:600">Pickup</div>
              <div id="map-pickup" style="font-size:0.75rem;color:#888;max-width:120px"></div>
            </div>
            <div style="font-size:2rem;line-height:3.5rem;color:#6c63ff">→</div>
            <div style="text-align:center">
              <div style="font-size:2rem">🏁</div>
              <div style="font-size:0.78rem;color:#ff6584;font-weight:600">Drop</div>
              <div id="map-drop" style="font-size:0.75rem;color:#888;max-width:120px"></div>
            </div>
          </div>
        </div>`;
      return;
    }
  
    map = new google.maps.Map(mapEl, {
      center: { lat: 19.0760, lng: 72.8777 },
      zoom: 13,
      styles: getMapStyle(),
      disableDefaultUI: false,
    });
  
    directionsRenderer = new google.maps.DirectionsRenderer({
      polylineOptions: { strokeColor: '#6c63ff', strokeWeight: 4 }
    });
    directionsRenderer.setMap(map);
  }
  
  function setPickupMarker(lat, lng, address) {
    if (!map) {
      const el = document.getElementById('map-pickup');
      if (el) el.textContent = address;
      return;
    }
    if (pickupMarker) pickupMarker.setMap(null);
    pickupMarker = new google.maps.Marker({
      position: { lat, lng }, map,
      label: { text: 'A', color: '#fff' },
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: '#6c63ff', fillOpacity: 1,
        strokeColor: '#fff', strokeWeight: 2,
      }
    });
    map.setCenter({ lat, lng });
  
    document.getElementById('pickup_lat').value = lat;
    document.getElementById('pickup_lng').value = lng;
  }
  
  function setDropMarker(lat, lng, address) {
    if (!map) {
      const el = document.getElementById('map-drop');
      if (el) el.textContent = address;
      return;
    }
    if (dropMarker) dropMarker.setMap(null);
    dropMarker = new google.maps.Marker({
      position: { lat, lng }, map,
      label: { text: 'B', color: '#fff' },
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: '#ff6584', fillOpacity: 1,
        strokeColor: '#fff', strokeWeight: 2,
      }
    });
  
    document.getElementById('drop_lat').value = lat;
    document.getElementById('drop_lng').value = lng;
  
    // Draw route if both markers set
    if (pickupMarker) drawRoute();
  }
  
  function drawRoute() {
    if (!map || !pickupMarker || !dropMarker) return;
    const ds = new google.maps.DirectionsService();
    ds.route({
      origin: pickupMarker.getPosition(),
      destination: dropMarker.getPosition(),
      travelMode: google.maps.TravelMode.DRIVING,
    }, (result, status) => {
      if (status === 'OK') {
        directionsRenderer.setDirections(result);
        const leg = result.routes[0].legs[0];
        const km = (leg.distance.value / 1000).toFixed(1);
        document.getElementById('distance_km').value = km;
        document.getElementById('distance-display').textContent = leg.distance.text;
  
        // Trigger fare estimate
        const plat = pickupMarker.getPosition().lat();
        const plng = pickupMarker.getPosition().lng();
        const dlat = dropMarker.getPosition().lat();
        const dlng = dropMarker.getPosition().lng();
        FareEstimator.estimate(plat, plng, dlat, dlng).then(d => {
          if (d?.estimates) FareEstimator.updateCards(d.estimates);
        });
      }
    });
  }
  
  function getMapStyle() {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (!dark) return [];
    return [
      { elementType: 'geometry', stylers: [{ color: '#1a1a2e' }] },
      { elementType: 'labels.text.fill', stylers: [{ color: '#8d9db3' }] },
      { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#16213e' }] },
      { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#212a37' }] },
      { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0f0f2a' }] },
    ];
  }
  
  // ── Autocomplete (demo fallback) ───────────────────────────────────────────────
  function initLocationInputs() {
    // Demo locations for when Google Maps API is not set
    const demoLocations = [
      { name: 'Mumbai Airport, Sahar', lat: 19.0896, lng: 72.8656 },
      { name: 'Bandra West, Mumbai', lat: 19.0544, lng: 72.8402 },
      { name: 'Dadar Station, Mumbai', lat: 19.0178, lng: 72.8478 },
      { name: 'Andheri East, Mumbai', lat: 19.1136, lng: 72.8697 },
      { name: 'Colaba, Mumbai', lat: 18.9067, lng: 72.8147 },
      { name: 'Powai, Mumbai', lat: 19.1177, lng: 72.9060 },
      { name: 'Thane Station', lat: 19.2183, lng: 72.9781 },
      { name: 'Borivali West', lat: 19.2307, lng: 72.8567 },
      { name: 'Navi Mumbai', lat: 19.0330, lng: 73.0297 },
      { name: 'Churchgate Station', lat: 18.9355, lng: 72.8276 },
    ];
  
    ['pickup', 'drop'].forEach(field => {
      const input = document.getElementById(`${field}_address`);
      if (!input) return;
  
      let suggBox = document.getElementById(`${field}-suggestions`);
      if (!suggBox) {
        suggBox = document.createElement('div');
        suggBox.id = `${field}-suggestions`;
        suggBox.className = 'location-suggestions';
        suggBox.style.cssText = `
          position:absolute; top:100%; left:0; right:0; z-index:999;
          background:var(--bg-card); border:1px solid var(--border);
          border-radius:10px; box-shadow:var(--shadow-hover);
          max-height:200px; overflow-y:auto; display:none;`;
        input.parentElement.style.position = 'relative';
        input.parentElement.appendChild(suggBox);
      }
  
      input.addEventListener('input', function () {
        const q = this.value.toLowerCase();
        if (q.length < 2) { suggBox.style.display = 'none'; return; }
        const matches = demoLocations.filter(l => l.name.toLowerCase().includes(q));
        if (!matches.length) { suggBox.style.display = 'none'; return; }
        suggBox.innerHTML = matches.map(l =>
          `<div class="sugg-item" data-lat="${l.lat}" data-lng="${l.lng}"
                style="padding:10px 16px;cursor:pointer;font-size:0.88rem;
                       border-bottom:1px solid var(--border);"
                onmouseover="this.style.background='var(--primary-light)'"
                onmouseout="this.style.background=''">
            <i class="bi bi-geo-alt" style="color:var(--primary);margin-right:8px"></i>${l.name}
           </div>`
        ).join('');
        suggBox.style.display = 'block';
  
        suggBox.querySelectorAll('.sugg-item').forEach(item => {
          item.addEventListener('click', function () {
            input.value = this.textContent.trim();
            const lat = parseFloat(this.dataset.lat);
            const lng = parseFloat(this.dataset.lng);
            suggBox.style.display = 'none';
  
            if (field === 'pickup') {
              setPickupMarker(lat, lng, input.value);
              document.getElementById('pickup_lat').value = lat;
              document.getElementById('pickup_lng').value = lng;
            } else {
              setDropMarker(lat, lng, input.value);
              document.getElementById('drop_lat').value = lat;
              document.getElementById('drop_lng').value = lng;
            }
  
            // Auto-fetch fares if both are set
            const plat = document.getElementById('pickup_lat')?.value;
            const plng = document.getElementById('pickup_lng')?.value;
            const dlat = document.getElementById('drop_lat')?.value;
            const dlng = document.getElementById('drop_lng')?.value;
            if (plat && plng && dlat && dlng) {
              FareEstimator.estimate(
                parseFloat(plat), parseFloat(plng),
                parseFloat(dlat), parseFloat(dlng)
              ).then(d => {
                if (d?.estimates) FareEstimator.updateCards(d.estimates);
              });
            }
          });
        });
      });
  
      document.addEventListener('click', e => {
        if (!input.contains(e.target) && !suggBox.contains(e.target)) {
          suggBox.style.display = 'none';
        }
      });
    });
  }
  
  // ── Star Rating ────────────────────────────────────────────────────────────────
  function initStarRating() {
    const stars = document.querySelectorAll('.star-rating label');
    stars.forEach((star, idx) => {
      star.addEventListener('click', () => {
        const val = stars.length - idx;
        document.getElementById('rating-input').value = val;
        stars.forEach((s, i) => {
          s.style.color = (stars.length - i) <= val ? '#ffc107' : 'var(--border)';
        });
      });
    });
  }
  
  // ── Copy to clipboard ──────────────────────────────────────────────────────────
  function copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.innerHTML;
      btn.innerHTML = '<i class="bi bi-check2"></i>';
      setTimeout(() => btn.innerHTML = orig, 1500);
    });
  }
  
  // ── Charts (Admin) ─────────────────────────────────────────────────────────────
  function initCharts(revenueData, months, vehicleData) {
    // Revenue chart
    const revCtx = document.getElementById('revenue-chart');
    if (revCtx && revenueData) {
      new Chart(revCtx, {
        type: 'bar',
        data: {
          labels: months,
          datasets: [{
            label: 'Revenue (₹)',
            data: revenueData,
            backgroundColor: 'rgba(108,99,255,0.7)',
            borderColor: '#6c63ff',
            borderWidth: 2,
            borderRadius: 6,
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            y: { grid: { color: 'rgba(255,255,255,0.05)' } },
            x: { grid: { display: false } }
          }
        }
      });
    }
  
    // Vehicle type donut
    const vehCtx = document.getElementById('vehicle-chart');
    if (vehCtx && vehicleData) {
      new Chart(vehCtx, {
        type: 'doughnut',
        data: {
          labels: vehicleData.map(v => v[0]),
          datasets: [{
            data: vehicleData.map(v => v[1]),
            backgroundColor: ['#6c63ff', '#43e97b', '#ff6584', '#ffc107', '#17a2b8'],
            borderWidth: 0,
            hoverOffset: 4,
          }]
        },
        options: {
          responsive: true,
          cutout: '65%',
          plugins: { legend: { position: 'bottom' } }
        }
      });
    }
  
    // Earnings line chart (driver)
    const earnCtx = document.getElementById('earnings-chart');
    if (earnCtx && revenueData) {
      new Chart(earnCtx, {
        type: 'line',
        data: {
          labels: months,
          datasets: [{
            label: 'Earnings (₹)',
            data: revenueData,
            borderColor: '#43e97b',
            backgroundColor: 'rgba(67,233,123,0.1)',
            borderWidth: 2.5,
            tension: 0.4,
            fill: true,
            pointBackgroundColor: '#43e97b',
            pointRadius: 4,
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } }
        }
      });
    }
  }
  
  // ── Init ───────────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
    Sidebar.init();
    initAlerts();
    initVehicleCards();
    initLocationInputs();
    initStarRating();
    initMap();
  });