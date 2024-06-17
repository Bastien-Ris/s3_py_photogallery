from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for, jsonify)
from celery import Celery
from s3_pygallery.core import Image, User, db
from s3_pygallery.main import create_main_blueprint
from s3_pygallery.admin import create_admin_blueprint
from s3_pygallery.api import create_api_blueprint
# used to create overviews
overview_entries = ["album", "village", "town", "county",
                    "state", "country", "date", "before", "after"]


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)

    if config is None:
        app.config.from_pyfile("config.py", silent=False)
    title = app.config.get("APP_TITLE")
    s3_config = app.config.get("S3_BACKEND")
    target_bucket = app.config.get("BUCKET")
    db.init_app(app)
    with app.app_context():
        db.create_all()

    main = create_main_blueprint(
        title, s3_config=s3_config, target_bucket=target_bucket)
    api = create_api_blueprint()
    admin = create_admin_blueprint()

    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(admin)

    @ app.route("/")
    def default_view():
        return redirect(url_for("main.gallery"))

    @app.route("/task/update_db", methods=["POST"])
    def start_db_update():
        if app.config.get("UPDATE_DB_TRUSTED_IP") is not None and request.remote_addr not in app.config.get("UPDATE_DB_TRUSTED_IP"):
            abort(403)
        else:
            update_db.delay()
            return jsonify("Ok. The database is being updated in the background"), 200

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


@ celery.task
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
