from sqlalchemy import column, text
from flask import Blueprint, session, request, render_template, redirect, url_for
from s3_pygallery.core import S3Client, Image, User, db, valid_keys, handle_request


overview_entries = ["album", "village", "town", "county",
                    "state", "country", "date", "before", "after"]


def create_main_blueprint(app):
    s3_client = S3Client(app.config.get("S3_BACKEND"))
    title = app.config.get("APP_TITLE")
    target_bucket = app.config.get("BUCKET")
    main = Blueprint("main", __name__)

    @ main.route("/gallery")
    def gallery():
        if not session.get("logged_in"):
            return redirect(url_for("main.login"))
        else:
            if request.args:
                gallery_search = request.args.copy()
                shouldRedirect = False
                for k, v in request.args.items():
                    if v == "":
                        shouldRedirect = True
                        gallery_search[k] = None
                if shouldRedirect:
                    return redirect(url_for("main.gallery", **gallery_search))
                else:
                    images = handle_request(db, gallery_search)
                    return render_template("gallery.html",
                                           title=title,
                                           body=[i._gen_frontend(s3_client, target_bucket)
                                                 for i in list(images)])
            else:
                body = {}
                for entry in overview_entries:
                    if entry not in ["before", "after"]:
                        body[entry] = db.session.execute(
                            db.select(getattr(Image, entry)).distinct()).scalars()
                    else:
                        body[entry] = db.session.execute(
                            db.select(getattr(Image, "date")).distinct()).scalars()
                return render_template("overview.html",
                                       body=body, title=title,
                                       image_number=db.session.query(Image).count())

    @ main.route("/metadata")
    def metadata():
        if not session.get("logged_in"):
            return redirect(url_for("main.login"))
        else:
            if not request.args:
                return redirect(url_for("default_view"))
            else:
                for k, v in request.args.items():
                    image = db.session.execute(db.select(Image).where(
                        getattr(Image, k) == int(v))).scalar_one()
                    return render_template("metadata.html", title=title, frontend=image._gen_frontend(s3_client, target_bucket), metadata=image._asdict())

    @main.route("/login", methods=['GET', 'POST'])
    def login():
        if request.method == "GET":
            return render_template("login.html", title=title)

        if request.method == "POST":
            if request.form.items() is not None:
                username = request.form["name"]
                password = request.form["password"]
            user = db.session.execute(db.select(User).where(
                User.name == username)).scalar_one_or_none()
            if user and user.check_password(password):
                session["logged_in"] = True
                session["username"] = username
                session["admin"] = user.admin
                return redirect(url_for("default_view"))
            else:
                flash("Authentication failed.")
                return redirect(url_for("default_view"))

    @main.route("/logout")
    def logout():
        session.pop("logged_in", False)
        session.pop("username", None)
        session.pop("admin", False)
        return redirect(url_for("default_view"))

    return main
