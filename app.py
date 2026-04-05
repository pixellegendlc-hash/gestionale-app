"""
app.py — Gestionale PWA
Entry point Flask, registra tutti i blueprint.
"""
import os
from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gestionale-secret-2024")

from routes.tasks   import bp as tasks_bp
from routes.finanze import bp as finanze_bp
from routes.appunti import bp as appunti_bp
from routes.photos  import bp as photos_bp
from routes.stats   import bp as stats_bp
from routes.export  import bp as export_bp

app.register_blueprint(tasks_bp)
app.register_blueprint(finanze_bp)
app.register_blueprint(appunti_bp)
app.register_blueprint(photos_bp)
app.register_blueprint(stats_bp)
app.register_blueprint(export_bp)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
