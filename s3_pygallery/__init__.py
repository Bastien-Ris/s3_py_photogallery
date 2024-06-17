from sqlalchemy import column, text
from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from celery import Celery
import s3_pygallery.s3
from werkzeug.security import generate_password_hash, check_password_hash
from s3_pygallery.core import Base, Image, db
from s3_pygallery.handle_request import main as handle_request

# used to create overviews
overview_entries = ["album", "village", "town", "county",
                    "state", "country", "date", "before", "after"]


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)

    if config is None:
        app.config.from_pyfile("config.py", silent=False)
    s3_config = app.config.get("S3_BACKEND")
    target_bucket = app.config.get("BUCKET")
    title = app.config.get("APP_TITLE")
    db.init_app(app)
    with app.app_context():
        db.create_all()

    @ app.route("/")
    def default_view():
        return redirect(url_for("gallery"))

    @ app.route("/gallery")
    def gallery():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        else:
            if request.args:
                gallery_search = request.args.copy()
                shouldRedirect = False
                for k, v in request.args.items():
                    if v == "":
                        shouldRedirect = True
                        gallery_search[k] = None
                if shouldRedirect:
                    return redirect(url_for("gallery", **gallery_search))
                else:
                    images = handle_request(db, gallery_search)
                    return render_template("gallery.html",
                                           title=title,
                                           body=[i._gen_frontend(s3_config, target_bucket)
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

    @ app.route("/metadata")
    def metadata():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        else:
            if not request.args:
                return redirect(url_for("default_view"))
            else:
                for k, v in request.args.items():
                    image = db.session.execute(db.select(Image).where(
                        getattr(Image, k) == int(v))).scalar_one()
                    return render_template("metadata.html", title=title, frontend=image._gen_frontend(s3_config, target_bucket), metadata=image._asdict())

    @ app.route("/login", methods=['GET', 'POST'])
    def login():
        if request.method == "GET":
            return render_template("login.html", title=title)

        if request.method == "POST":
            user = request.form["name"]
            password = request.form["password"]
            if s3.check_access(s3_config, target_bucket, user, password) is True:
                session["logged_in"] = True
                return redirect(url_for("default_view"))
            else:
                flash("Authentication failed.")

    @app.route("/api/users")
    def show_users():
        return render_template("users.html", body=db.session.execute(db.select(User.id, User.name, User.admin)).scalars())

    @app.route("/api/gallery")
    def gallery_api():
        if request.args.get("access_key") is None or request.args.get("secret_key") is None:
            abort(403)
        if not s3.check_access(s3_config, target_bucket, request.args.get("access_key"), request.args.get("secret_key")):
            abort(403)
        else:
            query = {k: v for (k, v) in request.args.items()
                     if k in overview_entries}
            if not query:
                abort(404)
            else:
                images = handle_request(db, query)
                return [i._json_prepare() for i in images]

    @app.route("/api/update_db", methods=["POST"])
    def request_update_db():
        if app.config.get("UPDATE_DB_TRUSTED_IP") is not None and request.remote_addr not in app.config.get("UPDATE_DB_TRUSTED_IP"):
            abort(403)
        else:
            update_db.delay()
            flash("The database is being updated in background")
            return redirect(url_for("default_view"))

    return app


def create_celery(app):
    celery = Celery(app.name, broker=app.config.get('CELERY_BROKER_URL'))
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery


app = create_app()
celery = create_celery(app)


@celery.task
def update_db():
    s3_config = app.config.get("S3_BACKEND")
    target_bucket = app.config.get("BUCKET")
    database_keys = list(db.session.execute(db.select(Image.key)).scalars())
    storage_keys = s3.list_objects(s3_config, target_bucket)
    _to_delete = [key for key in database_keys if key not in storage_keys]
    _to_add = [key for key in storage_keys if key not in database_keys]

    for key in _to_delete:
        db.session.delete(Image).where(Image.key == key)
    db.session.commit()

    # break im groups of <20 images by commit.
    while len(_to_add) > 0:
        if len(_to_add) > 20:
            _handle = _to_add[0:20]
            for im in _handle:
                db.session.add(Image.from_s3_obj(s3_config=s3_config, bucket=target_bucket, key=im,
                               geolocator_agent=app.config.get("GEOLOCATOR_AGENT"), album=app.config.get("DEFAULT_ALBUM")))
            db.session.commit()
            del _to_add[0:20]
        else:
            for im in _to_add:
                db.session.add(Image.from_s3_obj(s3_config=s3_config, bucket=target_bucket, key=im,
                               geolocator_agent=app.config.get("GEOLOCATOR_AGENT"), album=app.config.get("DEFAULT_ALBUM")))
            db.session.commit()
            return
