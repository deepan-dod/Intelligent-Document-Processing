import os
import click
from flask import Flask
from config import Config
from database.models import db, User
from auth.security import bcrypt, login_manager, create_user

def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["MODEL_DIR"], exist_ok=True)
    db.init_app(app); bcrypt.init_app(app); login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    from auth.routes import auth_bp
    from api.routes import api
    from api.web import web
    for bp in (auth_bp, api, web): app.register_blueprint(bp)

    @app.get("/health")
    def health(): return {"status": "ok"}

    @app.after_request
    def headers(r):
        r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY"}); return r

    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username=app.config["ADMIN_USER"]).first():
            create_user(app.config["ADMIN_USER"], app.config["ADMIN_PASSWORD"], "admin")
        demo_users = [
            ("inv", "password123", "investigator"),
            ("rev", "password123", "reviewer"),
            ("aud", "password123", "auditor"),
        ]
        for uname, pwd, role in demo_users:
            if not User.query.filter_by(username=uname).first():
                create_user(uname, pwd, role)

    @app.cli.command("create-user")
    @click.argument("username")
    @click.argument("password")
    @click.argument("role")
    def _create_user(username, password, role): create_user(username, password, role); click.echo("created")

    @app.cli.command("train-models")
    def _train():
        from ml.training import train_classifier
        click.echo(train_classifier(app.config["MODEL_DIR"]).metrics)

    @app.cli.command("demo-data")
    def _demo():
        from documents.samples import load_demo
        click.echo(load_demo())
    return app

if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG") == "1")
