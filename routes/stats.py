from flask import Blueprint, jsonify
from datetime import datetime, date, timedelta
import db

bp = Blueprint("stats", __name__)

def somme(trans, mese):
    e = u = 0.0
    for t in trans:
        if t.get("data","").startswith(mese):
            if t.get("tipo") == "Entrata": e += float(t.get("importo",0))
            elif t.get("tipo") == "Uscita": u += float(t.get("importo",0))
    return {"mese": mese, "entrate": e, "uscite": u, "saldo": e - u}

@bp.route("/api/stats", methods=["GET"])
def get_stats():
    tasks,   _ = db.read("tasks.json")
    finanze, _ = db.read("finanze.json")
    notes,   _ = db.read("appunti.json")

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
                    giorni = (d - today).days
                    if giorni <= 3:
                        urgenti.append({"nome": t.get("nome",""), "scadenza": scad, "giorni": giorni})
                except: pass

    oggi = datetime.now()
    mesi_fin = []
    for i in range(6):
        m = oggi.replace(day=1) - timedelta(days=30*i)
        mesi_fin.append(somme(finanze, m.strftime("%Y-%m")))
    mesi_fin.reverse()

    completati_per_giorno = {}
    for t in tasks:
        if t.get("stato") == "Completato" and t.get("data_completamento"):
            ds = t["data_completamento"][:10]
            completati_per_giorno[ds] = completati_per_giorno.get(ds,0) + 1

    # Priorità distribution
    pri_dist = {"molto_Alta":0,"Alta":0,"Media":0,"Bassa":0}
    for t in tasks:
        if t.get("stato") not in ("Completato","Falliti"):
            p = t.get("priorita","Media")
            if p in pri_dist: pri_dist[p] += 1

    return jsonify({
        "tasks": {
            "totale": totale, "completati": completati, "falliti": falliti,
            "in_progresso": in_prog, "da_iniziare": da_iniziare,
            "urgenti": urgenti,
            "percentuale": round(completati/totale*100) if totale else 0
        },
        "note": len(notes),
        "finanze_mese": somme(finanze, oggi.strftime("%Y-%m")),
        "completati_per_giorno": completati_per_giorno,
        "andamento_finanziario": mesi_fin,
        "priorita_distribution": pri_dist
    })
