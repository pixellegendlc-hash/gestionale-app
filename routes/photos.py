from flask import Blueprint, jsonify, request
import db, base64

bp = Blueprint("photos", __name__)

@bp.route("/api/photos", methods=["GET"])
def get_photos():
    group = request.args.get("group")
    photos = db.list_photos(group if group and group != "Tutte" else None)
    return jsonify(photos)

@bp.route("/api/photos/groups", methods=["GET"])
def get_groups():
    return jsonify(db.list_groups())

@bp.route("/api/photos/groups", methods=["POST"])
def create_group():
    name = request.json.get("name","").strip()
    if not name: return jsonify({"ok":False, "error":"Nome gruppo mancante"}), 400
    return jsonify({"ok": db.create_group(name)})

@bp.route("/api/photos/upload", methods=["POST"])
def upload():
    data = request.json
    filename = data.get("filename","")
    content  = data.get("content","")   # base64 puro
    group    = data.get("group") or None
    if not filename or not content:
        return jsonify({"ok":False, "error":"Dati mancanti"}), 400
    # Rimuovi eventuale header data:image/...;base64,
    if "," in content:
        content = content.split(",",1)[1]
    return jsonify({"ok": db.upload_photo(filename, content, group)})

@bp.route("/api/photos/delete", methods=["POST"])
def delete():
    data = request.json
    path = data.get("path","")
    sha  = data.get("sha","")
    if not path or not sha:
        return jsonify({"ok":False}), 400
    return jsonify({"ok": db.delete_photo(path, sha)})
