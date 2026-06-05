from flask import Flask
import os


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "sd-invoice-v6-secret-key")

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "data")

    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.client import client_bp
    from .routes.superadmin import superadmin_bp
    from .routes.masters import masters_bp
    from .routes.documents import documents_bp
    from .routes.ledger import ledger_bp
    from .routes.reports import reports_bp
    from .routes.exports import exports_bp
    from .routes.users import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(superadmin_bp)
    app.register_blueprint(masters_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(ledger_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(exports_bp)
    app.register_blueprint(users_bp)

    return app
