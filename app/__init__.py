from flask import Flask, jsonify
import os

VERSION = "V6.1.2 Enterprise"


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "updates"), exist_ok=True)

    @app.context_processor
    def inject_globals():
        return {"APP_VERSION": VERSION, "COMPANY_NAME": "SMART DADA SOLUTION"}

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "version": VERSION})

    @app.route("/ready")
    def ready():
        return jsonify({"status": "ready", "version": VERSION})

    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.superadmin import superadmin_bp
    from .routes.client import client_bp
    from .routes.masters import masters_bp
    from .routes.documents import documents_bp
    from .routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(superadmin_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(masters_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(reports_bp)

    return app
