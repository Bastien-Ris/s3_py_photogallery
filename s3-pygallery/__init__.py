from flask import Flask


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    if config is None:
        app.config.from_pyfile("config.py", silent=False)

    return app
