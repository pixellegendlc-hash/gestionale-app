"""
Organizzatore - Backend Flask
"""
from flask import Flask, jsonify, request, render_template, send_file
from datetime import datetime, date, timedelta
import json, os, base64, requests, csv, io

app = Flask(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "")
GITHUB_REPO  = os.environ.get("GITHUB_REPO",  "")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

FILES = {
    "tasks":     "tasks.json",
    "finanze":   "finanze.json",
    "appunti":   "appunti.json",
    "foto_meta": "foto_meta.json",
}

_cache = {}

def gh_read(filename, force=False):
    if not force and filename in _cache:
        return _cache[filename]["data"], _cache[filename]["sha"]
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{filename}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 404:
        return [], None
    if res.status_code != 200:
        return [], None
    body = res.json()
    try:
        content = json.loads(base64.b64decode(body["content"]).decode("utf-8"))
    except:
        content = []
    sha = body["sha"]
    _cache[filename] = {"data": content, "sha": sha}
    return content, sha

def gh_write(filename, data):
    _, sha = gh_read(filename)
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{filename}"
    content_b64 = base64.b64encode(
        json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")
    payload = {"message": f"update {filename}", "content": content_b64}
    if sha:
        payload["sha"] = sha
    res = requests.put(url, headers=HEADERS, json=payload)
    if res.status_code in (200, 201):
        new_sha = res.json()["content"]["sha"]
        _cache[filename] = {"data": data, "sha": new_sha}
        return True
    return False

def gh_upload_image(path, image_b64):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    sha = res.json().get("sha") if res.status_code == 200 else None
    payload = {"message": f"upload {path}", "content": image_b64}
    if sha:
        payload["sha"] = sha
    res = requests.put(url, headers=HEADERS, json=payload)
    return res.status_code in (200, 201)

def gh_delete_file(path):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return False
    sha = res.json().get("sha")
    res = requests.delete(url, headers=HEADERS, json={"message": f"delete {path}", "sha": sha})
    return res.status_code == 200

def inv(f):
    _cache.pop(f, None)

def days_until(s):
    if not s or s.strip() in ("", "9999-01-01"):
        return 9999
    try:
        d = datetime.strptime(s.strip(), "%Y-%m-%d").date()
        delta = (d - date.today()).days
        return delta if delta >= 0 else -1
    except:
        return 9999

def calcola_somme(trans, mese=None):
    if not mese:
        mese = datetime.now().strftime("%Y-%m")
    e = u = 0.0
    for t in trans:
        if t.get("data", "").startswith(mese):
            if t.get("tipo") == "Entrata": e += float(t.get("importo", 0))
            elif t.get("tipo") == "Uscita": u += float(t.get("importo", 0))
    return {"mese": mese, "entrate": e, "uscite": u, "saldo": e - u}

@app.route("/")
def index():
    return render_template("index.html")

# ── DASHBOARD ──
@app.route("/api/dashboard")
def dashboard():
    inv(FILES["tasks"]); inv(FILES["finanze"])
    tasks, _   = gh_read(FILES["tasks"])
    finanze, _ = gh_read(FILES["finanze"])
    attivi     = [t for t in tasks if t.get("stato") not in ("Completato","Falliti")]
    completati = [t for t in tasks if t.get("stato") == "Completato"]
    urgenti = []
    for i, t in enumerate(attivi):
        g = days_until(t.get("scadenza",""))
        if g <= 3:
            urgenti.append({**t, "_id": tasks.index(t), "_giorni": g})
    urgenti.sort(key=lambda x: x["_giorni"])
    mc = calcola_somme(finanze)
    return jsonify({
        "task_attivi": len(attivi), "task_completati": len(completati),
        "task_urgenti": len(urgenti), "urgenti": urgenti[:5],
        "finanze_mese": mc
    })

# ── SEARCH ──
@app.route("/api/search")
def search():
    q = request.args.get("q","").lower().strip()
    if not q:
        return jsonify([])
    tasks,   _ = gh_read(FILES["tasks"])
    finanze, _ = gh_read(FILES["finanze"])
    notes,   _ = gh_read(FILES["appunti"])
    results = []
    for i, t in enumerate(tasks):
        if q in t.get("nome","").lower() or q in t.get("note","").lower() or q in t.get("categoria","").lower():
            results.append({"tipo":"task","id":i,"titolo":t.get("nome",""),"sub":t.get("stato",""),"priorita":t.get("priorita","")})
    for i, f in enumerate(finanze):
        if q in f.get("descrizione","").lower() or q in f.get("categoria","").lower():
            results.append({"tipo":"finanza","id":i,"titolo":f.get("descrizione",""),"sub":f"{'+' if f.get('tipo')=='Entrata' else '-'}€{float(f.get('importo',0)):.2f}"})
    for i, n in enumerate(notes):
        if q in n.get("titolo","").lower() or q in n.get("contenuto","").lower():
            results.append({"tipo":"appunto","id":i,"titolo":n.get("titolo",""),"sub":n.get("data","")[:10]})
    return jsonify(results[:20])

# ── TASK ──
@app.route("/api/tasks")
def get_tasks():
    inv(FILES["tasks"])
    tasks, _ = gh_read(FILES["tasks"])
    stato_f = request.args.get("stato")
    prio_f  = request.args.get("priorita")
    cat_f   = request.args.get("categoria")
    result = []
    for i, t in enumerate(tasks):
        if stato_f:
            if t.get("stato") != stato_f: continue
        else:
            if t.get("stato") in ("Completato","Falliti"): continue
        if prio_f and prio_f != "Tutti" and t.get("priorita") != prio_f: continue
        if cat_f and cat_f != "Tutti" and t.get("categoria","") != cat_f: continue
        d = dict(t); d["_id"] = i; d["_giorni"] = days_until(t.get("scadenza",""))
        result.append(d)
    def sk(t):
        g = t["_giorni"]
        if g == -1: return (0,0)
        if g <= 3:  return (1,g)
        if g != 9999: return (2,g)
        return (3,0)
    result.sort(key=sk)
    return jsonify(result)

@app.route("/api/tasks/all")
def get_all_tasks():
    inv(FILES["tasks"])
    tasks, _ = gh_read(FILES["tasks"])
    stato = request.args.get("stato")
    result = []
    for i, t in enumerate(tasks):
        if stato and t.get("stato") != stato: continue
        d = dict(t); d["_id"] = i
        result.append(d)
    return jsonify(result)

@app.route("/api/tasks/categorie")
def get_categorie():
    tasks, _ = gh_read(FILES["tasks"])
    cats = list(set(t.get("categoria","") for t in tasks if t.get("categoria","")))
    return jsonify(sorted(cats))

@app.route("/api/tasks/scadenzario")
def scadenzario():
    inv(FILES["tasks"])
    tasks, _ = gh_read(FILES["tasks"])
    result = {}
    for i, t in enumerate(tasks):
        if t.get("stato") in ("Completato","Falliti"): continue
        scad = t.get("scadenza","")
        if not scad or scad == "9999-01-01": continue
        if scad not in result: result[scad] = []
        result[scad].append({**t, "_id": i, "_giorni": days_until(scad)})
    return jsonify(result)

@app.route("/api/tasks", methods=["POST"])
def add_task():
    tasks, _ = gh_read(FILES["tasks"])
    d = request.json
    tasks.append({
        "nome":               d.get("nome",""),
        "scadenza":           d.get("scadenza",""),
        "priorita":           d.get("priorita","Media"),
        "stato":              d.get("stato","Da Iniziare"),
        "note":               d.get("note",""),
        "categoria":          d.get("categoria",""),
        "data_creazione":     datetime.now().strftime("%Y-%m-%d"),
        "data_completamento": ""
    })
    return jsonify({"ok": gh_write(FILES["tasks"], tasks)})

@app.route("/api/tasks/<int:idx>", methods=["PUT"])
def update_task(idx):
    tasks, _ = gh_read(FILES["tasks"])
    if idx < 0 or idx >= len(tasks): return jsonify({"ok": False}), 404
    d = request.json
    for k in ("nome","scadenza","priorita","stato","note","categoria"):
        if k in d: tasks[idx][k] = d[k]
    if tasks[idx]["stato"] == "Completato" and not tasks[idx].get("data_completamento"):
        tasks[idx]["data_completamento"] = datetime.now().strftime("%Y-%m-%d")
    return jsonify({"ok": gh_write(FILES["tasks"], tasks)})

@app.route("/api/tasks/<int:idx>", methods=["DELETE"])
def delete_task(idx):
    tasks, _ = gh_read(FILES["tasks"])
    if idx < 0 or idx >= len(tasks): return jsonify({"ok": False}), 404
    tasks.pop(idx)
    return jsonify({"ok": gh_write(FILES["tasks"], tasks)})

@app.route("/api/tasks/<int:idx>/stato", methods=["PATCH"])
def set_stato(idx):
    tasks, _ = gh_read(FILES["tasks"])
    if idx < 0 or idx >= len(tasks): return jsonify({"ok": False}), 404
    s = request.json.get("stato")
    tasks[idx]["stato"] = s
    tasks[idx]["data_completamento"] = datetime.now().strftime("%Y-%m-%d") if s in ("Completato","Falliti") else ""
    return jsonify({"ok": gh_write(FILES["tasks"], tasks)})

# ── FINANZE ──
@app.route("/api/finanze")
def get_finanze():
    inv(FILES["finanze"])
    finanze, _ = gh_read(FILES["finanze"])
    tipo = request.args.get("tipo")
    result = []
    for i, f in enumerate(finanze):
        if tipo and tipo != "Tutti" and f.get("tipo") != tipo: continue
        d = dict(f); d["_id"] = i
        result.append(d)
    result.sort(key=lambda x: x.get("data",""), reverse=True)
    return jsonify(result)

@app.route("/api/finanze/riepilogo")
def riepilogo():
    finanze, _ = gh_read(FILES["finanze"])
    oggi = datetime.now()
    mesi = []
    for i in range(6):
        m = oggi.replace(day=1) - timedelta(days=30*i)
        mesi.append(calcola_somme(finanze, m.strftime("%Y-%m")))
    mesi.reverse()
    # Spese per categoria mese corrente
    cat_spese = {}
    mese = oggi.strftime("%Y-%m")
    for f in finanze:
        if f.get("data","").startswith(mese) and f.get("tipo") == "Uscita":
            cat = f.get("categoria","Altro")
            cat_spese[cat] = cat_spese.get(cat, 0) + float(f.get("importo",0))
    return jsonify({"mese_corrente": calcola_somme(finanze), "ultimi_6_mesi": mesi, "spese_categoria": cat_spese})

@app.route("/api/finanze", methods=["POST"])
def add_finanza():
    finanze, _ = gh_read(FILES["finanze"])
    d = request.json
    finanze.append({
        "descrizione": d.get("descrizione",""),
        "data":        d.get("data", datetime.now().strftime("%Y-%m-%d")),
        "tipo":        d.get("tipo","Uscita"),
        "importo":     float(d.get("importo",0)),
        "categoria":   d.get("categoria","Altro")
    })
    return jsonify({"ok": gh_write(FILES["finanze"], finanze)})

@app.route("/api/finanze/<int:idx>", methods=["DELETE"])
def delete_finanza(idx):
    finanze, _ = gh_read(FILES["finanze"])
    if idx < 0 or idx >= len(finanze): return jsonify({"ok": False}), 404
    finanze.pop(idx)
    return jsonify({"ok": gh_write(FILES["finanze"], finanze)})

# ── APPUNTI ──
@app.route("/api/appunti")
def get_appunti():
    inv(FILES["appunti"])
    notes, _ = gh_read(FILES["appunti"])
    q = request.args.get("q","").lower()
    result = []
    for i, n in enumerate(notes):
        if q and q not in n.get("titolo","").lower() and q not in n.get("contenuto","").lower(): continue
        d = {k:v for k,v in n.items() if k != "history"}
        d["_id"] = i
        result.append(d)
    result.sort(key=lambda x: (not x.get("pinned",False), x.get("data","")), reverse=True)
    return jsonify(result)

@app.route("/api/appunti/<int:idx>")
def get_appunto(idx):
    notes, _ = gh_read(FILES["appunti"])
    if idx < 0 or idx >= len(notes): return jsonify({"ok": False}), 404
    d = dict(notes[idx]); d["_id"] = idx
    return jsonify(d)

@app.route("/api/appunti", methods=["POST"])
def add_appunto():
    notes, _ = gh_read(FILES["appunti"])
    d = request.json
    notes.append({
        "titolo":    d.get("titolo",""),
        "contenuto": d.get("contenuto",""),
        "data":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pinned":    False,
        "history":   []
    })
    return jsonify({"ok": gh_write(FILES["appunti"], notes), "id": len(notes)-1})

@app.route("/api/appunti/<int:idx>", methods=["PUT"])
def update_appunto(idx):
    notes, _ = gh_read(FILES["appunti"])
    if idx < 0 or idx >= len(notes): return jsonify({"ok": False}), 404
    d = request.json
    prev = dict(notes[idx])
    history = prev.pop("history", [])
    history.append({**prev, "date": prev.get("data","")})
    notes[idx].update({
        "titolo":    d.get("titolo",    notes[idx].get("titolo","")),
        "contenuto": d.get("contenuto", notes[idx].get("contenuto","")),
        "data":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history":   history[-10:]
    })
    return jsonify({"ok": gh_write(FILES["appunti"], notes)})

@app.route("/api/appunti/<int:idx>/pin", methods=["PATCH"])
def pin_appunto(idx):
    notes, _ = gh_read(FILES["appunti"])
    if idx < 0 or idx >= len(notes): return jsonify({"ok": False}), 404
    notes[idx]["pinned"] = not notes[idx].get("pinned", False)
    return jsonify({"ok": gh_write(FILES["appunti"], notes), "pinned": notes[idx]["pinned"]})

@app.route("/api/appunti/<int:idx>", methods=["DELETE"])
def delete_appunto(idx):
    notes, _ = gh_read(FILES["appunti"])
    if idx < 0 or idx >= len(notes): return jsonify({"ok": False}), 404
    notes.pop(idx)
    return jsonify({"ok": gh_write(FILES["appunti"], notes)})

# ── FOTO ──
@app.route("/api/foto")
def get_foto():
    inv(FILES["foto_meta"])
    meta, _ = gh_read(FILES["foto_meta"])
    gruppo = request.args.get("gruppo")
    if gruppo and gruppo != "Tutti":
        meta = [f for f in meta if f.get("gruppo") == gruppo]
    return jsonify(meta if isinstance(meta, list) else [])

@app.route("/api/foto/gruppi")
def get_gruppi():
    meta, _ = gh_read(FILES["foto_meta"])
    gruppi = list(set(f.get("gruppo","Senza gruppo") for f in (meta if isinstance(meta,list) else [])))
    return jsonify(["Tutti"] + sorted(gruppi))

@app.route("/api/foto", methods=["POST"])
def upload_foto():
    meta, _ = gh_read(FILES["foto_meta"])
    if not isinstance(meta, list): meta = []
    d = request.json
    name    = d.get("name","foto.jpg").replace(" ","_")
    b64data = d.get("data","")
    gruppo  = d.get("gruppo","Senza gruppo")
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename= f"foto/{ts}_{name}"
    ok = gh_upload_image(filename, b64data)
    if ok:
        meta.append({
            "id":     ts,
            "name":   name,
            "path":   filename,
            "gruppo": gruppo,
            "data":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url":    f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/{filename}"
        })
        gh_write(FILES["foto_meta"], meta)
    return jsonify({"ok": ok})

@app.route("/api/foto/<foto_id>", methods=["DELETE"])
def delete_foto(foto_id):
    meta, _ = gh_read(FILES["foto_meta"])
    if not isinstance(meta, list): return jsonify({"ok": False})
    foto = next((f for f in meta if f.get("id") == foto_id), None)
    if not foto: return jsonify({"ok": False}), 404
    gh_delete_file(foto["path"])
    meta = [f for f in meta if f.get("id") != foto_id]
    return jsonify({"ok": gh_write(FILES["foto_meta"], meta)})

# ── STATS ──
@app.route("/api/stats")
def stats():
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
            g = days_until(t.get("scadenza",""))
            if g <= 3:
                urgenti.append({"nome": t.get("nome",""), "scadenza": t.get("scadenza",""), "giorni": g})
    oggi = datetime.now()
    mesi = []
    for i in range(6):
        m = oggi.replace(day=1) - timedelta(days=30*i)
        mesi.append(calcola_somme(finanze, m.strftime("%Y-%m")))
    mesi.reverse()
    prio = {"molto_Alta":0,"Alta":0,"Media":0,"Bassa":0}
    for t in tasks:
        if t.get("stato") not in ("Completato","Falliti"):
            p = t.get("priorita","Media")
            if p in prio: prio[p] += 1
    cat_spese = {}
    mese = oggi.strftime("%Y-%m")
    for f in finanze:
        if f.get("data","").startswith(mese) and f.get("tipo") == "Uscita":
            cat = f.get("categoria","Altro")
            cat_spese[cat] = cat_spese.get(cat,0) + float(f.get("importo",0))
    return jsonify({
        "tasks": {"totale":totale,"completati":completati,"falliti":falliti,
                  "in_progresso":in_prog,"da_iniziare":da_iniziare,"urgenti":urgenti},
        "priorita": prio, "andamento_finanziario": mesi, "spese_categoria": cat_spese
    })

# ── EXPORT ──
@app.route("/api/export/tasks/csv")
def export_tasks_csv():
    tasks, _ = gh_read(FILES["tasks"])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Nome","Scadenza","Priorità","Stato","Categoria","Note","Data Completamento"])
    for t in tasks:
        w.writerow([t.get("nome",""),t.get("scadenza",""),t.get("priorita",""),
                    t.get("stato",""),t.get("categoria",""),t.get("note",""),t.get("data_completamento","")])
    out.seek(0)
    return send_file(io.BytesIO(out.getvalue().encode("utf-8")), mimetype="text/csv",
                     as_attachment=True, download_name=f"task_{date.today()}.csv")

@app.route("/api/export/finanze/csv")
def export_finanze_csv():
    finanze, _ = gh_read(FILES["finanze"])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Descrizione","Data","Tipo","Importo","Categoria"])
    for f in finanze:
        w.writerow([f.get("descrizione",""),f.get("data",""),f.get("tipo",""),
                    f.get("importo",""),f.get("categoria","")])
    out.seek(0)
    return send_file(io.BytesIO(out.getvalue().encode("utf-8")), mimetype="text/csv",
                     as_attachment=True, download_name=f"finanze_{date.today()}.csv")

@app.route("/api/export/tasks/pdf")
def export_tasks_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        tasks, _ = gh_read(FILES["tasks"])
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        styles = getSampleStyleSheet()
        els = [Paragraph("Organizzatore — Task", styles["Title"]), Spacer(1,12)]
        data = [["Nome","Scadenza","Priorità","Stato","Categoria"]]
        for t in tasks:
            data.append([t.get("nome",""),t.get("scadenza",""),t.get("priorita",""),t.get("stato",""),t.get("categoria","")])
        tbl = Table(data, colWidths=[180,70,70,80,60])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e1b4b")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
            ("FONTSIZE",(0,0),(-1,-1),9),("PADDING",(0,0),(-1,-1),6),
        ]))
        els.append(tbl)
        doc.build(els)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=f"task_{date.today()}.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/finanze/pdf")
def export_finanze_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        finanze, _ = gh_read(FILES["finanze"])
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        styles = getSampleStyleSheet()
        mc = calcola_somme(finanze)
        els = [
            Paragraph("Organizzatore — Finanze", styles["Title"]), Spacer(1,6),
            Paragraph(f"Mese corrente: Entrate €{mc['entrate']:.2f} | Uscite €{mc['uscite']:.2f} | Saldo €{mc['saldo']:.2f}", styles["Normal"]),
            Spacer(1,12)
        ]
        data = [["Descrizione","Data","Tipo","Importo","Categoria"]]
        for f in finanze:
            data.append([f.get("descrizione",""),f.get("data",""),f.get("tipo",""),f"€{float(f.get('importo',0)):.2f}",f.get("categoria","")])
        tbl = Table(data, colWidths=[160,70,60,70,80])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e1b4b")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
            ("FONTSIZE",(0,0),(-1,-1),9),("PADDING",(0,0),(-1,-1),6),
        ]))
        els.append(tbl)
        doc.build(els)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=f"finanze_{date.today()}.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── IMPORT ──
@app.route("/api/import/tasks", methods=["POST"])
def import_tasks():
    try:
        content = request.json.get("csv","")
        reader = csv.DictReader(io.StringIO(content))
        tasks, _ = gh_read(FILES["tasks"])
        count = 0
        for row in reader:
            nome = row.get("Nome", row.get("nome","")).strip()
            if not nome: continue
            tasks.append({
                "nome": nome, "scadenza": row.get("Scadenza", row.get("scadenza","")),
                "priorita": row.get("Priorità", row.get("priorita","Media")),
                "stato": row.get("Stato", row.get("stato","Da Iniziare")),
                "note": row.get("Note", row.get("note","")),
                "categoria": row.get("Categoria", row.get("categoria","")),
                "data_creazione": datetime.now().strftime("%Y-%m-%d"), "data_completamento": ""
            })
            count += 1
        gh_write(FILES["tasks"], tasks)
        return jsonify({"ok": True, "importati": count})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/import/finanze", methods=["POST"])
def import_finanze():
    try:
        content = request.json.get("csv","")
        reader = csv.DictReader(io.StringIO(content))
        finanze, _ = gh_read(FILES["finanze"])
        count = 0
        for row in reader:
            desc = row.get("Descrizione", row.get("descrizione","")).strip()
            if not desc: continue
            finanze.append({
                "descrizione": desc,
                "data": row.get("Data", row.get("data", datetime.now().strftime("%Y-%m-%d"))),
                "tipo": row.get("Tipo", row.get("tipo","Uscita")),
                "importo": float(row.get("Importo", row.get("importo",0)) or 0),
                "categoria": row.get("Categoria", row.get("categoria","Altro"))
            })
            count += 1
        gh_write(FILES["finanze"], finanze)
        return jsonify({"ok": True, "importati": count})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── BACKUP ──
@app.route("/api/backup")
def backup():
    tasks,   _ = gh_read(FILES["tasks"])
    finanze, _ = gh_read(FILES["finanze"])
    notes,   _ = gh_read(FILES["appunti"])
    foto,    _ = gh_read(FILES["foto_meta"])
    data = {"timestamp": datetime.now().isoformat(), "tasks": tasks,
            "finanze": finanze, "appunti": notes, "foto_meta": foto if isinstance(foto,list) else []}
    buf = io.BytesIO(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
    return send_file(buf, mimetype="application/json", as_attachment=True,
                     download_name=f"backup_organizzatore_{date.today()}.json")

@app.route("/api/restore", methods=["POST"])
def restore():
    try:
        data = request.json
        if "tasks"   in data: gh_write(FILES["tasks"],   data["tasks"])
        if "finanze" in data: gh_write(FILES["finanze"], data["finanze"])
        if "appunti" in data: gh_write(FILES["appunti"], data["appunti"])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
