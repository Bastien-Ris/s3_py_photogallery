from flask import render_template, abort
from s3_pygallery.core import Image
from datetime import date, time


def main(db, request):

    for key in request.keys():
        if key not in ["date_interval"] and not hasattr(Image, key):
            return None

    for k, v in request.items():
        if k == "date_interval":
            _v = v.split("_")
            print(_v)
            images = db.session.execute(
                db.select(Image)
                .where(Image.date >= date.fromisoformat(_v[0]))
                .where(Image.date <= date.fromisoformat(_v[1]))).scalars()
        if k == "date":
            images = db.session.execute(
                db.select(Image)
                .where(getattr(Image, k) == date.fromisoformat(v))).scalars()
        else:
            images = db.session.execute(
                db.select(Image)
                .where(getattr(Image, k) == v)).scalars()

        return images
