from flask import Blueprint, jsonify, request
from datetime import datetime, date
import db

bp = Blueprint("tasks", __name__)
FILE = "tasks.json"

PRIORITY_ORDER = {"molto_Alta": 0, "Alta": 1, "Media": 2, "Bassa": 3}

def days_until(s):
    if not s or s.strip() in ("", "9999-01-01"):
        return 9999
    try:
        d = datetime.strptime(s.strip(), "%Y-%m-%d").date()
        delta = (d - date.today()).days
        return delta if delta >= 0 else -1
    except:
        return 9999

def sort_key(t):
    g = t["_giorni"]
    if g == -1:   return (0, 0)
    if g <= 3:    return (1, g)
    if g != 9999: return (2, g)
    return (3, PRIORITY_ORDER.get(t.get("priorita","Media"), 2))

@bp.route("/api/tasks", methods=["GET"])
def get_tasks():
    db.invalidate(FILE)
    tasks, _ = db.read(FILE)
    stato_f = request.args.get("stato")
    pri_f   = request.args.get("priorita")
    result  = []
    for i, t in enumerate(tasks):
        if stato_f:
            if t.get("stato") != stato_f: continue
        else:
            if t.get("stato") in ("Completato","Falliti"): continue
        if pri_f and pri_f != "Tutti" and t.get("priorita") != pri_f: continue
        d = dict(t); d["_id"] = i; d["_giorni"] = days_until(t.get("scadenza",""))
        result.append(d)
    result.sort(key=sort_key)
    return jsonify(result)

@bp.route("/api/tasks/all", methods=["GET"])
def get_all_tasks():
    db.invalidate(FILE)
    tasks, _ = db.read(FILE)
    stato = request.args.get("stato")
    result = []
    for i, t in enumerate(tasks):
        if stato and t.get("stato") != stato: continue
        d = dict(t); d["_id"] = i; d["_giorni"] = days_until(t.get("scadenza",""))
        result.append(d)
    return jsonify(result)

@bp.route("/api/tasks", methods=["POST"])
def add_task():
    tasks, _ = db.read(FILE)
    data = request.json
    tasks.append({
        "nome":               data.get("nome","").strip(),
        "scadenza":           data.get("scadenza",""),
        "priorita":           data.get("priorita","Media"),
        "stato":              data.get("stato","Da Iniziare"),
        "note":               data.get("note",""),
        "data_creazione":     datetime.now().strftime("%Y-%m-%d"),
        "data_completamento": ""
    })
    return jsonify({"ok": db.write(FILE, tasks)})

@bp.route("/api/tasks/<int:idx>", methods=["PUT"])
def update_task(idx):
    tasks, _ = db.read(FILE)
    if idx < 0 or idx >= len(tasks): return jsonify({"ok":False}), 404
    data = request.json
    t = tasks[idx]
    t.update({k: data[k] for k in ("nome","scadenza","priorita","stato","note") if k in data})
    if t["stato"] == "Completato" and not t.get("data_completamento"):
        t["data_completamento"] = datetime.now().strftime("%Y-%m-%d")
    if t["stato"] in ("Da Iniziare","In Progresso"):
        t["data_completamento"] = ""
    return jsonify({"ok": db.write(FILE, tasks)})

@bp.route("/api/tasks/<int:idx>", methods=["DELETE"])
def delete_task(idx):
    tasks, _ = db.read(FILE)
    if idx < 0 or idx >= len(tasks): return jsonify({"ok":False}), 404
    tasks.pop(idx)
    return jsonify({"ok": db.write(FILE, tasks)})

@bp.route("/api/tasks/<int:idx>/stato", methods=["PATCH"])
def set_stato(idx):
    tasks, _ = db.read(FILE)
    if idx < 0 or idx >= len(tasks): return jsonify({"ok":False}), 404
    nuovo = request.json.get("stato")
    tasks[idx]["stato"] = nuovo
    if nuovo in ("Completato","Falliti"):
        tasks[idx]["data_completamento"] = datetime.now().strftime("%Y-%m-%d")
    else:
        tasks[idx]["data_completamento"] = ""
    return jsonify({"ok": db.write(FILE, tasks)})
