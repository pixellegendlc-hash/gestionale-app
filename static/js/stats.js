// ═══════════════════════════════════════
// stats.js — Statistiche e Grafici
// ═══════════════════════════════════════
const Stats = (() => {
  let charts = {};

  function destroyCharts() {
    Object.values(charts).forEach(c => { try { c.destroy(); } catch(e){} });
    charts = {};
  }

  async function load() {
    destroyCharts();
    document.getElementById('stats-content').innerHTML = `<div class="loader"><div class="spinner"></div></div>`;
    try {
      const d = await api('/api/stats');
      render(d);
    } catch(e) {
      document.getElementById('stats-content').innerHTML = `<div class="empty"><div class="empty-icon"><i class="fa fa-chart-line"></i></div><p>Errore caricamento dati</p></div>`;
    }
  }

  function render(d) {
    const t = d.tasks;
    const fin = d.finanze_mese;
    const urgIcon = t.urgenti.length > 0 ? '⚠️' : '✅';

    document.getElementById('stats-content').innerHTML = `
      <!-- KPI GRID -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">📋</div>
          <div class="stat-val col-accent">${t.totale}</div>
          <div class="stat-lbl">Task Totali</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">🏆</div>
          <div class="stat-val col-green">${t.percentuale}%</div>
          <div class="stat-lbl">Completamento</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">${urgIcon}</div>
          <div class="stat-val" style="color:${t.urgenti.length>0?'var(--red)':'var(--green)'}">${t.urgenti.length}</div>
          <div class="stat-lbl">Task Urgenti</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📝</div>
          <div class="stat-val col-accent">${d.note}</div>
          <div class="stat-lbl">Appunti</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">💰</div>
          <div class="stat-val col-green">${fmtMoney(fin.entrate)}</div>
          <div class="stat-lbl">Entrate mese</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📉</div>
          <div class="stat-val col-red">${fmtMoney(fin.uscite)}</div>
          <div class="stat-lbl">Uscite mese</div>
        </div>
      </div>

      <!-- URGENTI -->
      ${t.urgenti.length ? `
        <div class="chart-card" style="border-color:var(--red)33">
          <div class="chart-title" style="color:var(--red)">⚠️ Task Urgenti</div>
          ${t.urgenti.map(u => `
            <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)">
              <span style="font-size:14px;font-weight:600">${u.nome}</span>
              <span style="${u.giorni<0?'color:var(--purple)':'color:var(--red)'}">
                ${u.giorni<0?'SCADUTO':u.giorni===0?'OGGI':u.giorni+'g'}
              </span>
            </div>`).join('')}
        </div>` : ''}

      <!-- GRAFICO STATI TASK -->
      <div class="chart-card">
        <div class="chart-title">Distribuzione Task</div>
        <canvas id="chart-stati" height="200"></canvas>
      </div>

      <!-- GRAFICO PRIORITÀ -->
      <div class="chart-card">
        <div class="chart-title">Task per Priorità (attivi)</div>
        <canvas id="chart-pri" height="180"></canvas>
      </div>

      <!-- GRAFICO FINANZIARIO -->
      <div class="chart-card">
        <div class="chart-title">Andamento Finanziario 6 mesi</div>
        <canvas id="chart-fin" height="220"></canvas>
      </div>

      <!-- EXPORT -->
      <div class="chart-card">
        <div class="chart-title">Esporta Dati</div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <a href="/api/export/tasks"   class="btn btn-ghost" style="text-align:center;text-decoration:none"><i class="fa fa-download"></i> Esporta Task (CSV)</a>
          <a href="/api/export/finanze" class="btn btn-ghost" style="text-align:center;text-decoration:none"><i class="fa fa-download"></i> Esporta Finanze (CSV)</a>
          <a href="/api/export/appunti" class="btn btn-ghost" style="text-align:center;text-decoration:none"><i class="fa fa-download"></i> Esporta Appunti (CSV)</a>
        </div>
      </div>`;

    // ── CHART STATI ──
    const ctxS = document.getElementById('chart-stati');
    if (ctxS) {
      charts.stati = new Chart(ctxS, {
        type: 'doughnut',
        data: {
          labels: ['Da Iniziare','In Progresso','Completati','Falliti'],
          datasets: [{ data: [t.da_iniziare, t.in_progresso, t.completati, t.falliti],
            backgroundColor: ['#4f7bff','#ffd60a','#00e676','#ff4d6a'], borderWidth: 0 }]
        },
        options: { plugins: { legend: { labels: { color: '#8fa8c8', font: {size:12} }, position:'bottom' } }, cutout: '65%' }
      });
    }

    // ── CHART PRIORITÀ ──
    const pri = d.priorita_distribution;
    const ctxP = document.getElementById('chart-pri');
    if (ctxP) {
      charts.pri = new Chart(ctxP, {
        type: 'bar',
        data: {
          labels: ['Molto Alta','Alta','Media','Bassa'],
          datasets: [{ data: [pri.molto_Alta, pri.Alta, pri.Media, pri.Bassa],
            backgroundColor: ['#ff4d6a','#ff8c42','#ffd60a','#00e676'], borderRadius: 6, borderWidth: 0 }]
        },
        options: { plugins:{legend:{display:false}}, scales:{
          x:{ticks:{color:'#8fa8c8'},grid:{color:'#1c2f47'}},
          y:{ticks:{color:'#8fa8c8'},grid:{color:'#1c2f47'}}
        }}
      });
    }

    // ── CHART FINANZIARIO ──
    const mesi = d.andamento_finanziario;
    const ctxF = document.getElementById('chart-fin');
    if (ctxF) {
      charts.fin = new Chart(ctxF, {
        type: 'bar',
        data: {
          labels: mesi.map(m => m.mese),
          datasets: [
            { label:'Entrate', data: mesi.map(m=>m.entrate), backgroundColor:'#00e67666', borderRadius:6, borderWidth:0 },
            { label:'Uscite',  data: mesi.map(m=>m.uscite),  backgroundColor:'#ff4d6a66', borderRadius:6, borderWidth:0 }
          ]
        },
        options: {
          plugins:{ legend:{labels:{color:'#8fa8c8'}} },
          scales:{
            x:{ticks:{color:'#8fa8c8'},grid:{color:'#1c2f47'}},
            y:{ticks:{color:'#8fa8c8'},grid:{color:'#1c2f47'}}
          }
        }
      });
    }
  }

  return { load };
})();
