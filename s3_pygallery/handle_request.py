from flask import render_template, abort
from s3_pygallery.core import Image
from functools import partial
from datetime import date, time

special_keys = ["before", "after", "time_before", "time_after"]
valid_keys = dir(Image) + special_keys


def query_stmt(k, v):
    return lambda Image: getattr(Image, k) == v


def main(db, request):
    stmts = []
    for k, v in request.items():
        if k in valid_keys and request.get(k) != "":
            match k:
                case "before":
                    _date = date.fromisoformat(v)
                    stmts.append(lambda Image: Image.date <= _date)
                case "after":
                    _date = date.fromisoformat(v)
                    stmts.append(lambda Image: Image.date >= _date)
                case "date":
                    _date = date.fromisoformat(v)
                    stmts.append(lambda Image: Image.date == _date)
                case "time":
                    _time = time.fromisoformat(v)
                    stmts.append(lambda Image: Image.time == _time)
                case "time_after":
                    _time = time.fromisoformat(v)
                    stmts.append(lambda Image: Image.time >= _time)
                case "time_before":
                    _time = time.fromisoformat(v)
                    stmts.append(lambda Image: Image.time <= _time)
                case _:
                    stmts.append(query_stmt(k=k, v=v))
    return db.session.execute(db.select(Image).where(*[stmt(Image) for stmt in stmts])).scalars()
