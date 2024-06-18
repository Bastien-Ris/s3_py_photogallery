from sqlalchemy import column, text
from flask import (Flask, Blueprint, abort, flash, redirect, render_template, request,
                   session, url_for, jsonify)
from celery import Celery
from werkzeug.security import generate_password_hash, check_password_hash
from s3_pygallery.core import Image, User, db, handle_request

valid_keys = dir(Image) + ["after", "before", "time_after", "time_before"]


def create_admin_blueprint(app):
    admin = Blueprint("admin", __name__, url_prefix="/admin")

    @admin.route("/")
    def get_user():
        return

    return admin
