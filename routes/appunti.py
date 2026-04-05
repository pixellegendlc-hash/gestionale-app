from flask import Blueprint, jsonify, request
from datetime import datetime
import db

bp = Blueprint("appunti", __name__)
FILE = "appunti.json"

@bp.route("/api/appunti", methods=["GET"])
def get_appunti():
    db.invalidate(FILE)
    notes, _ = db.read(FILE)
    q = request.args.get("q","").lower()
    result = []
    for i, n in enumerate(notes):
        if q and q not in n.get("titolo","").lower() and q not in n.get("contenuto","").lower(): continue
        d = {k: v for k,v in n.items() if k != "history"}
        d["_id"] = i
        result.append(d)
    result.sort(key=lambda x: x.get("data",""), reverse=True)
    return jsonify(result)

@bp.route("/api/appunti/<int:idx>", methods=["GET"])
def get_appunto(idx):
    notes, _ = db.read(FILE)
    if idx < 0 or idx >= len(notes): return jsonify({"ok":False}), 404
    d = dict(notes[idx]); d["_id"] = idx
    return jsonify(d)

@bp.route("/api/appunti", methods=["POST"])
def add_appunto():
    notes, _ = db.read(FILE)
    data = request.json
    notes.append({
        "titolo":    data.get("titolo","").strip(),
        "contenuto": data.get("contenuto",""),
        "colore":    data.get("colore","default"),
        "data":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history":   []
    })
    ok = db.write(FILE, notes)
    return jsonify({"ok": ok, "id": len(notes)-1})

@bp.route("/api/appunti/<int:idx>", methods=["PUT"])
def update_appunto(idx):
    notes, _ = db.read(FILE)
    if idx < 0 or idx >= len(notes): return jsonify({"ok":False}), 404
    data = request.json
    prev = dict(notes[idx])
    history = prev.pop("history", [])
    history.append({**prev, "date": prev.get("data","")})
    notes[idx].update({k: data[k] for k in ("titolo","contenuto","colore") if k in data})
    notes[idx]["data"]    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notes[idx]["history"] = history[-20:]
    return jsonify({"ok": db.write(FILE, notes)})

@bp.route("/api/appunti/<int:idx>", methods=["DELETE"])
def delete_appunto(idx):
    notes, _ = db.read(FILE)
    if idx < 0 or idx >= len(notes): return jsonify({"ok":False}), 404
    notes.pop(idx)
    return jsonify({"ok": db.write(FILE, notes)})
