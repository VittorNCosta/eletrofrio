const API = "/api";
let chart = null;

const $ = (id) => document.getElementById(id);

function severityClass(sev) {
    const map = { ok: "ok", warning: "warning", critical: "critical" };
    return map[sev] || "unknown";
}

function show(screenId) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    $(screenId).classList.add("active");
}

async function loadDevices() {
    try {
        const resp = await fetch(`${API}/devices/summary`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const devices = await resp.json();

        $("devices-loading").classList.add("hidden");
        const list = $("devices-list");
        list.innerHTML = "";

        if (!devices.length) {
            list.innerHTML = `<li class="loading">Nenhum dispositivo encontrado.</li>`;
            return;
        }

        devices.forEach(d => {
            const sev = d.last_severity || "unknown";
            const li = document.createElement("li");
            li.className = "device-item";
            li.innerHTML = `
                <span class="device-dot dot-${severityClass(sev)}"></span>
                <div class="device-info">
                    <div class="device-name">Device ${d.device_id}</div>
                    <div class="device-meta">
                        ${d.loja_nome || "Loja —"} · ${d.alarm_count} alarme(s)
                        ${d.last_severity ? ` · último: ${d.last_severity}` : ""}
                    </div>
                </div>
                <span class="device-arrow">›</span>
            `;
            li.addEventListener("click", () => analyzeDevice(d));
            list.appendChild(li);
        });
    } catch (e) {
        $("devices-loading").textContent = `Erro ao carregar: ${e.message}`;
    }
}

async function analyzeDevice(device) {
    console.log("[analyzeDevice] start", device);
    show("screen-detail");
    $("detail-title").textContent = `Device ${device.device_id}`;
    $("detail-subtitle").textContent = "analisando…";
    $("detail-loading").classList.remove("hidden");
    $("detail-loading").textContent = "🔍 Analisando dispositivo...";
    $("detail-content").classList.add("hidden");
    $("rag-card").classList.add("hidden");
    $("notif-card").classList.add("hidden");

    try {
        // Dispara análise + busca telemetria em paralelo
        console.log("[analyzeDevice] fetching analyze + telemetry...");
        const [analyzeResp, telemetryResp] = await Promise.all([
            fetch(`${API}/analyze/${device.device_id}`),
            fetch(`${API}/telemetry/${device.device_id}`)
        ]);
        console.log("[analyzeDevice] responses", analyzeResp.status, telemetryResp.status);

        if (!analyzeResp.ok) throw new Error(`Analyze HTTP ${analyzeResp.status}`);
        const decision = await analyzeResp.json();
        const telemetry = telemetryResp.ok ? await telemetryResp.json() : [];
        console.log("[analyzeDevice] decision", decision);
        console.log("[analyzeDevice] telemetry samples:", telemetry.length);

        renderDecision(decision, telemetry, device);
        console.log("[analyzeDevice] render OK");
    } catch (e) {
        console.error("[analyzeDevice] error", e);
        $("detail-loading").classList.remove("hidden");
        $("detail-loading").textContent = `Erro: ${e.message}`;
    }
}

function renderDecision(decision, telemetry, device) {
    $("detail-loading").classList.add("hidden");
    $("detail-content").classList.remove("hidden");

    // Subtitle no header
    $("detail-subtitle").textContent = device.loja_nome || `severity: ${decision.severity}`;

    // Severity badge
    const sevClass = severityClass(decision.severity);
    const badge = $("severity-badge");
    badge.className = `severity-badge sev-${sevClass}`;
    badge.textContent = `${decision.severity || "?"}`;

    $("reason-text").textContent = decision.reason || "Sem detalhes.";

    // Métricas
    const temps = extractTemps(telemetry);
    const max = temps.length ? Math.max(...temps).toFixed(1) : "—";
    const avg = temps.length ? (temps.reduce((a,b)=>a+b,0) / temps.length).toFixed(1) : "—";
    const min = temps.length ? Math.min(...temps).toFixed(1) : "—";
    $("metric-max").textContent = max === "—" ? "—" : `${max}°C`;
    $("metric-avg").textContent = avg === "—" ? "—" : `${avg}°C`;
    $("metric-min").textContent = min === "—" ? "—" : `${min}°C`;

    // Link para o gráfico em tela cheia (página dedicada, melhor no mobile)
    const fs = $("chart-fullscreen");
    const loja = encodeURIComponent(device.loja_nome || "");
    fs.href = `chart.html?device=${device.device_id}&loja=${loja}`;
    fs.classList.remove("hidden");

    // Chart é opcional — se Chart.js falhou ao carregar, segue o jogo
    try {
        renderChart(telemetry);
    } catch (e) {
        console.warn("[renderDecision] Chart falhou:", e);
    }
    renderAlarms(device);

    // RAG
    if (decision.rag_recommendation) {
        $("rag-card").classList.remove("hidden");
        $("rag-text").textContent = decision.rag_recommendation;
    }

    // Alerta WhatsApp ao cliente
    const notif = decision.notification_response;
    if (notif) {
        $("notif-card").classList.remove("hidden");
        const phone = notif.phone ? ` para ${notif.phone}` : "";
        if (decision.notification_sent) {
            $("notif-text").textContent = `✅ Alerta enviado${phone}.`;
        } else if (notif.reason === "no_phone") {
            $("notif-text").textContent = "ℹ️ Loja sem telefone cadastrado — alerta não enviado.";
        } else {
            $("notif-text").textContent = `⚠️ Falha ao enviar alerta${phone}.`;
        }
    }
}

function extractTemps(telemetry) {
    // Formato atual: {labels, datasets:[{label, color, values}]}
    if (telemetry && Array.isArray(telemetry.datasets)) {
        const ds = telemetry.datasets.find(d => {
            const lbl = (d.label || "").toLowerCase();
            return lbl.includes("temperatura") && !lbl.includes("setpoint");
        });
        return ds ? ds.values.filter(v => typeof v === "number") : [];
    }
    // Fallback: list[dict] legado
    const keys = ["temperatura", "temp", "valor", "value"];
    const temps = [];
    for (const row of telemetry || []) {
        for (const k of keys) {
            if (typeof row[k] === "number") { temps.push(row[k]); break; }
        }
    }
    return temps;
}

function renderChart(telemetry) {
    if (typeof Chart === "undefined") {
        console.warn("[renderChart] Chart.js não carregou (CDN bloqueada?). Pulando gráfico.");
        return;
    }
    const canvas = $("temp-chart");
    if (chart) chart.destroy();

    const labels = (telemetry && telemetry.labels) ? telemetry.labels : [];
    const apiDatasets = (telemetry && telemetry.datasets) ? telemetry.datasets : [];

    // Mapeia datasets da API para formato Chart.js
    const datasets = apiDatasets.map(ds => ({
        label: ds.label,
        data: ds.values,
        borderColor: ds.color || "#0ea5e9",
        backgroundColor: (ds.color || "#0ea5e9") + "22",
        fill: false,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 1.5,
    }));

    // Linha de threshold
    if (datasets.length && labels.length) {
        const threshold = 10;
        datasets.push({
            label: "Limite",
            data: labels.map(() => threshold),
            borderColor: "#ef4444",
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false,
            borderWidth: 1,
        });
    }

    chart = new Chart(canvas, {
        type: "line",
        data: { labels, datasets },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: "bottom",
                    labels: { boxWidth: 10, font: { size: 9 }, padding: 6 }
                }
            },
            scales: {
                y: { beginAtZero: false, ticks: { font: { size: 9 } } },
                x: { ticks: { maxTicksLimit: 6, font: { size: 9 } } }
            }
        }
    });
}

function renderAlarms(device) {
    const list = $("alarms-list");
    list.innerHTML = "";
    if (!device.alarm_count || device.alarm_count === 0) {
        list.innerHTML = `<li class="empty">✓ Nenhum alarme recente.</li>`;
        return;
    }
    const li = document.createElement("li");
    li.textContent = `${device.alarm_count} alarme(s) registrado(s) · tag: ${device.tag || "—"}`;
    list.appendChild(li);
}

// ===== Eventos =====
$("back-btn").addEventListener("click", () => show("screen-list"));

// Atualiza relógio
function updateClock() {
    const now = new Date();
    const h = now.getHours().toString().padStart(2, "0");
    const m = now.getMinutes().toString().padStart(2, "0");
    $("status-time").textContent = `${h}:${m}`;
}
updateClock();
setInterval(updateClock, 30000);

// Bootstrap
loadDevices();
