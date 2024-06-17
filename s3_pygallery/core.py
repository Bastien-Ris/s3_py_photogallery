from dataclasses import asdict, dataclass
from typing import List, Optional
from datetime import datetime
from io import BytesIO
from urllib.request import urlopen
from os import path
from PIL import Image as pil, ExifTags
from geopy.geocoders import Nominatim

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from s3_pygallery.s3 import gen_temporary_url
from sqlalchemy import (Date, ForeignKey, Integer, String, Boolean, Time, create_engine,
                        select, column)
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, mapped_column,
                            relationship)


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class User(db.Model):
    __tablename__ = "users"

    def __init__(self, name, password, admin=False):
        self.name = name
        self.password = generate_password_hash(password)
        self.admin = admin

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String())
    admin: Mapped[bool] = mapped_column(Boolean(), default="false")


@dataclass
class Image(db.Model):
    __tablename__ = "pygallery2"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(), unique=True, nullable=False)
    album: Mapped[str] = mapped_column(String())
    width: Mapped[int] = mapped_column(Integer())
    height: Mapped[int] = mapped_column(Integer())
    orientation: Mapped[int] = mapped_column(Integer())
    date: Mapped[str] = mapped_column(Date())
    time: Mapped[str] = mapped_column(Time())
    road: Mapped[Optional[str]] = mapped_column(String())
    village: Mapped[Optional[str]] = mapped_column(String())
    town: Mapped[Optional[str]] = mapped_column(String())
    municipality: Mapped[Optional[str]] = mapped_column(String())
    county: Mapped[Optional[str]] = mapped_column(String())
    state: Mapped[Optional[str]] = mapped_column(String())
    country: Mapped[Optional[str]] = mapped_column(String())
    altitude: Mapped[Optional[int]] = mapped_column(Integer())

    def _gen_frontend(self, s3_config, bucket, expire=3600):
        _dict = {"image_id": self.id, "url": gen_temporary_url(
            s3_config, bucket, self.key, expire)}
        if int(self.orientation) in [3, 5, 6, 7, 8]:
            _dict["display_height"] = self.width
            _dict["display_width"] = self.height
        else:
            _dict["display_height"] = self.height
            _dict["display_width"] = self.width
        return _dict

    def _asdict(self):
        return asdict(self)

    def _json_prepare(self):
        _dict = self._asdict()
        _dict["date"] = _dict["date"].isoformat()
        _dict["time"] = _dict["time"].isoformat()
        return _dict

    @classmethod
    def from_s3_obj(cls, s3_config, bucket, key, geolocator_agent, album=None):
        print("Image: {0}...".format(key))
        if album is None:
            dirname, filename = path.split(key)
            album = dirname.replace("/", "_")

        _meta = {"key": key, "album": album}
        fd = urlopen(gen_temporary_url(s3_config, bucket, key, expire=60))
        obj = BytesIO(fd.read())

        pil_info = pil.open(obj)

        _meta["width"], _meta["height"] = pil_info.size

        exifs = {ExifTags.TAGS[k]: v for k, v in pil_info._getexif(
        ).items() if k in ExifTags.TAGS}

        if exifs.get("Orientation"):
            _meta["orientation"] = exifs.get("Orientation")
        else:
            _meta["orientation"] = 1

        if exifs.get("DateTimeOriginal"):
            _exif_date = datetime.strptime(
                exifs.get("DateTimeOriginal"), "%Y:%m:%d %H:%M:%S")
            _meta["date"] = _exif_date.strftime("%Y-%m-%d")
            _meta["time"] = _exif_date.strftime("%H:%M")

        if exifs.get("GPSInfo"):
            gpsinfo = exifs.get("GPSInfo")
            geolocator = Nominatim(user_agent=geolocator_agent, timeout=5)

            def dms_do_dd(gps_coords, gps_coords_ref):
                try:
                    d, m, s = gps_coords
                except TypeError as e:
                    return
                dd = d + m / 60 + s / 3600
                if gps_coords_ref.upper() in ("S", "W"):
                    return float(-dd)
                elif gps_coords_ref.upper() in ("N", "E"):
                    return float(dd)
                else:
                    raise RuntimeError(
                        "Incorrect gps_coords_ref {}".format(gps_coords_ref))

            try:
                exif_long = dms_do_dd(
                    gpsinfo.get(4), gpsinfo.get(3))
                exif_lat = dms_do_dd(
                    gpsinfo.get(2), gpsinfo.get(1))

                image_location = geolocator.reverse(f"{exif_lat}, {exif_long}").raw.get(
                    "address"
                )

                for key in image_location.keys():
                    if key in dir(Image):
                        _meta[key] = image_location.get(key)

            except (RuntimeError, ValueError, KeyError, ConnectionError, Exception) as e:
                print(e)

            if gpsinfo.get(5) == b"\x00":
                _meta["altitude"] = int(gpsinfo.get(6))
            if gpsinfo.get(5) == b"\x01":
                _meta["altitude"] = - int(gpsinfo.get(6))

        return Image(**_meta)
