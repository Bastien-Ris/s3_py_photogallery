from sqlalchemy import column, text
from flask import (Flask, Blueprint, abort, flash, redirect, render_template, request,
                   session, url_for, jsonify)
from celery import Celery
import s3_pygallery.s3
from werkzeug.security import generate_password_hash, check_password_hash
from s3_pygallery.core import Image, User, db
from s3_pygallery.handle_request import main as handle_request

valid_keys = dir(Image) + ["after", "before", "time_after", "time_before"]


def create_api_blueprint():
    api = Blueprint("api", __name__, url_prefix="/api")

    @api.route("/gallery")
    def gallery_api():
        if not session.get("admin"):
            abort(403)
        else:
            query = {k: v for (k, v) in request.args.items()
                     if k in valid_keys}
            if not query:
                abort(404)
            else:
                images = handle_request(db, query)
                return [i._json_prepare() for i in images]

    return api
