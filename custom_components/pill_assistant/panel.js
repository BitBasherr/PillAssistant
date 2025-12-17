class HaPanelPillAssistant extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this._render();
    }
    this._update();
  }

  set panel(panel) {
    this._panel = panel;
  }

  _render() {
    this._rendered = true;
    this.innerHTML = `
      <style>
        .pa-container { padding: 16px; }
        .pa-header { display: flex; justify-content: space-between; align-items: center; }
        .pa-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-top: 12px; }
        .pa-card { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 12px; padding: 12px; background: var(--card-background-color, #fff); box-shadow: var(--ha-card-box-shadow, 0 1px 4px rgba(0,0,0,0.1)); }
        .pa-row { display: flex; justify-content: space-between; align-items: center; margin-top: 4px; }
        .pa-actions { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
        .pa-badge { background: var(--primary-color, #6200ee); color: #fff; padding: 2px 8px; border-radius: 8px; font-size: 12px; }
        button.pa-btn { cursor: pointer; border: none; border-radius: 8px; padding: 6px 10px; background: var(--primary-color, #6200ee); color: #fff; }
        button.pa-btn.secondary { background: var(--secondary-text-color, #555); color: var(--primary-background-color, #fff); }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 6px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
      </style>
      <div class="pa-container">
        <div class="pa-header">
          <div>
            <h1>Pill Assistant</h1>
            <p>Admin-only quick actions and daily view.</p>
          </div>
          <div class="pa-badge" id="pa-log-path"></div>
        </div>
        <div id="pa-medications"></div>
        <h2 style="margin-top:16px">Today's doses</h2>
        <div id="pa-history"></div>
      </div>
    `;
  }

  _update() {
    if (!this._hass) return;
    const medsContainer = this.querySelector('#pa-medications');
    const historyContainer = this.querySelector('#pa-history');
    const logPathEl = this.querySelector('#pa-log-path');

    const meds = Object.values(this._hass.states)
      .filter((st) => st.entity_id.startsWith('sensor.pa_'))
      .sort((a, b) => (a.attributes.friendly_name || '').localeCompare(b.attributes.friendly_name || ''));

    if (logPathEl) {
      const path = this._panel?.config?.log_path;
      logPathEl.textContent = path ? `Log: ${path}` : '';
      logPathEl.title = 'CSV history location';
    }

    if (medsContainer) {
      if (!meds.length) {
        medsContainer.innerHTML = '<p>No medications configured yet.</p>';
      } else {
        medsContainer.innerHTML = '<div class="pa-grid"></div>';
        const grid = medsContainer.querySelector('.pa-grid');
        meds.forEach((med) => {
          const medId = med.attributes['Medication ID'] || med.entity_id;
          const doses = med.attributes['Doses today'] || [];
          const ratio = med.attributes.taken_scheduled_ratio || med.attributes['taken_scheduled_ratio'];
          const nextDose = med.attributes['Next dose at'] || med.attributes.next_dose_time;
          const lastTaken = med.attributes['Last taken at'] || med.attributes.last_taken;
          const card = document.createElement('div');
          card.className = 'pa-card';
          card.innerHTML = `
            <div class="pa-row"><strong>${med.attributes.friendly_name || med.entity_id}</strong><span class="pa-badge">${med.state}</span></div>
            <div class="pa-row"><span>Next</span><span>${nextDose || 'n/a'}</span></div>
            <div class="pa-row"><span>Last taken</span><span>${lastTaken || 'n/a'}</span></div>
            <div class="pa-row"><span>Doses today</span><span>${doses.length}</span></div>
            <div class="pa-row"><span>Ratio</span><span>${ratio || '0/0'}</span></div>
            <div class="pa-actions">
              <button class="pa-btn" data-action="take" data-med="${medId}">Mark taken</button>
              <button class="pa-btn secondary" data-action="snooze" data-med="${medId}">Snooze</button>
              <button class="pa-btn secondary" data-action="test" data-med="${medId}">Test notify</button>
            </div>
          `;
          grid.appendChild(card);
        });
        grid.querySelectorAll('button.pa-btn').forEach((btn) => {
          btn.addEventListener('click', (ev) => this._handleAction(ev));
        });
      }
    }

    if (historyContainer) {
      const allDoses = meds.flatMap((m) => (m.attributes['Doses today'] || []).map((ts) => ({
        name: m.attributes.friendly_name || m.entity_id,
        timestamp: ts,
      })));
      if (!allDoses.length) {
        historyContainer.innerHTML = '<p>No doses recorded today.</p>';
      } else {
        const rows = allDoses
          .sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''))
          .map((row) => `<tr><td>${row.name}</td><td>${row.timestamp}</td></tr>`)
          .join('');
        historyContainer.innerHTML = `<table><thead><tr><th>Medication</th><th>Time</th></tr></thead><tbody>${rows}</tbody></table>`;
      }
    }
  }

  async _handleAction(ev) {
    const button = ev.currentTarget;
    const medId = button.dataset.med;
    const action = button.dataset.action;
    if (!this._hass || !medId || !action) return;

    if (action === 'take') {
      await this._hass.callService('pill_assistant', 'take_medication', { medication_id: medId });
    } else if (action === 'snooze') {
      await this._hass.callService('pill_assistant', 'snooze_medication', { medication_id: medId });
    } else if (action === 'test') {
      await this._hass.callService('pill_assistant', 'test_notification', { medication_id: medId });
    }
  }
}

customElements.define('ha-panel-pill-assistant', HaPanelPillAssistant);
