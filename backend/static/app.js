const LABELS = { normal: 'Normal', atencion: 'Atencion', critico: 'Critico' };

let thresholds   = { threshold_cpu: 85, threshold_ram: 85 };
let currentHours = 1;

const chartCpu = new Chart(document.getElementById('chart-cpu').getContext('2d'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'CPU %',
                data: [],
                borderColor: '#2290cc',
                backgroundColor: 'rgba(34,144,204,0.10)',
                tension: 0.3,
                fill: true,
                pointRadius: 0,
                borderWidth: 2,
            },
            {
                label: 'RAM %',
                data: [],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99,102,241,0.10)',
                tension: 0.3,
                fill: true,
                pointRadius: 0,
                borderWidth: 2,
            },
        ]
    },
    options: {
        animation: { duration: 400, easing: 'easeOutQuart' },
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { labels: { color: '#2a5a7a', boxWidth: 12, font: { size: 11 } } },
            annotation: { annotations: {} },
        },
        scales: {
            x: {
                ticks: { color: '#5a8aaa', maxTicksLimit: 6, maxRotation: 0, font: { size: 11 } },
                grid: { color: 'rgba(0,0,0,0.06)' }
            },
            y: {
                min: 0, max: 100,
                ticks: { color: '#5a8aaa', callback: v => v + '%', font: { size: 11 } },
                grid: { color: 'rgba(0,0,0,0.06)' }
            }
        }
    }
});

const chartNet = new Chart(document.getElementById('chart-net').getContext('2d'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Red entrada',
                data: [],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16,185,129,0.10)',
                tension: 0.3,
                fill: true,
                pointRadius: 0,
                borderWidth: 2,
            },
            {
                label: 'Red salida',
                data: [],
                borderColor: '#0ea5e9',
                backgroundColor: 'rgba(14,165,233,0.10)',
                tension: 0.3,
                fill: true,
                pointRadius: 0,
                borderWidth: 2,
            },
        ]
    },
    options: {
        animation: { duration: 400, easing: 'easeOutQuart' },
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { labels: { color: '#2a5a7a', boxWidth: 12, font: { size: 11 } } },
            annotation: { annotations: {} },
        },
        scales: {
            x: {
                ticks: { color: '#5a8aaa', maxTicksLimit: 6, maxRotation: 0, font: { size: 11 } },
                grid: { color: 'rgba(0,0,0,0.06)' }
            },
            y: {
                ticks: {
                    color: '#5a8aaa',
                    font: { size: 11 },
                    callback: v => {
                        if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + ' MB';
                        if (v >= 1_000)     return (v / 1_000).toFixed(0) + ' KB';
                        return v + ' B';
                    }
                },
                grid: { color: 'rgba(0,0,0,0.06)' }
            }
        }
    }
});

function downsample(arr, max) {
    if (arr.length <= max) return arr;
    const bucketSize = arr.length / max;
    return Array.from({ length: max }, (_, i) => {
        const start  = Math.floor(i * bucketSize);
        const end    = Math.min(Math.floor((i + 1) * bucketSize), arr.length);
        // Preserva el punto con mayor carga en el balde para no perder picos
        return arr.slice(start, end).reduce((peak, m) =>
            Math.max(m.cpu_pct, m.ram_pct) > Math.max(peak.cpu_pct, peak.ram_pct) ? m : peak
        );
    });
}

function formatBytes(bytes) {
    if (bytes >= 1_000_000) return [(bytes / 1_000_000).toFixed(1), 'MB'];
    if (bytes >= 1_000)     return [(bytes / 1_000).toFixed(1), 'KB'];
    return [bytes, 'B'];
}

function formatTime(ts) {
    return new Date(ts).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
}

function formatDateTime(ts) {
    return new Date(ts).toLocaleString('es-CO');
}

function levelFromValue(value, threshold) {
    if (value >= threshold)       return 'danger';
    if (value >= threshold - 10)  return 'warning';
    return 'ok';
}

async function loadMetrics() {
    const res = await fetch('/metricas/actuales');
    if (!res.ok) return;
    const d = await res.json();

    const cpuLevel = levelFromValue(d.cpu_pct, thresholds.threshold_cpu);
    const ramLevel = levelFromValue(d.ram_pct, thresholds.threshold_ram);

    const cpuEl = document.getElementById('cpu-val');
    const ramEl = document.getElementById('ram-val');
    const cpuBar = document.getElementById('cpu-bar');
    const ramBar = document.getElementById('ram-bar');

    cpuEl.textContent = d.cpu_pct.toFixed(1);
    cpuEl.className   = `card-value ${cpuLevel !== 'ok' ? cpuLevel : ''}`;
    cpuBar.style.width = d.cpu_pct + '%';
    cpuBar.className  = `progress-fill cpu ${cpuLevel !== 'ok' ? cpuLevel : ''}`;

    ramEl.textContent = d.ram_pct.toFixed(1);
    ramEl.className   = `card-value ${ramLevel !== 'ok' ? ramLevel : ''}`;
    ramBar.style.width = d.ram_pct + '%';
    ramBar.className  = `progress-fill ram ${ramLevel !== 'ok' ? ramLevel : ''}`;

    const [inVal, inUnit]   = formatBytes(d.net_bytes_in);
    const [outVal, outUnit] = formatBytes(d.net_bytes_out);
    document.getElementById('net-in-val').textContent  = inVal;
    document.getElementById('net-in-unit').textContent = inUnit;
    document.getElementById('net-out-val').textContent  = outVal;
    document.getElementById('net-out-unit').textContent = outUnit;
}

async function loadChart() {
    const [resData, resThresh] = await Promise.all([
        fetch(`/metricas/historial?horas=${currentHours}`),
        fetch('/config/umbrales'),
    ]);
    if (!resData.ok) return;

    const data = await resData.json();
    const emptyCpu = document.getElementById('chart-cpu-empty');
    const emptyNet = document.getElementById('chart-net-empty');

    if (!data.length) {
        emptyCpu.style.display = 'block';
        emptyNet.style.display = 'block';
        return;
    }
    emptyCpu.style.display = 'none';
    emptyNet.style.display = 'none';

    const sampled = downsample(data, 80);
    const labels  = sampled.map(d => formatTime(d.timestamp));

    chartCpu.data.labels           = labels;
    chartCpu.data.datasets[0].data = sampled.map(d => d.cpu_pct);
    chartCpu.data.datasets[1].data = sampled.map(d => d.ram_pct);

    chartNet.data.labels           = labels;
    chartNet.data.datasets[0].data = sampled.map(d => d.net_bytes_in);
    chartNet.data.datasets[1].data = sampled.map(d => d.net_bytes_out);

    if (resThresh.ok) {
        const t = await resThresh.json();
        thresholds = t;
        chartCpu.options.plugins.annotation.annotations = {
            cpuThreshold: {
                type: 'line',
                yMin: t.threshold_cpu,
                yMax: t.threshold_cpu,
                borderColor: 'rgba(34,144,204,0.5)',
                borderWidth: 1,
                borderDash: [5, 5],
                label: {
                    display: true,
                    content: 'Umbral CPU ' + t.threshold_cpu + '%',
                    color: '#1a6fa0',
                    backgroundColor: 'rgba(255,255,255,0)',
                    font: { size: 10 },
                    position: 'end',
                },
            },
            ramThreshold: {
                type: 'line',
                yMin: t.threshold_ram,
                yMax: t.threshold_ram,
                borderColor: 'rgba(99,102,241,0.5)',
                borderWidth: 1,
                borderDash: [5, 5],
                label: {
                    display: true,
                    content: 'Umbral RAM ' + t.threshold_ram + '%',
                    color: '#6366f1',
                    backgroundColor: 'rgba(255,255,255,0)',
                    font: { size: 10 },
                    position: 'start',
                },
            },
        };
    }

    chartCpu.update();
    chartNet.update();
}

async function loadNarrative() {
    const res = await fetch('/narrativa/ultima');
    const card = document.getElementById('narrative-card');
    const badge = document.getElementById('narrative-badge');
    const body = document.getElementById('narrative-body');

    if (!res.ok) {
        card.className = 'card narrative-card';
        body.innerHTML = `
            <div class="narrative-empty">
                <span>Generando primera narrativa...</span>
                <span style="font-size:0.75rem; color:#6e7681">El LLM analizara las metricas en breve</span>
            </div>`;
        return;
    }

    const d = await res.json();

    card.className  = `card narrative-card ${d.level}`;
    badge.className = `badge ${d.level}`;
    badge.textContent = LABELS[d.level] || d.level;
    body.innerHTML  = `<p class="narrative-text">${d.text}</p>`;
    document.getElementById('narrative-ts').textContent = 'Generada: ' + formatDateTime(d.timestamp);

    const ageMinutes = (Date.now() - new Date(d.timestamp)) / 60_000;
    document.getElementById('narrative-stale').style.display = ageMinutes > 60 ? 'inline' : 'none';

    document.getElementById('alert-badge').className  = `badge ${d.level}`;
    document.getElementById('alert-badge').textContent = LABELS[d.level] || d.level;
}

async function loadHistory() {
    const res = await fetch('/narrativa/historial');
    if (!res.ok) return;
    const data = await res.json();

    const list = document.getElementById('history-list');
    if (!data.length) {
        list.innerHTML = '<p style="color:#6e7681; font-size:0.85rem">Sin registros aun.</p>';
        return;
    }

    list.innerHTML = data.map(d => `
        <div class="history-item">
            <div class="status-dot ${d.level}"></div>
            <p class="history-text">${d.text}</p>
            <span class="history-ts">${formatDateTime(d.timestamp)}</span>
            <span class="badge ${d.level}" style="flex-shrink:0; margin-left:0.5rem">${LABELS[d.level]}</span>
        </div>
    `).join('');
}

async function loadSimMode() {
    const res = await fetch('/simulacion/estado');
    if (!res.ok) return;
    const d   = await res.json();
    const cls = { normal: 'normal', alta_carga: 'atencion', critico: 'critico', nocturno: 'nocturno' };
    const badge = document.getElementById('sim-mode-badge');
    badge.textContent = d.modes[d.mode] || d.mode;
    badge.className   = 'badge ' + (cls[d.mode] || 'normal');
    const instLabel = d.instance.label || d.instance.id || d.instance;
    document.getElementById('instance-name').textContent = 'Instancia: ' + instLabel;
}

async function refresh() {
    await Promise.all([loadMetrics(), loadChart(), loadNarrative(), loadHistory(), loadSimMode()]);
    document.getElementById('last-updated').textContent =
        'En vivo - ' + new Date().toLocaleTimeString('es-CO');
}

function setPresetHours(btn, hours) {
    document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentHours = hours;
    loadChart();
}

document.querySelectorAll('.time-btn[data-hours]').forEach(btn => {
    btn.addEventListener('click', () => setPresetHours(btn, parseInt(btn.dataset.hours)));
});

refresh();
setInterval(refresh, 60_000);
