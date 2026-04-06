from flask import Blueprint, jsonify, Response
from datetime import datetime
import csv, io
import db

bp = Blueprint("export", __name__)

@bp.route("/api/export/tasks", methods=["GET"])
def export_tasks():
    tasks, _ = db.read("tasks.json")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Nome","Scadenza","Priorità","Stato","Note","Data Completamento"])
    for t in tasks:
        w.writerow([t.get("nome",""), t.get("scadenza",""), t.get("priorita",""),
                    t.get("stato",""), t.get("note",""), t.get("data_completamento","")])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment;filename=tasks_{datetime.now().strftime('%Y%m%d')}.csv"})

@bp.route("/api/export/finanze", methods=["GET"])
def export_finanze():
    fin, _ = db.read("finanze.json")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Descrizione","Data","Tipo","Categoria","Importo","Note"])
    for f in fin:
        w.writerow([f.get("descrizione",""), f.get("data",""), f.get("tipo",""),
                    f.get("categoria",""), f.get("importo",""), f.get("note","")])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment;filename=finanze_{datetime.now().strftime('%Y%m%d')}.csv"})

@bp.route("/api/export/appunti", methods=["GET"])
def export_appunti():
    notes, _ = db.read("appunti.json")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Titolo","Contenuto","Data"])
    for n in notes:
        w.writerow([n.get("titolo",""), n.get("contenuto",""), n.get("data","")])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment;filename=appunti_{datetime.now().strftime('%Y%m%d')}.csv"})
