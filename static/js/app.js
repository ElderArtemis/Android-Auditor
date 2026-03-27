/**
 * AndroidAuditor v1.0.0 — Frontend JS
 */

let lastResult = null;
let deviceConnected = false;

setInterval(() => { document.getElementById('clock').textContent = new Date().toTimeString().split(' ')[0]; }, 1000);

// Nav tabs
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel-view').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`panel-${tab.dataset.panel}`).classList.add('active');
  });
});

// Check ADB status on load and periodically
checkADBStatus();
setInterval(checkADBStatus, 10000);

document.getElementById('refreshBtn').addEventListener('click', checkADBStatus);
document.getElementById('scanBtn').addEventListener('click', startScan);
document.getElementById('exportBtn').addEventListener('click', exportJSON);

async function checkADBStatus() {
  try {
    const res = await fetch('/api/scan/status');
    const data = await res.json();

    const dot    = document.getElementById('statusDot');
    const badge  = document.getElementById('deviceBadge');
    const name   = document.getElementById('deviceName');
    const scanBtn = document.getElementById('scanBtn');

    if (data.connected) {
      dot.className = 'dot';
      badge.className = 'device-badge connected';
      badge.textContent = 'CONNECTED';
      name.textContent = data.devices[0]?.split('\t')[0] || 'Device';
      scanBtn.disabled = false;
      deviceConnected = true;
      document.getElementById('connectScreen').style.display = 'none';
    } else if (data.unauthorized?.length > 0) {
      dot.className = 'dot disconnected';
      badge.className = 'device-badge unauthorized';
      badge.textContent = 'AUTHORIZE ON DEVICE';
      name.textContent = 'Waiting for authorization...';
      scanBtn.disabled = true;
      deviceConnected = false;
    } else {
      dot.className = 'dot disconnected';
      badge.className = 'device-badge disconnected';
      badge.textContent = 'NO DEVICE';
      name.textContent = 'Connect a device via USB';
      scanBtn.disabled = true;
      deviceConnected = false;
      if (!lastResult) {
        document.getElementById('connectScreen').style.display = 'flex';
      }
    }

    document.getElementById('adbPath').textContent = data.adb_path || 'Not found';

  } catch (err) {
    console.error('Status check failed:', err);
  }
}

async function startScan() {
  document.getElementById('scanBtn').disabled = true;
  document.getElementById('progressSection').classList.add('visible');
  document.getElementById('gradeBar').style.display = 'none';
  document.getElementById('modulesGrid').innerHTML = buildSkeleton();
  document.getElementById('modulesGrid').style.display = 'grid';
  document.getElementById('connectScreen').style.display = 'none';
  document.getElementById('exportBtn').style.display = 'none';

  setProgress(5, 'Connecting to device...');

  try {
    setProgress(15, 'Reading device information...');
    const res = await fetch('/api/scan', { method: 'POST' });
    if (!res.ok) throw new Error(`Server error: ${res.status}`);

    setProgress(65, 'Analyzing apps and permissions...');
    const data = await res.json();
    lastResult = data;

    setProgress(90, 'Calculating security score...');
    await new Promise(r => setTimeout(r, 200));

    renderResults(data);
    setProgress(100, `✓ Audit complete — Grade: ${data.security?.grade}`);
    document.getElementById('exportBtn').style.display = 'inline-block';

  } catch (err) {
    setProgress(100, `✗ ${err.message}`);
    document.getElementById('modulesGrid').innerHTML =
      `<div class="module span-3"><div class="module-body"><div class="error-msg">SCAN FAILED: ${err.message}</div></div></div>`;
  } finally {
    document.getElementById('scanBtn').disabled = !deviceConnected;
  }
}

function setProgress(pct, msg) {
  document.getElementById('progressBar').style.width = pct + '%';
  document.getElementById('progressPct').textContent = pct + '%';
  if (msg) { document.getElementById('progressLabel').textContent = msg; document.getElementById('scanLog').textContent = msg; }
}

function buildSkeleton() {
  return ['SECURITY SCORE','DEVICE INFO','INSTALLED APPS','RISKY PERMISSIONS','WIFI NETWORKS','CERTIFICATES'].map((t,i) =>
    `<div class="module ${i===2||i===3?'span-2':''}" style="animation-delay:${i*0.06}s">
      <div class="module-header"><div class="module-title">${t}</div><span class="module-badge badge-scanning">SCANNING</span></div>
      <div class="module-body"><div class="placeholder">⬡ reading device...</div></div>
    </div>`).join('');
}

// ── RENDER ──
function renderResults(data) {
  const { security, modules: m } = data;
  renderGradeBar(security, m);
  document.getElementById('modulesGrid').innerHTML = [
    cardScore(security),
    cardDevice(m.device),
    cardAppsOverview(m.apps),
    cardRiskyApps(m.apps),
    cardNetwork(m.network),
    cardCerts(m.certs),
  ].join('');
}

function renderGradeBar(sec, m) {
  const grade    = sec?.grade || '?';
  const score    = sec?.score || 0;
  const device   = m?.device  || {};
  const apps     = m?.apps    || {};
  const certs    = m?.certs   || {};
  const gradeC   = gradeClass(grade);

  document.getElementById('gradeBar').innerHTML = `
    <div class="grade-card">
      <div class="grade-lbl">SECURITY GRADE</div>
      <div class="grade-val ${gradeC}">${grade}</div>
      <div class="grade-sub">score ${score}/100</div>
    </div>
    <div class="grade-card">
      <div class="grade-lbl">ANDROID VERSION</div>
      <div class="grade-val info">${device.android_version || '?'}</div>
      <div class="grade-sub">SDK ${device.sdk_version || '?'}</div>
    </div>
    <div class="grade-card">
      <div class="grade-lbl">RISKY APPS</div>
      <div class="grade-val ${apps.total_risky > 0 ? 'warn' : 'ok'}">${apps.total_risky || 0}</div>
      <div class="grade-sub">with dangerous perms</div>
    </div>
    <div class="grade-card">
      <div class="grade-lbl">SIDELOADED APKs</div>
      <div class="grade-val ${apps.unknown_sources_count > 0 ? 'danger' : 'ok'}">${apps.unknown_sources_count || 0}</div>
      <div class="grade-sub">outside Play Store</div>
    </div>
    <div class="grade-card">
      <div class="grade-lbl">USER CA CERTS</div>
      <div class="grade-val ${certs.user_cert_count > 0 ? 'critical' : 'ok'}">${certs.user_cert_count || 0}</div>
      <div class="grade-sub">${certs.user_cert_count > 0 ? 'MITM risk' : 'clean'}</div>
    </div>`;
  document.getElementById('gradeBar').style.display = 'grid';
}

// ── HELPERS ──
function gradeClass(g) {
  return g==='A+'?'aplus':g==='A'?'a':g==='B'?'b':g==='C'?'c':g==='D'?'d':'f';
}
function badge(cls, txt) { return `<span class="module-badge ${cls}">${txt}</span>`; }
function card(title, badgeHtml, bodyHtml, spanClass='') {
  return `<div class="module ${spanClass}">
    <div class="module-header"><div class="module-title">${title}</div>${badgeHtml}</div>
    <div class="module-body">${bodyHtml}</div>
  </div>`;
}
function row(k, v, cls='') {
  return `<div class="data-row"><div class="data-key">${k}</div><div class="data-val ${cls}">${v??'N/A'}</div></div>`;
}

// ── SCORE CARD ──
function cardScore(sec) {
  if (!sec) return card('SECURITY SCORE', badge('badge-info','N/A'), '<div class="placeholder">⬡ no data</div>');
  const { score, grade, findings } = sec;
  const gc = gradeClass(grade);
  const labels = { 'A+': 'EXCELLENT', A: 'GOOD', B: 'FAIR', C: 'ACCEPTABLE', D: 'POOR', F: 'CRITICAL' };
  const body = `
    <div class="score-wrap">
      <div class="score-val ${gc}">${grade}</div>
      <div><div class="score-label">${labels[grade]||grade}</div><div class="score-sub">SECURITY SCORE: ${score}/100</div></div>
    </div>
    <div class="score-bar-wrap"><div class="score-bar ${gc}" style="width:${score}%"></div></div>
    <div class="findings-list">${(findings||[]).map(f=>`<div class="finding ${f.level}">${f.label}</div>`).join('')||'<div class="finding ok">No critical issues found</div>'}</div>`;
  return card('SECURITY SCORE', badge(gc==='aplus'||gc==='a'?'badge-ok':gc==='b'?'badge-info':gc==='c'?'badge-warn':'badge-danger', labels[grade]||grade), body);
}

// ── DEVICE CARD ──
function cardDevice(d) {
  if (!d || d.error) return card('DEVICE INFO', badge('badge-danger','ERROR'), `<div class="error-msg">${d?.error||'Failed'}</div>`);
  const patch = d.security_patch || '?';
  const patchDays = patch !== '?' ? Math.floor((Date.now() - new Date(patch)) / 86400000) : null;
  const patchCls = patchDays === null ? '' : patchDays > 365 ? 'critical' : patchDays > 180 ? 'danger' : patchDays > 90 ? 'warn' : 'ok';

  const body = `
    ${row('MODEL', d.model, 'accent')}
    ${row('ANDROID', `${d.android_version} (SDK ${d.sdk_version})`, 'accent')}
    ${row('SECURITY PATCH', `${patch}${patchDays ? ` (${patchDays}d ago)` : ''}`, patchCls)}
    ${row('ENCRYPTED', d.encrypted ? 'YES ✓' : 'NO ⚠', d.encrypted ? 'ok' : 'critical')}
    ${row('SCREEN LOCK', d.screen_lock ? 'YES ✓' : 'NO ⚠', d.screen_lock ? 'ok' : 'danger')}
    ${row('USB DEBUGGING', d.usb_debugging ? 'ENABLED ⚠' : 'DISABLED ✓', d.usb_debugging ? 'warn' : 'ok')}
    ${row('DEV OPTIONS', d.dev_options ? 'ENABLED ⚠' : 'DISABLED ✓', d.dev_options ? 'warn' : 'ok')}
    ${row('ROOTED', d.rooted ? 'YES ⚠' : 'NOT DETECTED', d.rooted ? 'critical' : 'ok')}
    ${row('BUILD TYPE', d.build_type, '')}
    ${d.battery !== null ? row('BATTERY', `${d.battery}%`, d.battery > 20 ? 'ok' : 'warn') : ''}
    ${row('CPU', d.cpu_abi, 'info')}`;
  return card('DEVICE INFO', badge(d.rooted ? 'badge-critical' : 'badge-ok', d.model?.split(' ')[0] || 'DEVICE'), body);
}

// ── APPS OVERVIEW ──
function cardAppsOverview(a) {
  if (!a || a.error) return card('INSTALLED APPS', badge('badge-danger','ERROR'), `<div class="error-msg">${a?.error||'Failed'}</div>`);
  const body = `
    ${row('TOTAL APPS', a.total_packages, '')}
    ${row('THIRD PARTY', a.third_party_count, a.third_party_count > 50 ? 'warn' : 'ok')}
    ${row('SYSTEM APPS', a.system_count, 'info')}
    ${row('SIDELOADED APKs', a.unknown_sources_count || 0, a.unknown_sources_count > 0 ? 'danger' : 'ok')}
    ${row('RISKY APPS', a.total_risky || 0, a.total_risky > 5 ? 'warn' : a.total_risky > 0 ? 'warn' : 'ok')}
    ${row('CRITICAL PERMS', a.critical_permission_count || 0, a.critical_permission_count > 3 ? 'critical' : a.critical_permission_count > 0 ? 'danger' : 'ok')}
    ${(a.unknown_sources||[]).slice(0,3).map(u => `<div class="data-row"><div class="data-key">SIDELOADED</div><div class="data-val danger">${u.package?.split('.').pop()||u.package}</div></div>`).join('')}`;
  return card('INSTALLED APPS', badge(a.unknown_sources_count > 0 ? 'badge-danger' : 'badge-ok', `${a.total_packages} APPS`), body);
}

// ── RISKY APPS ──
function cardRiskyApps(a) {
  if (!a || a.error) return card('RISKY PERMISSIONS', badge('badge-danger','ERROR'), `<div class="error-msg">${a?.error||'Failed'}</div>`, 'span-2');
  const apps = a.risky_apps || [];
  if (!apps.length) return card('RISKY PERMISSIONS', badge('badge-ok','CLEAN'), '<div class="placeholder">⬡ No apps with dangerous permissions found</div>', 'span-2');

  const html = apps.slice(0,10).map(app => `
    <div class="app-item">
      <div class="app-sev ${app.max_level}"></div>
      <div class="app-info">
        <div class="app-name">${app.name}</div>
        <div class="app-pkg">${app.package}</div>
        <div class="app-perms">${app.dangerous.slice(0,4).map(p =>
          `<span class="app-perm ${p.level}">${p.label}</span>`).join('')}
          ${app.dangerous.length > 4 ? `<span class="app-perm medium">+${app.dangerous.length-4} more</span>` : ''}
        </div>
      </div>
    </div>`).join('');

  const hasCritical = apps.some(a => a.max_level === 'critical');
  return card('RISKY PERMISSIONS', badge(hasCritical ? 'badge-critical' : 'badge-warn', `${apps.length} APPS`),
    `<div class="scrollable">${html}</div>`, 'span-2');
}

// ── NETWORK CARD ──
function cardNetwork(n) {
  if (!n || n.error) return card('WIFI NETWORKS', badge('badge-danger','ERROR'), `<div class="error-msg">${n?.error||'Failed'}</div>`);
  const nets = n.saved_networks || [];
  const body = `
    ${row('SAVED NETWORKS', n.saved_count || 0, '')}
    ${n.current_wifi ? row('CONNECTED TO', n.current_wifi, 'accent') : ''}
    ${row('VPN ACTIVE', n.vpn_active ? 'YES' : 'NO', n.vpn_active ? 'ok' : 'info')}
    ${row('PROXY', n.proxy_configured ? n.proxy_value : 'NONE', n.proxy_configured ? 'warn' : 'ok')}
    ${nets.length ? `<div class="field-label" style="margin-top:8px">SAVED NETWORKS</div>
    <div class="scrollable">${nets.slice(0,10).map(net => `
      <div class="wifi-item">
        <div class="wifi-icon">⊙</div>
        <div class="wifi-ssid">${net.ssid}</div>
      </div>`).join('')}</div>` : ''}`;
  return card('WIFI NETWORKS', badge('badge-info', `${n.saved_count || 0} SAVED`), body);
}

// ── CERTS CARD ──
function cardCerts(c) {
  if (!c || c.error) return card('CA CERTIFICATES', badge('badge-danger','ERROR'), `<div class="error-msg">${c?.error||'Failed'}</div>`);
  const userCerts = c.user_certs || [];
  const body = `
    ${row('USER-INSTALLED CAs', c.user_cert_count || 0, c.user_cert_count > 0 ? 'critical' : 'ok')}
    ${row('SYSTEM CAs', c.system_cert_count || 0, 'info')}
    ${row('MITM RISK', c.mitm_risk ? 'HIGH ⚠' : 'LOW ✓', c.mitm_risk ? 'critical' : 'ok')}
    ${userCerts.length ? `<div class="field-label" style="margin-top:8px">USER-INSTALLED CERTIFICATES</div>
    ${userCerts.map(cert => `
      <div class="cert-item">
        <div class="cert-file">${cert.file}</div>
        ${cert.detail ? `<div class="cert-detail">${cert.detail.split('\n')[0]}</div>` : ''}
      </div>`).join('')}` : ''}
    ${!c.mitm_risk ? '<div class="info-msg" style="margin-top:8px">No user-installed certificates found</div>' : ''}`;
  return card('CA CERTIFICATES', badge(c.mitm_risk ? 'badge-critical' : 'badge-ok', c.mitm_risk ? 'MITM RISK' : 'CLEAN'), body);
}

// ── EXPORT ──
function exportJSON() {
  if (!lastResult) return;
  const b = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(b);
  a.download = `android_audit_${Date.now()}.json`;
  a.click(); URL.revokeObjectURL(a.href);
}
