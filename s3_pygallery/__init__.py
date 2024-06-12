from sqlalchemy import column, text
from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
import s3_pygallery.s3
from s3_pygallery.core import Base, Image, db
from s3_pygallery.db_update import main as db_update
from s3_pygallery.handle_request import main as handle_request
overview_entries = ["album", "village", "county", "country", "date"]


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)

    if config is None:
        app.config.from_pyfile("config.py", silent=False)
    s3_config = app.config.get("S3_BACKEND")
    target_bucket = app.config.get("BUCKET")
    title = app.config.get("APP_TITLE")
    db.init_app(app)

    @app.route("/")
    def default_view():
        return redirect(url_for("gallery"))

    @app.route("/gallery")
    def gallery():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        else:
            if request.args:
                images = handle_request(db, request.args)
                if images is None:
                    flash("Request is invalid")
                    return redirect(url_for("default_view"))
                else:
                    return render_template("gallery.html",
                                           title=title,
                                           body=[i._gen_frontend(s3_config, target_bucket)
                                                 for i in list(images)])
            else:
                body = {}
                for entry in overview_entries:
                    body[entry] = db.session.execute(
                        db.select(getattr(Image, entry)).distinct()).scalars()
                return render_template("overview.html", body=body, title=title)

    @ app.route("/metadata", methods=['GET', 'POST'])
    def metadata():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        else:
            if request.method == "GET":
                if not request.args:
                    return redirect(url_for("default_view"))
                else:
                    for k, v in request.args.items():
                        if k == "id":
                            image = db.session.execute(
                                db.select(Image).where(getattr(Image, k) == int(v))).scalar_one()
                        return render_template("metadata.html", title=title, frontend=image._gen_frontend(s3_config, target_bucket), metadata=image._asdict())
            if request.method == "POST":
                image_id = int(request.args.get("id"))
                image = db.session.execute(
                    db.select(Image).where(Image.id == image_id)
                ).scalar_one()
                for k, v in request.form.items():
                    setattr(image, k, v)
                db.session.commit()
                return redirect(url_for("metadata", id=image_id))

    @ app.route("/login", methods=['GET', 'POST'])
    def login():
        if request.method == "GET":
            return render_template("login.html")

        if request.method == "POST":
            user = request.form["name"]
            password = request.form["password"]
            print(user, password)
            if s3.check_access(s3_config, target_bucket, user, password) is True:
                session["logged_in"] = True
                return redirect(url_for("default_view"))
            else:
                flash("Authentication failed.")

    return app


app = create_app()


def update_db():
    with app.app_context():
        db.create_all()
        print(app.config.get("S3_BACKEND"))
        print(app.config.get("BUCKET"))
        db_update(config=app.config.get("S3_BACKEND"),
                  bucket=str(app.config.get("BUCKET")), db=db)
        return
