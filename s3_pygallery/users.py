from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (Date, ForeignKey, Integer, String, Boolean)
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, mapped_column)
from werkzeug.security import generate_password_hash, check_password_hash


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def verify_password(session, user, passwd):
    user_passwd = db.session.execute(
        db.select(User.password).where(User.name == user)).scalar_one()
    return check_password_hash(user_passwd, passwd)
