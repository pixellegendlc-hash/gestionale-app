"""
Gestionale Mobile - Backend Flask
Dati salvati su GitHub (repository privato)
"""

from flask import Flask, jsonify, request, render_template
from datetime import datetime, date, timedelta
import json, os, base64, requests

app = Flask(__name__)

# ─────────────────────────────────────────────
# CONFIGURAZIONE GITHUB
# Queste variabili vengono impostate su Render
# ─────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "")   # il tuo username GitHub
GITHUB_REPO  = os.environ.get("GITHUB_REPO",  "")   # nome del repo dati

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

FILES = {
    "tasks":   "tasks.json",
    "finanze": "finanze.json",
    "appunti": "appunti.json"
}

# Cache in memoria per ridurre chiamate API
_cache = {}

# ─────────────────────────────────────────────
# GITHUB HELPERS
# ─────────────────────────────────────────────
def gh_read(filename):
    """Legge un file dal repository GitHub"""
    if filename in _cache:
        return _cache[filename]["data"], _cache[filename]["sha"]
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{filename}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 404:
        return [], None
    if res.status_code != 200:
        print(f"Errore lettura {filename}: {res.status_code} {res.text}")
        return [], None
    body = res.json()
    content = json.loads(base64.b64decode(body["content"]).decode("utf-8"))
    sha = body["sha"]
    _cache[filename] = {"data": content, "sha": sha}
    return content, sha

def gh_write(filename, data):
    """Scrive un file sul repository GitHub"""
    _, sha = gh_read(filename)
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{filename}"
    content_b64 = base64.b64encode(
        json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")
    payload = {
        "message": f"update {filename}",
        "content": content_b64
    }
    if sha:
        payload["sha"] = sha
    res = requests.put(url, headers=HEADERS, json=payload)
    if res.status_code in (200, 201):
        new_sha = res.json()["content"]["sha"]
        _cache[filename] = {"data": data, "sha": new_sha}
        return True
    print(f"Errore scrittura {filename}: {res.status_code} {res.text}")
    return False

def invalidate(filename):
    """Invalida la cache per forzare rilettura da GitHub"""
    _cache.pop(filename, None)

# ─────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────
def days_until(scadenza_str):
    if not scadenza_str or scadenza_str.strip() in ("", "9999-01-01"):
        return 9999
    try:
        scad = datetime.strptime(scadenza_str.strip(), "%Y-%m-%d").date()
        delta = (scad - date.today()).days
        return delta if delta >= 0 else -1
    except ValueError:
        return 9999

def calcola_somme(transazioni, mese_anno=None):
    if mese_anno is None:
        mese_anno = datetime.now().strftime("%Y-%m")
    entrate = uscite = 0.0
    for t in transazioni:
        if t.get("data", "").startswith(mese_anno):
            if t.get("tipo") == "Entrata":
                entrate += float(t.get("importo", 0))
            elif t.get("tipo") == "Uscita":
                uscite  += float(t.get("importo", 0))
    return {"mese": mese_anno, "entrate": entrate, "uscite": uscite, "saldo": entrate - uscite}

# ─────────────────────────────────────────────
# PAGINA PRINCIPALE
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# ═══════════════════════════════════════════════
# API TASK
# ═══════════════════════════════════════════════
@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    invalidate(FILES["tasks"])
    tasks, _ = gh_read(FILES["tasks"])
    stato_filter    = request.args.get("stato")
    priorita_filter = request.args.get("priorita")

    result = []
    for i, t in enumerate(tasks):
        if stato_filter:
            if t.get("stato") != stato_filter:
                continue
        else:
            if t.get("stato") in ("Completato", "Falliti"):
                continue
        if priorita_filter and priorita_filter != "Tutti" and t.get("priorita") != priorita_filter:
            continue
        d = dict(t)
        d["_id"] = i
        d["_giorni"] = days_until(t.get("scadenza", ""))
        result.append(d)

    def sort_key(t):
        g = t["_giorni"]
        if g == -1:   return (0, 0)
        if g <= 3:    return (1, g)
        if g != 9999: return (2, g)
        return (3, 0)

    result.sort(key=sort_key)
    return jsonify(result)

@app.route("/api/tasks/all", methods=["GET"])
def get_all_tasks():
    invalidate(FILES["tasks"])
    tasks, _ = gh_read(FILES["tasks"])
    stato = request.args.get("stato")
    result = []
    for i, t in enumerate(tasks):
        if stato and t.get("stato") != stato:
            continue
        d = dict(t); d["_id"] = i
        result.append(d)
    return jsonify(result)

@app.route("/api/tasks", methods=["POST"])
def add_task():
    tasks, _ = gh_read(FILES["tasks"])
    data = request.json
    tasks.append({
        "nome":               data.get("nome", ""),
        "assegnato_a":        data.get("assegnato_a", "N/D"),
        "scadenza":           data.get("scadenza", ""),
        "priorita":           data.get("priorita", "Media"),
        "stato":              data.get("stato", "Da Iniziare"),
        "data_completamento": ""
    })
    ok = gh_write(FILES["tasks"], tasks)
    return jsonify({"ok": ok})

@app.route("/api/tasks/<int:idx>", methods=["PUT"])
def update_task(idx):
    tasks, _ = gh_read(FILES["tasks"])
    if idx < 0 or idx >= len(tasks):
        return jsonify({"ok": False}), 404
    data = request.json
    tasks[idx].update({
        "nome":        data.get("nome",        tasks[idx].get("nome")),
        "assegnato_a": data.get("assegnato_a", tasks[idx].get("assegnato_a")),
        "scadenza":    data.get("scadenza",    tasks[idx].get("scadenza")),
        "priorita":    data.get("priorita",    tasks[idx].get("priorita")),
        "stato":       data.get("stato",       tasks[idx].get("stato")),
    })
    if tasks[idx]["stato"] == "Completato" and not tasks[idx].get("data_completamento"):
        tasks[idx]["data_completamento"] = datetime.now().strftime("%Y-%m-%d")
    ok = gh_write(FILES["tasks"], tasks)
    return jsonify({"ok": ok})

@app.route("/api/tasks/<int:idx>", methods=["DELETE"])
def delete_task(idx):
    tasks, _ = gh_read(FILES["tasks"])
    if idx < 0 or idx >= len(tasks):
        return jsonify({"ok": False}), 404
    tasks.pop(idx)
    ok = gh_write(FILES["tasks"], tasks)
    return jsonify({"ok": ok})

@app.route("/api/tasks/<int:idx>/stato", methods=["PATCH"])
def set_task_stato(idx):
    tasks, _ = gh_read(FILES["tasks"])
    if idx < 0 or idx >= len(tasks):
        return jsonify({"ok": False}), 404
    nuovo_stato = request.json.get("stato")
    tasks[idx]["stato"] = nuovo_stato
    if nuovo_stato in ("Completato", "Falliti"):
        tasks[idx]["data_completamento"] = datetime.now().strftime("%Y-%m-%d")
    else:
        tasks[idx]["data_completamento"] = ""
    ok = gh_write(FILES["tasks"], tasks)
    return jsonify({"ok": ok})

# ═══════════════════════════════════════════════
# API FINANZE
# ═══════════════════════════════════════════════
@app.route("/api/finanze", methods=["GET"])
def get_finanze():
    invalidate(FILES["finanze"])
    finanze, _ = gh_read(FILES["finanze"])
    tipo = request.args.get("tipo")
    result = []
    for i, f in enumerate(finanze):
        if tipo and tipo != "Tutti" and f.get("tipo") != tipo:
            continue
        d = dict(f); d["_id"] = i
        result.append(d)
    result.sort(key=lambda x: x.get("data",""), reverse=True)
    return jsonify(result)

@app.route("/api/finanze/riepilogo", methods=["GET"])
def get_riepilogo():
    finanze, _ = gh_read(FILES["finanze"])
    oggi = datetime.now()
    mesi = []
    for i in range(6):
        m = oggi.replace(day=1) - timedelta(days=30*i)
        mesi.append(calcola_somme(finanze, m.strftime("%Y-%m")))
    mesi.reverse()
    return jsonify({"mese_corrente": calcola_somme(finanze), "ultimi_6_mesi": mesi})

@app.route("/api/finanze", methods=["POST"])
def add_finanza():
    finanze, _ = gh_read(FILES["finanze"])
    data = request.json
    finanze.append({
        "descrizione": data.get("descrizione", ""),
        "data":        data.get("data", datetime.now().strftime("%Y-%m-%d")),
        "tipo":        data.get("tipo", "Uscita"),
        "importo":     float(data.get("importo", 0))
    })
    ok = gh_write(FILES["finanze"], finanze)
    return jsonify({"ok": ok})

@app.route("/api/finanze/<int:idx>", methods=["DELETE"])
def delete_finanza(idx):
    finanze, _ = gh_read(FILES["finanze"])
    if idx < 0 or idx >= len(finanze):
        return jsonify({"ok": False}), 404
    finanze.pop(idx)
    ok = gh_write(FILES["finanze"], finanze)
    return jsonify({"ok": ok})

# ═══════════════════════════════════════════════
# API APPUNTI
# ═══════════════════════════════════════════════
@app.route("/api/appunti", methods=["GET"])
def get_appunti():
    invalidate(FILES["appunti"])
    notes, _ = gh_read(FILES["appunti"])
    q = request.args.get("q", "").lower()
    result = []
    for i, n in enumerate(notes):
        if q and q not in n.get("titolo","").lower() and q not in n.get("contenuto","").lower():
            continue
        d = dict(n); d["_id"] = i
        d.pop("history", None)
        result.append(d)
    return jsonify(result)

@app.route("/api/appunti/<int:idx>", methods=["GET"])
def get_appunto(idx):
    notes, _ = gh_read(FILES["appunti"])
    if idx < 0 or idx >= len(notes):
        return jsonify({"ok": False}), 404
    d = dict(notes[idx]); d["_id"] = idx
    return jsonify(d)

@app.route("/api/appunti", methods=["POST"])
def add_appunto():
    notes, _ = gh_read(FILES["appunti"])
    data = request.json
    notes.append({
        "titolo":    data.get("titolo", ""),
        "contenuto": data.get("contenuto", ""),
        "data":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history":   []
    })
    ok = gh_write(FILES["appunti"], notes)
    return jsonify({"ok": ok, "id": len(notes)-1})

@app.route("/api/appunti/<int:idx>", methods=["PUT"])
def update_appunto(idx):
    notes, _ = gh_read(FILES["appunti"])
    if idx < 0 or idx >= len(notes):
        return jsonify({"ok": False}), 404
    data = request.json
    prev = dict(notes[idx])
    history = prev.pop("history", [])
    history.append({**prev, "date": prev.get("data","")})
    notes[idx]["titolo"]    = data.get("titolo",    notes[idx].get("titolo",""))
    notes[idx]["contenuto"] = data.get("contenuto", notes[idx].get("contenuto",""))
    notes[idx]["data"]      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notes[idx]["history"]   = history[-10:]
    ok = gh_write(FILES["appunti"], notes)
    return jsonify({"ok": ok})

@app.route("/api/appunti/<int:idx>", methods=["DELETE"])
def delete_appunto(idx):
    notes, _ = gh_read(FILES["appunti"])
    if idx < 0 or idx >= len(notes):
        return jsonify({"ok": False}), 404
    notes.pop(idx)
    ok = gh_write(FILES["appunti"], notes)
    return jsonify({"ok": ok})

# ═══════════════════════════════════════════════
# API STATS
# ═══════════════════════════════════════════════
@app.route("/api/stats", methods=["GET"])
def get_stats():
    tasks,   _ = gh_read(FILES["tasks"])
    finanze, _ = gh_read(FILES["finanze"])

    totale      = len(tasks)
    completati  = sum(1 for t in tasks if t.get("stato") == "Completato")
    falliti     = sum(1 for t in tasks if t.get("stato") == "Falliti")
    in_prog     = sum(1 for t in tasks if t.get("stato") == "In Progresso")
    da_iniziare = sum(1 for t in tasks if t.get("stato") == "Da Iniziare")

    today = date.today()
    urgenti = []
    for t in tasks:
        if t.get("stato") in ("Da Iniziare","In Progresso"):
            scad = t.get("scadenza","")
            if scad and scad != "9999-01-01":
                try:
                    d = datetime.strptime(scad,"%Y-%m-%d").date()
                    if (d - today).days <= 3:
                        urgenti.append({"nome": t.get("nome",""), "scadenza": scad, "giorni": (d-today).days})
                except: pass

    oggi = datetime.now()
    mesi = []
    for i in range(6):
        m = oggi.replace(day=1) - timedelta(days=30*i)
        mesi.append(calcola_somme(finanze, m.strftime("%Y-%m")))
    mesi.reverse()

    completati_per_giorno = {}
    for t in tasks:
        if t.get("stato") == "Completato" and t.get("data_completamento"):
            ds = t["data_completamento"][:10]
            completati_per_giorno[ds] = completati_per_giorno.get(ds,0) + 1

    return jsonify({
        "tasks": {
            "totale": totale, "completati": completati, "falliti": falliti,
            "in_progresso": in_prog, "da_iniziare": da_iniziare, "urgenti": urgenti
        },
        "completati_per_giorno": completati_per_giorno,
        "andamento_finanziario": mesi
    })

# ─────────────────────────────────────────────
# AVVIO
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
