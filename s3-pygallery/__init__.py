from core import Base, Image, db
from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)

# from s3 import s3_check_access


def handle_request(db, args):
    for k, v im args.items():
        images = db.get_or_404(
            db.select(Image).filter_by(getattr(Image, k) == v))
    return render_template("gallery.html",
                           body=[i._gen_frontend() for i in images])


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)

    if config is None:
        app.config.from_pyfile("config.py", silent=False)

    db.init_app(app)

    def update_db()

    @app.route("/")
    def default_view():
        return redirect(url_for("gallery"))

    @app.route("/gallery")
    def gallery():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        else:
            if request.args:
                return handle_request(db, request.args)
            else:
                return render_template("overview.html")

    @app.route("/login", methods=['GET', 'POST'])
    def login():
        if request.method == "GET":
            return render_template("login.html")
        if request.method == "POST":
            user = request.form["user"]
            password = request.form["password"]
            if s3_check_access(app.config, user, password) is True:
                session["logged_in"] = True
                return redirect(url_for("default_view"))
            else:
                flash("Authentication failed.")

    @app.route("/metadata")
    def metadata():
        print(request.args.keys())
        return [(k, v) for k, v in request.args.items()]

    return app
