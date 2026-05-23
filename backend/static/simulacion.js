let simState = { mode: 'normal', instance: {}, modes: {} };

async function loadSimulation() {
    const res = await fetch('/simulacion/estado');
    if (!res.ok) return;
    simState = await res.json();
    renderModes();
    updateHeader();
}

function renderModes() {
    document.getElementById('sim-modes').innerHTML = Object.entries(simState.modes).map(([key, label]) => `
        <button class="sim-mode-btn mode-${key} ${key === simState.mode ? 'active' : ''}"
                onclick="setMode('${key}')">
            ${label}
        </button>
    `).join('');
}

function updateHeader() {
    const instLabel = simState.instance.label || simState.instance.id || '';
    document.getElementById('sim-status-line').textContent = `Instancia: ${instLabel}`;

    const badge = document.getElementById('mode-badge');
    badge.textContent = simState.modes[simState.mode] || simState.mode;
    const cls = { normal: 'normal', alta_carga: 'atencion', critico: 'critico', nocturno: 'nocturno' };
    badge.className = 'badge ' + (cls[simState.mode] || 'normal');
}

async function setMode(mode) {
    const res = await fetch(`/simulacion/modo/${mode}`, { method: 'POST' });
    if (!res.ok) return;
    simState.mode = mode;
    renderModes();
    updateHeader();
}

async function forceRead() {
    const btn = document.getElementById('btn-force-read');
    btn.disabled = true;
    btn.textContent = 'Ejecutando...';
    const res = await fetch('/simulacion/lectura', { method: 'POST' });
    btn.textContent = res.ok ? 'Completado!' : 'Error al ejecutar';
    setTimeout(() => { btn.textContent = 'Forzar lectura'; btn.disabled = false; }, 2200);
}

async function forceNarrative() {
    const btn = document.getElementById('btn-force-narrative');
    btn.disabled = true;
    btn.textContent = 'Generando...';
    const res = await fetch('/simulacion/narrativa', { method: 'POST' });
    btn.textContent = res.ok ? 'Completado!' : 'Error al generar';
    setTimeout(() => { btn.textContent = 'Generar narrativa'; btn.disabled = false; }, 3000);
}

async function resetAll() {
    if (!confirm('Esto borrara TODOS los registros de metricas y narrativas.\n\nLas graficas quedaran vacias hasta que se generen nuevas lecturas.\n\nContinuar?')) return;
    const btn = document.getElementById('btn-reset');
    const feedback = document.getElementById('reset-feedback');
    btn.disabled = true;
    btn.textContent = 'Borrando...';
    feedback.style.display = 'none';

    try {
        const res = await fetch('/simulacion/reset', { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
            btn.textContent = 'Completado!';
            simState.mode = 'normal';
            renderModes();
            updateHeader();
            const spikeTip = 'El escenario incluye entre 1 y 3 picos de carga con ramp-up/down suave, distribuidos en las ultimas 24 horas.';
            feedback.innerHTML =
                `<strong>Escenario generado.</strong> Se eliminaron ${data.deleted.metrics} registros anteriores y se crearon ${data.inserted} nuevos puntos. ${spikeTip}<br>` +
                `<a href="/dashboard" style="color:#065f46; font-weight:700;">Ir al Monitor &rarr;</a>`;
            feedback.className = 'reset-feedback ok';
            feedback.style.display = 'block';
        } else {
            btn.textContent = 'Error';
            feedback.textContent = 'Error al reiniciar: ' + (data.detail || 'revisa los logs del servidor.');
            feedback.className = 'reset-feedback error';
            feedback.style.display = 'block';
        }
    } catch (e) {
        btn.textContent = 'Error';
        feedback.textContent = 'Error de red al conectar con el servidor.';
        feedback.className = 'reset-feedback error';
        feedback.style.display = 'block';
    }

    setTimeout(() => { btn.textContent = 'Borrar registros y reiniciar'; btn.disabled = false; }, 3000);
}

loadSimulation();
