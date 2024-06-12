from dataclasses import asdict, dataclass
from typing import List, Optional

from flask_sqlalchemy import SQLAlchemy
from s3_pygallery.s3 import gen_temporary_url
from sqlalchemy import (Date, ForeignKey, Integer, String, Time, create_engine,
                        select, column)
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, mapped_column,
                            relationship)


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


@dataclass
class Image(db.Model):
    __tablename__ = "pygallery2"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String())
    album: Mapped[str] = mapped_column(String())
    width: Mapped[int] = mapped_column(Integer())
    height: Mapped[int] = mapped_column(Integer())
    orientation: Mapped[str] = mapped_column(String())
    date: Mapped[str] = mapped_column(Date())
    time: Mapped[str] = mapped_column(Time())
    road: Mapped[Optional[str]] = mapped_column(String())
    village: Mapped[Optional[str]] = mapped_column(String())
    town: Mapped[Optional[str]] = mapped_column(String())
    municipality: Mapped[Optional[str]] = mapped_column(String())
    county: Mapped[Optional[str]] = mapped_column(String())
    state: Mapped[Optional[str]] = mapped_column(String())
    country: Mapped[Optional[str]] = mapped_column(String())

    def _gen_frontend(self, s3_config, bucket, expire=3600):
        _dict = {"image_id": self.id, "url": gen_temporary_url(
            config=s3_config, bucket=bucket, obj=self.key, expire=expire)}
        if self.orientation.upper() in ["RIGHT_TOP", u"RIGHT_TOP", "LEFT_TOP"]:
            _dict["display_height"] = self.width
            _dict["display_width"] = self.height
        else:
            _dict["display_height"] = self.height
            _dict["display_width"] = self.width
        return _dict

    def _asdict(self):
        return asdict(self)
