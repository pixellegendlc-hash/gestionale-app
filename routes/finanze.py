from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import db

bp = Blueprint("finanze", __name__)
FILE = "finanze.json"

def somme(trans, mese=None):
    mese = mese or datetime.now().strftime("%Y-%m")
    e = u = 0.0
    for t in trans:
        if t.get("data","").startswith(mese):
            if t.get("tipo") == "Entrata": e += float(t.get("importo",0))
            elif t.get("tipo") == "Uscita": u += float(t.get("importo",0))
    return {"mese": mese, "entrate": e, "uscite": u, "saldo": e - u}

@bp.route("/api/finanze", methods=["GET"])
def get_finanze():
    db.invalidate(FILE)
    fin, _ = db.read(FILE)
    tipo = request.args.get("tipo")
    mese = request.args.get("mese")
    result = []
    for i, f in enumerate(fin):
        if tipo and tipo != "Tutti" and f.get("tipo") != tipo: continue
        if mese and not f.get("data","").startswith(mese): continue
        d = dict(f); d["_id"] = i
        result.append(d)
    result.sort(key=lambda x: x.get("data",""), reverse=True)
    return jsonify(result)

@bp.route("/api/finanze/riepilogo", methods=["GET"])
def riepilogo():
    fin, _ = db.read(FILE)
    oggi = datetime.now()
    mesi = []
    for i in range(6):
        m = oggi.replace(day=1) - timedelta(days=30*i)
        mesi.append(somme(fin, m.strftime("%Y-%m")))
    mesi.reverse()
    
    # Tutti i mesi disponibili
    mesi_disp = sorted(set(f["data"][:7] for f in fin if f.get("data")), reverse=True)
    riepiloghi = [somme(fin, m) for m in mesi_disp]
    
    return jsonify({
        "mese_corrente": somme(fin),
        "ultimi_6_mesi": mesi,
        "tutti_mesi": riepiloghi
    })

@bp.route("/api/finanze", methods=["POST"])
def add_finanza():
    fin, _ = db.read(FILE)
    data = request.json
    fin.append({
        "descrizione": data.get("descrizione","").strip(),
        "importo":     float(data.get("importo",0)),
        "tipo":        data.get("tipo","Uscita"),
        "categoria":   data.get("categoria","Altro"),
        "data":        data.get("data", datetime.now().strftime("%Y-%m-%d")),
        "note":        data.get("note","")
    })
    return jsonify({"ok": db.write(FILE, fin)})

@bp.route("/api/finanze/<int:idx>", methods=["PUT"])
def update_finanza(idx):
    fin, _ = db.read(FILE)
    if idx < 0 or idx >= len(fin): return jsonify({"ok":False}), 404
    data = request.json
    fin[idx].update({k: data[k] for k in ("descrizione","importo","tipo","categoria","data","note") if k in data})
    fin[idx]["importo"] = float(fin[idx]["importo"])
    return jsonify({"ok": db.write(FILE, fin)})

@bp.route("/api/finanze/<int:idx>", methods=["DELETE"])
def delete_finanza(idx):
    fin, _ = db.read(FILE)
    if idx < 0 or idx >= len(fin): return jsonify({"ok":False}), 404
    fin.pop(idx)
    return jsonify({"ok": db.write(FILE, fin)})
